"""In-memory conversational session state for multi-turn estimation.

Sessions are stored in a process-local dictionary (no DB, no Redis). That is
deliberate for this phase: persistence, horizontal scaling, and session
federation belong to a later deployment module. The trade-off is accepted
volatility — all sessions are lost on service restart and are not shared
across worker processes.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, Field

from app.config import get_settings


class ProjectMetadata(BaseModel):
    """Distilled facts about the project under estimation.

    Survives history truncation. Updated after each turn with facts extracted
    from the latest user/assistant exchange.
    """

    project_name: str | None = None
    assumed_team_size: int | None = None
    mentioned_technologies: list[str] = Field(default_factory=list)
    agreed_scope: str | None = None


class Message(BaseModel):
    """A single conversational message (user or assistant only — not system)."""

    role: str
    content: str


class ConversationHistory:
    """Sliding-window store of user/assistant message pairs.

    The system prompt is never stored here. It is regenerated on every LLM call
    and prepended by ``to_messages_list()`` so ``project_metadata`` can update
    the system message without mutating stored turns.

    When the window exceeds ``MAX_CONVERSATION_TURNS`` pairs, the oldest
    user/assistant pair is discarded first.
    """

    def __init__(self) -> None:
        self._messages: list[Message] = []

    @property
    def messages(self) -> list[Message]:
        """Return a copy of the stored user/assistant messages."""
        return list(self._messages)

    def add_turn(self, user_content: str, assistant_content: str) -> None:
        """Append a user/assistant pair and enforce the sliding window."""
        self._messages.append(Message(role="user", content=user_content))
        self._messages.append(Message(role="assistant", content=assistant_content))
        self._trim()

    def _trim(self) -> None:
        max_messages = get_settings().MAX_CONVERSATION_TURNS * 2
        if len(self._messages) > max_messages:
            self._messages = self._messages[-max_messages:]

    def to_messages_list(self, system_prompt: str) -> list[dict[str, str]]:
        """Build the messages array for the LLM API.

        The system prompt is always first; stored turns follow in order.
        """
        result: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
        for message in self._messages:
            result.append({"role": message.role, "content": message.content})
        return result


class Session:
    """Conversational state for one estimation session.

    Combines raw history (``ConversationHistory``) with distilled project facts
    (``ProjectMetadata``). Both components are updated independently after each
    turn.
    """

    def __init__(self, session_id: str | None = None) -> None:
        self.session_id = session_id or str(uuid4())
        self.history = ConversationHistory()
        self.project_metadata = ProjectMetadata()
        self.anchors: list[str] = []
        self.summary: str = ""
        self.turn_index: int = 0
        self.last_resolved_tier: str = ""
        self.last_tier_rule: str = ""
        self.last_turn_observed: dict | None = None
        now = datetime.now(UTC)
        self.created_at = now
        self.updated_at = now

    def touch(self) -> None:
        """Update the last-modified timestamp."""
        self.updated_at = datetime.now(UTC)


class SessionNotFoundError(KeyError):
    """Raised when a ``session_id`` is not present in the store."""


class SessionStore:
    """Process-local registry of active sessions keyed by ``session_id``.

    Volatile by design: restarting the process clears all sessions. Migrating
    to Redis or PostgreSQL later requires only swapping this storage backend;
    ``Session``, ``ConversationHistory``, and ``ProjectMetadata`` stay unchanged.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def create(self) -> Session:
        """Create a new empty session and register it."""
        session = Session()
        self._sessions[session.session_id] = session
        return session

    def get(self, session_id: str) -> Session | None:
        """Return a session by id, or ``None`` if it does not exist."""
        return self._sessions.get(session_id)

    def get_or_raise(self, session_id: str) -> Session:
        """Return a session by id or raise ``SessionNotFoundError``."""
        session = self.get(session_id)
        if session is None:
            raise SessionNotFoundError(session_id)
        return session


# Module-level singleton — one store per worker process.
session_store = SessionStore()

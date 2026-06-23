# Estimator CAG - Servicio de Estimacion de Software con IA

Servicio de estimacion de proyectos de software impulsado por IA, utilizando una arquitectura **Cache Augmented Generation (CAG)**.

## Que es CAG y por que lo usamos

CAG (Cache Augmented Generation) es un patron de arquitectura donde el contexto relevante se inyecta directamente en el prompt del LLM como texto estatico. En esta fase del proyecto, las estimaciones de referencia se incluyen como ejemplos few-shot dentro del prompt del sistema, sin necesidad de una base de datos vectorial ni busqueda semantica.

La implementacion actual usa plantillas **Jinja2** bajo `app/prompts/estimation/`: cada version (`v1`, `v2`) tiene `system.j2`, `user.j2` y `examples.j2`, renderizados por `app/prompts/loader.py`. Existen dos conjuntos de prompts para comparaciones A/B en demos en vivo.

Este enfoque es ideal para empezar porque:
- Es simple de implementar y depurar
- No requiere infraestructura adicional (ni embeddings, ni vector stores)
- Funciona bien cuando el volumen de contexto es manejable (pocos ejemplos)

En modulos posteriores del master, este servicio evolucionara a una arquitectura **RAG** (Retrieval Augmented Generation) con base de datos vectorial para manejar un volumen mayor de ejemplos.

## Requisitos previos

- **Docker** y **Docker Compose** instalados (para la API)
- Una **API key** de OpenAI, Anthropic o Google Gemini
- **uv** y Python 3.11+ (para ejecucion local o Streamlit)
- Python **NO** es necesario localmente si solo usas Docker para la API

## Configuracion

Copia el archivo de entorno y configura las variables:

```bash
cp .env.example .env
# Editar .env y poner tu API key real
```

| Variable | Descripcion |
|----------|-------------|
| `LLM_PROVIDER` | Proveedor activo: `openai`, `anthropic` o `gemini` |
| `LLM_MODEL` | Modelo del proveedor (p. ej. `gpt-4o-mini`, `claude-haiku-4-5`, `gemini-2.0-flash`) |
| `OPENAI_API_KEY` | Clave OpenAI (requerida si `LLM_PROVIDER=openai`) |
| `ANTHROPIC_API_KEY` | Clave Anthropic (requerida si `LLM_PROVIDER=anthropic`) |
| `GEMINI_API_KEY` | Clave Google Gemini (requerida si `LLM_PROVIDER=gemini`) |
| `APP_ENV` | Entorno: `development`, `staging` o `production` |
| `LOG_LEVEL` | Nivel de log: `DEBUG`, `INFO`, `WARNING` o `ERROR` |
| `MAX_CONVERSATION_TURNS` | Pares user/assistant conservados en memoria por sesion (default: `6`) |

`.env.example` usa `openai` por defecto; si no hay archivo `.env`, `app/config.py` cae en `anthropic` / `claude-haiku-4-5`.

**Importante:** `get_settings()` esta cacheado con `@lru_cache`. Tras editar `.env`, **reinicia el proceso** (uvicorn o Streamlit). El flag `--reload` de uvicorn no recarga la configuracion cacheada.

## Inicio rapido con Docker (recomendado)

1. Clonar el repositorio y entrar al directorio:
   ```bash
   cd estimator
   ```

2. Configurar `.env` (ver seccion anterior).

3. Construir y levantar el servicio:
   ```bash
   docker compose up --build
   ```

4. La API estara disponible en `http://localhost:8000`

> Docker levanta **solo la API** (puerto 8000). La interfaz Streamlit no esta incluida en `docker-compose.yml` y debe ejecutarse localmente (ver mas abajo).

## Alternativa: ejecucion local sin Docker

```bash
uv sync
# Configurar .env con tus API keys
uv run uvicorn app.main:app --reload
```

## Interfaz web (Streamlit — Session 4)

Formulario tipado que envia la peticion a la API via HTTP. **No es chat ni streaming** — requiere que FastAPI este corriendo en paralelo.

```bash
# Terminal 1 — API
uv run uvicorn app.main:app --reload

# Terminal 2 — Streamlit
uv sync
cp .env.example .env   # configurar API key segun LLM_PROVIDER
uv run streamlit run streamlit_app.py
```

Abre `http://localhost:8501`. La barra lateral muestra proveedor y modelo (solo lectura), selector de version de prompt (`v1` / `v2`) y vistas previas del system/user prompt renderizados con Jinja. El formulario POSTea a `http://localhost:8000/api/v1/estimate?prompt_version=...` usando los mismos modelos Pydantic que la API.

## Sesiones conversacionales (Session 05)

El servicio soporta estimacion multi-turno con memoria en proceso y documentos adjuntos.

### Endpoints

| Metodo | Ruta | Descripcion |
|--------|------|-------------|
| `POST` | `/sessions` | Crea una sesion vacia; devuelve `{"session_id": "..."}` |
| `POST` | `/sessions/{session_id}/estimate` | Estima con `multipart/form-data` (`transcript` + `attachments` opcionales) |

Las sesiones viven en un diccionario en memoria del proceso: se pierden al reiniciar el servicio y no se comparten entre workers.

Ejemplo con transcript y adjunto:

```bash
SESSION_ID=$(curl -s -X POST http://localhost:8000/sessions | jq -r .session_id)

curl -X POST "http://localhost:8000/sessions/${SESSION_ID}/estimate?prompt_version=v2" \
  -F "transcript=We need a CRM with auth, contacts and roles. MVP in six weeks." \
  -F "attachments=@spec.docx"
```

**Respuesta** (`SessionEstimationResponse`):

```json
{
  "text": "...",
  "prompt_version": "v2",
  "project_metadata": {
    "project_name": null,
    "assumed_team_size": null,
    "mentioned_technologies": [],
    "agreed_scope": null
  }
}
```

### Adjuntos: Path B (extraccion local)

Implementamos **Path B** — extraccion de texto en el servicio AI con `pypdf` (PDF) y `python-docx` (Word), concatenada al transcript con el separador `=== attachment: filename ===`.

**Por que Path B y no multimodal directo (Path A):**

- **Independencia de proveedor** — el wrapper LLM sigue funcionando con OpenAI, Anthropic o Gemini sin Files API.
- **Control y testabilidad** — el texto extraido es inspectable y mockeable en tests.
- **Preparacion para RAG** — la misma logica de extraccion es el primer paso del pipeline de chunking del modulo 3.

Path A (subir el PDF al proveedor multimodal) es valido cuando la velocidad de desarrollo prima y se acepta acoplamiento al proveedor; para este ejercicio elegimos Path B.

## Probar el servicio

Health check:

```bash
curl http://localhost:8000/health
```

Estimacion (contrato Session 4):

```bash
curl -X POST "http://localhost:8000/api/v1/estimate?prompt_version=v1" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "We need a small CRM with auth, contacts and roles. MVP in six weeks.",
    "project_type": "web_saas",
    "detail_level": "medium",
    "output_format": "phases_table"
  }'
```

**Campos del request** (`EstimationRequest`):

| Campo | Valores permitidos |
|-------|-------------------|
| `description` | Texto del proyecto (20–2000 caracteres) |
| `project_type` | `mobile_app`, `web_saas`, `internal_tool`, `data_pipeline` |
| `detail_level` | `summary`, `medium`, `detailed` |
| `output_format` | `phases_table`, `line_items`, `narrative` |

**Query param:** `prompt_version` — `v1` (default) o `v2`. Selecciona el conjunto de plantillas Jinja bajo `app/prompts/estimation/`.

**Respuesta** (`EstimationResponse`):

```json
{
  "text": "...",
  "prompt_version": "v1"
}
```

## Flujo de la peticion

```mermaid
flowchart LR
  Client[Cliente_curl_o_Streamlit]
  API[POST_/api/v1/estimate]
  Loader[render_estimation_prompt]
  Templates["prompts/estimation/v1|v2"]
  LLM[llm_service]
  Client --> API
  API --> Loader
  Loader --> Templates
  Loader --> LLM
  LLM --> API
```

## Estructura del proyecto

```
estimator/
├── app/
│   ├── main.py                    # FastAPI, CORS, GET /health
│   ├── config.py                  # Pydantic Settings
│   ├── routers/estimations.py     # POST /api/v1/estimate
│   ├── routers/sessions.py        # POST /sessions, POST /sessions/{id}/estimate
│   ├── schemas/request_form.py    # EstimationRequest / EstimationResponse
│   ├── schemas/session.py         # SessionCreateResponse / SessionEstimationResponse
│   ├── services/llm_service.py    # generate_estimation_from_request (3 proveedores)
│   ├── services/attachments.py    # Extraccion local PDF/DOCX (Path B)
│   ├── services/session_estimation.py
│   ├── sessions.py                # ConversationHistory, ProjectMetadata, SessionStore
│   ├── prompts/
│   │   ├── loader.py              # render_estimation_prompt()
│   │   └── estimation/v1|v2/      # system.j2, user.j2, examples.j2
│   ├── ui/streamlit_helpers.py    # Helpers puros para sidebar/previews
│   └── fixtures/                  # Transcripciones de ejemplo (solo fixtures)
├── streamlit_app.py               # UI formulario (cliente HTTP)
├── tests/                         # pytest + AppTest
├── Dockerfile                     # Build multi-stage con uv
├── docker-compose.yml             # Configuracion para desarrollo local
└── pyproject.toml                 # Dependencias y configuracion
```

## Tests y lint

```bash
uv run pytest -v          # 107 tests, cobertura 100% en app/ + streamlit_app.py
uv run ruff check .
uv run ruff format .
```

Los tests usan mocks de proveedores — no requieren API keys reales (gracias a `tests/conftest.py`).

## Documentacion interactiva

Con el servicio corriendo, accede a la documentacion Swagger UI en:

- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

> Este proyecto forma parte del **Master en AI Engineering** y servira como base para evolucionar hacia una arquitectura RAG con base de datos vectorial en modulos posteriores.

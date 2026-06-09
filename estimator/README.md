# Estimator CAG - Servicio de Estimacion de Software con IA

Servicio de estimacion de proyectos de software impulsado por IA, utilizando una arquitectura **Cache Augmented Generation (CAG)**.

## Que es CAG y por que lo usamos

CAG (Cache Augmented Generation) es un patron de arquitectura donde el contexto relevante se inyecta directamente en el prompt del LLM como texto estatico. En esta fase del proyecto, las estimaciones de referencia se incluyen como ejemplos dentro del prompt del sistema, sin necesidad de una base de datos vectorial ni busqueda semantica.

Este enfoque es ideal para empezar porque:
- Es simple de implementar y depurar
- No requiere infraestructura adicional (ni embeddings, ni vector stores)
- Funciona bien cuando el volumen de contexto es manejable (pocos ejemplos)

En modulos posteriores del master, este servicio evolucionara a una arquitectura **RAG** (Retrieval Augmented Generation) con base de datos vectorial para manejar un volumen mayor de ejemplos.

## Requisitos previos

- **Docker** y **Docker Compose** instalados
- Una **API key** de OpenAI, Anthropic o Google Gemini
- Python **NO** es necesario localmente — todo se ejecuta dentro del contenedor

## Inicio rapido con Docker (recomendado)

1. Clonar el repositorio y entrar al directorio:
   ```bash
   cd estimator
   ```

2. Copiar el archivo de variables de entorno y configurar las API keys:
   ```bash
   cp .env.example .env
   # Editar .env y poner tu API key real
   ```

3. Construir y levantar el servicio:
   ```bash
   docker compose up --build
   ```

4. El servicio estara disponible en `http://localhost:8000`

## Alternativa: ejecucion local sin Docker

```bash
uv sync
# Configurar .env con tus API keys
uv run uvicorn app.main:app --reload
```

## Interfaz conversacional (Streamlit)

Chat multi-turno con estimaciones en streaming (Session 3). No requiere uvicorn — importa `app.*` directamente.

```bash
uv sync
cp .env.example .env   # configurar API key segun LLM_PROVIDER
uv run streamlit run streamlit_app.py
```

Abre `http://localhost:8501`. La barra lateral muestra proveedor, modelo, prompt del sistema, ejemplos CAG y metricas de la ultima llamada.

## Probar el servicio

```bash
curl -X POST http://localhost:8000/api/v1/estimate \
  -H "Content-Type: application/json" \
  -d '{
    "transcription": "The client wants to build a mobile app for managing restaurant reservations. They need user registration, a restaurant search with filters by cuisine and location, a real-time reservation system with availability checking, push notifications for reservation confirmations and reminders, and an admin panel for restaurant owners to manage their listings and view analytics."
  }'
```

## Estructura del proyecto

```
estimator/
├── app/
│   ├── main.py              # Aplicacion FastAPI, health check, CORS
│   ├── config.py            # Configuracion con Pydantic Settings
│   ├── routers/
│   │   └── estimations.py   # Endpoint POST /api/v1/estimate
│   ├── services/
│   │   └── llm_service.py   # LLM sync + streaming (OpenAI, Anthropic, Gemini)
│   ├── schemas/
│   │   └── estimation.py    # Modelos Pydantic (request/response)
│   ├── context/
│   │   └── examples.py      # Ejemplos de estimacion (contexto CAG)
│   └── ui/
│       └── streamlit_helpers.py  # Funciones puras para la UI Streamlit
├── streamlit_app.py         # Chat UI con streaming (Session 3)
├── tests/                   # pytest (API, LLM, Streamlit AppTest)
├── Dockerfile               # Build multi-stage con uv
├── docker-compose.yml       # Configuracion para desarrollo local
└── pyproject.toml           # Dependencias y configuracion
```

```bash
uv run pytest -v    # 45 tests — sin API keys reales
```

## Documentacion interactiva

Con el servicio corriendo, accede a la documentacion Swagger UI en:

- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

> Este proyecto forma parte del **Master en AI Engineering** y servira como base para evolucionar hacia una arquitectura RAG con base de datos vectorial en modulos posteriores.

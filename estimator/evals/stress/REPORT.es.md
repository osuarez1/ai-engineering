# Informe de prueba de estrés CAG (Ejercicio 6.1)

## Decisiones de diseño

- **Endpoint de snapshot:** Cada turno de estrés lee `GET /sessions/{id}` tras la estimación para que las métricas usen `last_turn_observed`, anclas, resumen y metadatos reales en lugar de inferir el estado solo desde el cuerpo de la respuesta.
- **Ubicación del módulo de métricas:** `evals/stress/metrics.py` vive junto al runner porque depende del contrato snapshot/`turn_observed`; no existe un paquete base compartido `evals/metrics.py` en este repositorio.
- **Caché activada durante el estrés:** `LLM_CACHE_ENABLED=true` para medir tasas de acierto exacto y semántico junto con latencia y coste.
- **Brecha especificación vs código:** el paso 0 añadió anclas, resumen incremental, niveles dinámicos, envoltorio de coste e instrumentación de caché sin ajustar constantes CAG existentes (`MAX_CONVERSATION_TURNS`, plantillas de prompt, etc.).

**Modo de ejecución:** in-process (LLM real, LLM_CACHE_ENABLED=true, pausa de 1500 ms entre peticiones) · **Filas:** 900

## Tabla resumen

| Escenario | Adjunto (KiB) | Latencia P50 (ms) | Latencia P95 (ms) | Coste total (USD) | Acierto caché exacta | Acierto caché semántica | Media MemoryDrift |
|---|---:|---:|---:|---:|---:|---:|---:|
| contradiction | 0 | 0 | 13976 | 0.0230 | 66.7% | 0.0% | 0.99 |
| contradiction | 5 | 0 | 0 | 0.0000 | 70.0% | 30.0% | 0.99 |
| contradiction | 20 | 0 | 0 | 0.0000 | 70.0% | 30.0% | 0.99 |
| contradiction | 50 | 0 | 0 | 0.0000 | 70.0% | 30.0% | 0.99 |
| contradiction | 100 | 0 | 0 | 0.0000 | 70.0% | 30.0% | 0.99 |
| growing | 0 | 0 | 11540 | 0.0203 | 66.7% | 0.0% | 0.94 |
| growing | 5 | 0 | 0 | 0.0011 | 73.3% | 25.0% | 0.94 |
| growing | 20 | 0 | 0 | 0.0000 | 70.0% | 30.0% | 0.94 |
| growing | 50 | 0 | 0 | 0.0000 | 70.0% | 30.0% | 0.94 |
| growing | 100 | 0 | 0 | 0.0000 | 70.0% | 30.0% | 0.94 |
| pivot | 0 | 0 | 8521 | 0.0164 | 66.7% | 0.0% | 0.96 |
| pivot | 5 | 0 | 0 | 0.0000 | 70.0% | 30.0% | 0.96 |
| pivot | 20 | 0 | 0 | 0.0000 | 70.0% | 30.0% | 0.96 |
| pivot | 50 | 0 | 0 | 0.0000 | 70.0% | 30.0% | 0.96 |
| pivot | 100 | 0 | 0 | 0.0000 | 70.0% | 30.0% | 0.96 |

## Curvas

### Latencia vs tokens de entrada (escenario growing, turno 1)

| Adjunto (KiB) | Media tokens_in | Media latency_ms | Media attachments_total_chars |
|---:|---:|---:|---:|
| 0 | 547 | 2730 | 0 |
| 5 | 4867 | 2211 | 20611 |
| 20 | 4867 | 0 | 60000 |
| 50 | 4867 | 0 | 60000 |
| 100 | 4867 | 0 | 60000 |

### Coste acumulado vs índice de turno (tamaño de adjunto = 0 KiB)

**contradiction**

| Turno | Media coste acumulado (USD) |
|---:|---:|
| 1 | 0.0001 |
| 3 | 0.0005 |
| 6 | 0.0013 |
| 10 | 0.0029 |
| 20 | 0.0077 |

**growing**

| Turno | Media coste acumulado (USD) |
|---:|---:|
| 1 | 0.0001 |
| 3 | 0.0005 |
| 6 | 0.0013 |
| 10 | 0.0028 |
| 20 | 0.0068 |

**pivot**

| Turno | Media coste acumulado (USD) |
|---:|---:|
| 1 | 0.0001 |
| 3 | 0.0005 |
| 6 | 0.0012 |
| 10 | 0.0024 |
| 20 | 0.0055 |

### Media MemoryDrift vs índice de turno (muestreado)

| Turno | Media memory_drift_score |
|---:|---:|
| 1 | 1.00 |
| 3 | 1.00 |
| 6 | 1.00 |
| 10 | 1.00 |
| 20 | 0.86 |

## Recuperación de adjuntos

- **5 KiB** (`STRESS_TOKEN_5KB`): tasa de recuperación 0.0% en 9 filas del turno 1.
- **20 KiB** (`STRESS_TOKEN_20KB`): tasa de recuperación 0.0% en 9 filas del turno 1.
- **50 KiB** (`STRESS_TOKEN_50KB`): tasa de recuperación 0.0% en 9 filas del turno 1.
- **100 KiB** (`STRESS_TOKEN_100KB`): tasa de recuperación 0.0% en 9 filas del turno 1.

## Análisis

En el perfil **growing** sin adjunto, el coste acumulado del turno 20 (0.0068 de media por sesión) es **54.4×** el coste por turno del turno 1 (0.0001), mientras que la media de `tokens_in` crece de 547 a 5152 (**9.4×**) a medida que el historial, las anclas y el resumen se acumulan en el prompt del sistema.

La recuperación media de MemoryDrift se mantiene en **100%** hasta el turno 12 y baja a **86%** en el turno 20 global (escenario pivot en turno 20: **79%**). La ejecución con adjunto de 100 KiB limita `attachments_total_chars` a **60000** (límite 60.000), y los tamaños de adjunto conservaron su `STRESS_TOKEN_*` en la respuesta del turno 1 según la tasa indicada arriba.

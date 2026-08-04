# CLAUDE.md

<<<<<<< HEAD
Este archivo guía a Claude Code al trabajar en este repositorio. No es solo documentación del proyecto: es una guía de ingeniería. Prioriza mantenibilidad, bajo acoplamiento y migración incremental hacia Clean Architecture por encima de resolver la tarea de la forma más rápida posible.

## Qué es esto

astrea-API es un backend FastAPI que genera reportes de carta natal astrológica. Calcula datos astronómicos con Swiss Ephemeris, hace que Claude (API de Anthropic) escriba la interpretación narrativa, persiste todo en SQLite, y puede renderizar el resultado como PDF o servirlo como JSON a un frontend. También genera horóscopos genéricos (no personalizados) diarios/semanales para los 12 signos.

## Objetivo arquitectónico del proyecto

Astrea está evolucionando hacia un backend de nivel profesional basado en Clean Architecture.

La migración será incremental. Nunca se realizarán reescrituras masivas.

Cada cambio debe acercar el proyecto a:
- módulos pequeños y cohesivos
- responsabilidades únicas
- inversión de dependencias
- alta testabilidad
- bajo acoplamiento
- separación entre dominio, aplicación e infraestructura

Cuando exista más de una solución válida, preferir la que facilite el mantenimiento a largo plazo.

**Hacia dónde evoluciona concretamente.** El destino no es una carpeta específica hoy, sino un conjunto de capas conceptuales que ya se pueden usar como lente al decidir dónde va código nuevo, aunque el árbol de carpetas actual (`app/api/`, `app/services/`, `app/models/`, `app/core/`) todavía no las refleje 1 a 1:

- **Dominio** — reglas de negocio puras, sin dependencias externas (FastAPI, SQLAlchemy, Anthropic, Nominatim). Ejemplos ya existentes: cálculos astrológicos (`dignidades_service.py`, `aspectos_service.py`, `regentes_service.py`), reglas del funnel de una carta.
- **Aplicación** — casos de uso que orquestan dominio + infraestructura para cumplir una operación completa (ej. "generar la interpretación premium de una carta"). Hoy vive mezclada dentro de `app/services/` y de `_calcular_todo` en `endpoints.py`.
- **Infraestructura** — detalles externos reemplazables: cliente de Anthropic, geocodificación (Nominatim), persistencia (SQLAlchemy/SQLite), renderizado (WeasyPrint), efemérides (Swiss Ephemeris).
- **Interfaz** — HTTP: routers de FastAPI, serialización de request/response. Es la capa más externa.

Regla de dependencia entre estas capas (más allá de que hoy no sean carpetas separadas): las capas externas dependen de las internas, nunca al revés. El dominio no debería necesitar saber que existen FastAPI, Anthropic o SQLAlchemy. Esto ya es, en espíritu, la sección "Dirección de dependencias" de más abajo — la diferencia es que ese apartado describe el estado actual de carpetas, y este describe hacia dónde apunta.

No crear `app/domain/`, `app/application/`, `app/infrastructure/` de forma preventiva o como tarea aislada — la migración ocurre cuando una tarea concreta lo justifica (ver "Forma de trabajar" y "God-files: regla split-first" más abajo), nunca como reorganización especulativa.

Las secciones siguientes (forma de trabajar, principios aplicados, deuda técnica conocida, convenciones) existen al servicio de este objetivo, no como reglas aisladas.

## Forma de trabajar

En este repo, actuá como un Staff Software Engineer — no como un generador de código que resuelve el pedido literal de la forma más rápida. Antes de implementar cualquier cambio no trivial:

1. **Evaluar el impacto real.** Qué capas toca el cambio, qué otros flujos dependen del código que vas a modificar (ej. tocar la forma de `calculo_json` afecta a las 3 llamadas a Claude que lo consumen y al renderizado del PDF, no solo al endpoint que estás editando).
2. **Detectar deuda técnica relacionada.** Si el cambio toca un archivo listado en `TECH_DEBT.md`, decilo explícitamente antes de implementar y proponé si conviene pagar parte de esa deuda como parte del cambio o dejarla para después — pero siempre de forma explícita, nunca en silencio.
3. **Explicar tradeoffs cuando haya más de una solución válida**, en vez de elegir en silencio. Justificar brevemente la opción elegida en términos de acoplamiento, testabilidad, tamaño del diff o riesgo — no solo "funciona".
4. **Priorizar mantenibilidad a largo plazo sobre la solución más rápida**, salvo que el usuario pida explícitamente lo contrario (ej. un prototipo descartable, un fix urgente de producción).
5. **No proponer reescrituras ni refactors masivos no pedidos.** El objetivo es que cada cambio individual acerque el proyecto al objetivo arquitectónico — no resolverlo todo de una vez porque "ya que estamos".
6. **Ante ambigüedad de alcance** (¿este cambio amerita separar un módulo o no?), preguntar o dejar explícito el criterio usado — no asumir en silencio y no sobre-diseñar por las dudas.

## Principios de ingeniería para este repo

Esto no es teoría genérica de SOLID/Clean Code — cada punto está anclado a una decisión real de este código. Al proponer un cambio, son los criterios de decisión, en este orden.

### 1. Dirección de dependencias

Dirección actual y objetivo:

```
app/api/*        → interfaz HTTP (routers de FastAPI)
     ↓
app/services/*   → lógica de aplicación y de dominio
     ↓
app/models/*     → schemas Pydantic + modelos SQLAlchemy
     ↓
app/core/*       → config, engine de DB, primitivas transversales
```

Nunca al revés: un servicio no importa nada de `app/api/`; `app/core/` no conoce nada de `app/services/`. Esto ya se respeta hoy — mantenerlo cuesta menos que restaurarlo después.

El límite dominio/infraestructura todavía no es explícito en el árbol de carpetas (no hay `app/domain/` ni `app/infrastructure/` separados). Hoy `app/services/` mezcla ambas cosas: lógica de dominio pura sin efectos secundarios (`dignidades_service.py`, `aspectos_service.py`, `regentes_service.py`, gran parte de `astro_service.py`) con infraestructura (llamadas HTTP a Anthropic/Nominatim, acceso a SQLAlchemy en `persistence_service.py`). No crear carpetas nuevas por prurito — pero si una tarea agrega responsabilidades nuevas a un servicio que ya mezcla ambas cosas, ese es el momento de separarlas, no antes.

### 2. Responsabilidad única, en la práctica

Un módulo tiene una única razón de cambio. Ejemplos ya correctos en el repo: `time_service.py` cambia solo si cambia cómo se calculan husos horarios o el día juliano; `geocoding_service.py` cambia solo si cambia el proveedor de geocodificación.

`interpretation_service.py` hoy viola esto: mezcla construcción de 4 prompts distintos, 4 llamadas a la API de Claude, parseo de markdown y validación de schema — al menos 3 razones de cambio distintas (cambiar un prompt, cambiar de proveedor de LLM, cambiar un esquema de validación) en un archivo de 563 líneas.

Regla práctica: si el cambio que necesitás hacer no tiene relación con la mayoría del archivo que estás tocando, es señal de que ya debería estar dividido. Extraé la pieza que estás tocando a su propio módulo como parte del cambio, no como tarea aparte "para después".

### 3. God-files: regla split-first

Dos archivos ya superaron el punto en que seguir agregándoles código es acumular deuda activamente:
- `app/api/endpoints.py` (591 líneas) — todas las rutas del proyecto en un único router.
- `app/services/interpretation_service.py` (563 líneas) — 4 prompts + 4 llamadas a Claude + parseo + validación.

Regla: **no seguir agregando código a estos archivos tal cual están.**

- Endpoint nuevo → va al archivo de dominio correspondiente aunque ese archivo todavía no exista. La convención ya está definida en `.claude/agents/revisor-endpoint.md`: `app/api/carta_natal.py`, `app/api/admin.py`, `app/api/horoscopos.py`, `app/api/dev_test.py` son el destino, no el estado actual (hoy no existen como archivos).
- Prompt nuevo en `interpretation_service.py` → evaluar extraer su bloque (prompt + llamada + parseo) a un módulo propio en vez de sumarlo al monolito.

Es migración incremental real: cada endpoint agregado en su propio archivo reduce el tamaño relativo del problema sin tocar lo que ya funciona.

### 4. Inversión de dependencias donde habilita testing

`interpretation_service.py` instancia `AsyncAnthropic` como singleton a nivel de módulo (línea 10). Esto acopla la lógica de negocio directamente al SDK y hace imposible testear construcción de prompts o parseo de respuestas sin llamar a la API real. No hace falta resolverlo preventivamente — pero si una tarea toca esta zona (nuevo prompt, cambio de modelo, primer test), inyectar el cliente como parámetro en vez de leerlo del scope del módulo es la dirección correcta.

`persistence_service.py` ya sigue el patrón correcto (recibe `db: Session` por parámetro en cada función) — es el ejemplo a imitar en el resto del código.

### 5. Validación en el borde, fail-fast

Los datos externos se validan una sola vez, en el borde, y el resto del sistema confía en esa forma ya validada:
- Requests HTTP: Pydantic (`app/models/schemas.py`) valida antes de que la lógica los toque.
- Respuesta de Claude: se valida contra un schema Pydantic inmediatamente después de parsear el JSON; si falla, se retorna `{"_validation_error": ...}` en vez de propagar un dict de forma desconocida hacia el resto del sistema.
- Errores esperables (ciudad no encontrada, fecha inválida) se modelan como `ValueError` y se traducen a `HTTPException` en el borde HTTP — nunca `None` silencioso ni excepciones sin capturar.

No agregues validación redundante más adentro del sistema "por las dudas" — si ya se validó en el borde, confiá en esa forma.

### 6. No abstracción especulativa (YAGNI)

Hay servicios simples de una función (`pdf_service.py`, `time_service.py`) que están bien así — no necesitan interfaces, clases base ni factories. Una abstracción (Protocol, ABC, Strategy) se justifica cuando ya existen ≥2 implementaciones reales o un test que la necesita para mockear — no para anticipar un proveedor de geocodificación o de LLM que todavía no existe. Preferí 3 líneas repetidas a una abstracción prematura que nadie usa todavía.

### 7. Refactor incremental, nunca reescrituras

- Nunca reescribir un módulo completo para cumplir una tarea chica. Si `endpoints.py` necesita un endpoint nuevo, no es la ocasión de partir todo el archivo — se agrega el endpoint en su lugar correcto y se deja el resto intacto.
- Boy-scout rule acotada: si tocás una función, dejala mejor de como la encontraste — pero no extiendas el refactor a código vecino que la tarea no te pidió tocar.
- Cuando haya más de una solución válida, elegí la que reduzca acoplamiento y facilite el próximo cambio, aunque tome un poco más de código hoy.
- Ejemplo real ya en el repo: al agregar el cuarto prompt de Claude (`generar_horoscopos`), se replicó el patrón existente (prompt + llamada + `_limpiar_json_markdown` + validación) en vez de generalizarlo de entrada — correcto en su momento, porque todavía no había una segunda necesidad real de abstracción. Ahora que son 4 casos casi idénticos, sí es candidato real a un helper compartido la próxima vez que se toque ese archivo — la repetición dejó de pagar su costo.

## Deuda técnica conocida

El proyecto tiene deuda técnica identificada y priorizada — god-files (`endpoints.py`, `interpretation_service.py`), falta de inyección de dependencias en la integración con Claude, ausencia de tests, y otros hallazgos de seguridad y consistencia de datos.

**`TECH_DEBT.md` es la fuente única y oficial para el seguimiento de esta deuda** (inventario completo, impacto, prioridad y plan de migración por fases). No se duplica el inventario acá — antes de tocar código en una zona con deuda conocida, revisar ese archivo. Si `TECH_DEBT.md` no existe o quedó desactualizado, tratarlo como una alerta a resolver, no como ausencia de deuda.

## Comandos

```bash
# Levantar el server en dev (con reload)
uvicorn app.main:app --reload

# Instalar dependencias
pip install -r requirements.txt

# Migraciones de DB (SQLite, archivo ./astrea.db en local)
alembic revision --autogenerate -m "descripcion"
alembic upgrade head

# Build/run con Docker (usado para el deploy en Railway)
docker build -t astrea-api .
docker run -p 8000:8000 astrea-api
```

No hay suite de tests ni tooling de lint/format configurado en el repo — no inventes comandos para ninguno de los dos. Si una tarea introduce el primer test, ver el ítem correspondiente en la tabla de deuda técnica.

Los commits son en español, estilo `tipo: descripcion` (`feat:`, `fix:`), consistente con `git log`.

## Arquitectura de dominio

Esta sección describe cómo funciona el sistema hoy — es el mapa, no el criterio de decisión (eso está arriba).

**Flujo de un request:** `app/api/endpoints.py` (todas las rutas viven hoy en este único archivo, con prefijo `/api/v1` definido en `app/main.py`) → `app/services/*` para toda la lógica de negocio → `app/models/db_models.py` (SQLAlchemy) para persistencia y `app/models/schemas.py` (Pydantic) para request/response y para validar el JSON que devuelve Claude.

**Pipeline de cálculo de carta** (orquestado por `_calcular_todo` en `endpoints.py`):
1. `geocoding_service.geocodificar_ciudad` — ciudad/país → lat/lon (Nominatim, rate-limited a 1 req/s, lanza `ValueError` si falla).
2. `time_service.calcular_hora_utc` — hora local de nacimiento → UTC usando el huso horario histórico real de esas coordenadas (`timezonefinder` + `zoneinfo`), luego `calcular_dia_juliano` para Swiss Ephemeris.
3. `astro_service.calcular_casas` / `calcular_posiciones_planetarias` — casas (Placidus) y posiciones planetarias vía `pyswisseph`. Los archivos de efemérides viven en `ephe/`.
4. `aspectos_service.calcular_todos_los_aspectos` — aspectos mayores entre todos los puntos.
5. `dignidades_service.calcular_dignidades_de_carta` / `calcular_elementos_y_modalidades` — dignidades esenciales, balance de elemento/modalidad.

Las tablas de referencia astrológica (códigos de planetas, signos, dispositores, dignidades, elementos/modalidades) son constantes en `app/core/config.py`, no viven en los servicios.

**Modelo de persistencia — una fila que crece a lo largo del funnel** (`CartaNatalGuardada` en `db_models.py`): una carta se identifica de forma única por `(fecha_hora_local, latitud, longitud)`. La misma fila acumula, en orden, a medida que el cliente avanza en el funnel: `calculo_json` (siempre) → `resumen_json` (teaser gratis) → `interpretacion_json` (premium, narrativa completa) → `areas_de_vida_json` (2da llamada a Claude) → `transitos_json` (3ra llamada a Claude) → `token`/`enviado` (aprobado manualmente y enviado). La etapa que ya existe se reutiliza en vez de recalcular Swiss Ephemeris o volver a pagar una llamada a Claude — revisar `deserializar_carta` y los `obtener_*` de `persistence_service.py` antes de regenerar cualquier cosa.

**Integración con Claude** (`interpretation_service.py`, el servicio más grande): 4 llamadas independientes, cada una con su propio system prompt, schema Pydantic y propósito:
- `interpretar_carta_completa` — interpretación premium completa (una sola llamada para que la narrativa pueda tejer conexiones entre puntos de la carta).
- `interpretar_resumen_gratuito` — teaser gratuito, deliberadamente superficial (solo Big Three), llamada separada de la interpretación completa.
- `interpretar_areas_de_vida` — 2da llamada premium: vocación/dinero/amor/herida (Quirón)/plan de acción/brújula. Usa `regentes_service.calcular_regentes_de_casas` para poder interpretar casas vacías a través de su regente.
- `interpretar_transitos` — 3ra llamada premium: tránsitos actuales vs. carta natal, foto fija tomada en el momento de aprobación, nunca se actualiza sola.
- `generar_horoscopos` — horóscopos genéricos diarios/semanales para los 12 signos, usa Haiku (más barato, contenido no personalizado) en vez de Sonnet.

Las 4 parsean la respuesta cruda de Claude con `_limpiar_json_markdown` (saca los ```json que Claude a veces agrega aunque se le pida no hacerlo), y validan contra un schema Pydantic de `app/models/schemas.py`. Ante `json.JSONDecodeError`/`ValidationError` devuelven `{"_validation_error": ..., "_raw_response": ...}` en vez de lanzar — los callers (endpoints, `guardar_horoscopo`, etc.) chequean `"_validation_error"` en el dict en vez de depender de excepciones. Cada prompt inyecta `genero` (femenino/masculino/None) para controlar la concordancia gramatical de género en español del texto generado, con instrucción explícita de evitar nombrar el género como sustantivo ("esta mujer") a favor de sujeto tácito en español.

**Tránsitos vs. natal, y vs. casas "naturales":** `transitos_service.calcular_transitos_actuales` compara las posiciones planetarias de hoy contra las casas natales de una persona específica (usado en su reporte premium). `calcular_transitos_por_signo` en cambio mapea los tránsitos de hoy sobre la rueda genérica casa-por-signo (Aries=Casa1, Tauro=Casa2, ...) sin datos reales de nacimiento — esto es lo que alimenta los horóscopos genéricos, vía `astro_service.calcular_casa_natural`.

**Renderizado del reporte:** `report_service.construir_contexto` junta el cálculo crudo de la carta con la interpretación de Claude en un solo dict (ej. adjunta a cada planeta su texto de interpretación por nombre), y se usa tanto para el template del PDF como para el endpoint JSON que consume el frontend — mantené esta lógica de join ahí en vez de duplicarla. `generar_html_reporte` renderiza `app/templates/carta_report.html` vía Jinja2; `pdf_service.generar_pdf_desde_html` convierte ese HTML a PDF con WeasyPrint (el layout de página/márgenes vive en las reglas CSS `@page` del template, no en Python).

**Auth:** las rutas de admin dependen de `verificar_admin_secret` (`app/core/admin_auth.py`), que chequea un header `X-Admin-Secret` contra `settings.admin_secret`. Las rutas públicas no tienen auth; el endpoint de resumen gratuito además tiene rate limit vía `app/core/limiter.py` (`slowapi`, por IP). `limiter` vive en su propio módulo específicamente para evitar un import circular entre `main.py` y `endpoints.py`.

**Fechas:** los datetimes naive guardados como UTC se serializan con `_iso_utc()` (`endpoints.py`), que agrega `Z` explícito — nunca usar `.isoformat()` a secas para estos casos, porque un datetime naive sin sufijo se interpreta mal como hora local en el frontend (bug real ya ocurrido).

## Convenciones para nuevos endpoints

Existe un subagente dedicado `revisor-endpoint` (`.claude/agents/revisor-endpoint.md`) que revisa endpoints nuevos/modificados contra estas convenciones — usalo después de escribir uno. Estas convenciones son la aplicación concreta de los principios de la sección de arriba (SRP, validación en el borde, split-first) a este dominio específico:

- Endpoints públicos que dependen de geocodificación envuelven la lógica en `try/except ValueError as e: raise HTTPException(400, ...)`. No encontrado → 404. Recurso existe pero en estado inválido (ej. interpretación aún no generada) → 409.
- Sin lógica de negocio en la función del endpoint (cálculos, construcción de prompts, manipulación de JSON no trivial) — eso vive en `app/services/`. El endpoint solo recibe el request, llama funciones de servicio, y devuelve la respuesta.
- Todo endpoint que toca la DB recibe `db: Session = Depends(get_db)`.
- Toda ruta bajo `/admin/*` (excepto la pública `/horoscopos/{cadencia}`) debe tener `dependencies=[Depends(verificar_admin_secret)]` — su ausencia es un hueco de seguridad real, no un detalle de estilo.
- Campos opcionales del request (ej. `genero`, `forzar`) van en un modelo Pydantic dedicado (`class XRequest(BaseModel): ...`), no como parámetros sueltos. Un booleano de "forzar regeneración" se llama `forzar`, default `False` (ver `ConversionAPremium`, `GenerarAreasDeVidaRequest`, `GenerarTransitosRequest`).
- Endpoints de generación (`/admin/generar-*`) devuelven `{"status": ..., "mensaje": ...}` con status en `generada`/`ya_existia`/`error`. Endpoints de listado devuelven dicts planos, nunca objetos SQLAlchemy crudos.
- Antes de escribir lógica nueva, buscar si ya existe una función de servicio equivalente (`obtener_carta_por_id`, `deserializar_carta`, `_iso_utc`, etc.) — no duplicar.

Nota: el checklist del agente describe las rutas divididas entre `app/api/carta_natal.py`, `app/api/admin.py`, `app/api/horoscopos.py` y `app/api/dev_test.py`, pero hoy todas las rutas viven en `app/api/endpoints.py`. Tratá esa división como la dirección objetivo (ver "God-files: regla split-first" arriba), no como el layout actual — verificá con grep antes de asumir que una ruta vive en un archivo que todavía no existe.
=======
This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

astrea-API: a FastAPI backend that computes natal astrology charts (Swiss Ephemeris) and generates
narrative interpretations via Claude (Anthropic API). It serves a free teaser flow, a paid PDF/premium
flow driven manually through an admin panel, and generic (non-personalized) daily/weekly horoscopes.
All domain code, comments, and API text are in Spanish (Latin American neutral) — keep new code
consistent with that.

## Folder structure

```
app/
  main.py                 # FastAPI app setup: CORS, rate limiter, static mount, router include
  api/
    endpoints.py          # All routes (public + /admin/*), single flat router
  core/
    config.py             # Settings (env-based) + all astrological constants (signs, rulers,
                           # dignities, elements/modalities) — extend tables here, not inline
    database.py            # SQLAlchemy engine/session, Base, get_db dependency
    admin_auth.py           # X-Admin-Secret header check dependency
    limiter.py              # slowapi Limiter instance (own module to avoid circular import)
  models/
    db_models.py            # SQLAlchemy models: CartaNatalGuardada, HoroscopoGenerado
    schemas.py               # Pydantic request/response schemas, incl. the Claude response schemas
  services/
    astro_service.py               # Swiss Ephemeris: houses, planetary positions, sign/house math
    time_service.py                 # local->UTC conversion (timezonefinder) + Julian day
    aspectos_service.py             # aspect calculation between chart points
    dignidades_service.py           # essential dignities + element/modality balance
    regentes_service.py             # house ruler ("regente") lookup, for empty-house interpretation
    transitos_service.py            # today's transits vs. a natal chart, and vs. generic sign wheel
    geocoding_service.py            # city+country -> lat/lon (Nominatim, rate-limited)
    interpretation_service.py       # all Claude calls: full chart, areas de vida, transitos, horoscopos
    resumen_deterministico_service.py  # free teaser text, rule-based (no Claude call)
    report_service.py               # joins calculo + interpretacion into the render context
    pdf_service.py                  # HTML -> PDF via WeasyPrint
    persistence_service.py          # all CartaNatalGuardada/HoroscopoGenerado CRUD + (de)serialization
  templates/
    carta_report.html        # Jinja2 template, shared by the HTML endpoint and the PDF renderer
    assets/                   # images referenced by the template (resolved via pdf_service base_url)
static/assets/               # served at /static, used by the web (non-PDF) chart view
ephe/                         # Swiss Ephemeris data files (seas_18.se1, semo_18.se1, sepl_18.se1, sefstars.txt)
alembic/                      # migrations; versions/ holds one file per schema change
alembic.ini                   # default sqlalchemy.url, overridden by DATABASE_URL at runtime (see env.py)
borrar_cache.py                # one-off manual script to delete a specific cached CartaNatalGuardada row by natural key
carta_preview.html, reporte.html, vista_web.html  # standalone HTML mockups/previews, not served by the app
```

## Running locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Requires a `.env` file (loaded via `python-dotenv` in `app/main.py`) with:
- `ANTHROPIC_API_KEY` — used by `app/services/interpretation_service.py`
- `ADMIN_SECRET` — required header value (`X-Admin-Secret`) for all `/admin/*` endpoints
- `DATABASE_URL` (optional) — SQLite path; defaults to `sqlite:///./astrea.db` locally, and to a Railway
  persistent volume (e.g. `sqlite:////data/astrea.db`) in production

No test suite or linter is configured in this repo yet.

### Database migrations (Alembic)

```bash
alembic revision --autogenerate -m "descripcion"
alembic upgrade head
```

`alembic/env.py` overrides `alembic.ini`'s hardcoded URL with the same `DATABASE_URL` env var the app
uses, so migrations target the same DB as the running app (important in production, where the URL points
to a mounted volume). Table creation also happens automatically on app startup via
`Base.metadata.create_all()` in `app/main.py` — this is additive only (never drops/alters existing
tables), so schema changes to existing tables still need a real Alembic migration.

## Architecture

### Request flow (the core pipeline)

Every chart-producing endpoint in `app/api/endpoints.py` follows the same shape:
1. Geocode city+country → lat/lon (`geocoding_service.geocodificar_ciudad`, Nominatim, rate-limited to
   1 req/sec).
2. Look up `CartaNatalGuardada` by the natural key `(fecha_hora_local, latitud, longitud)` via
   `persistence_service.buscar_carta_existente` — charts are cached/reused by this key rather than
   recomputed, since Swiss Ephemeris + Claude calls are expensive.
3. If missing, run the full astronomical calculation (`endpoints._calcular_todo`): local→UTC time
   conversion using the coordinate's real historical timezone (`time_service`), Julian day, houses +
   planetary positions (`astro_service`, using `pyswisseph` with ephemeris files in `ephe/`), aspects
   (`aspectos_service`), essential dignities and element/modality balance (`dignidades_service`).
2. Persist progressively — a `CartaNatalGuardada` row accumulates state over its lifecycle rather than
   being written once. Which JSON columns are populated tells you what stage the chart is at (see the
   docstring on the model in `app/models/db_models.py`):
   - `calculo_json` only → nothing generated yet
   - `+ resumen_json` → free teaser flow completed
   - `+ interpretacion_json` → premium purchased and full interpretation generated
   - `+ token` + `enviado=True` → manually approved by admin and link sent to customer
   - `areas_de_vida_json` / `transitos_json` are separate, independently-generated premium sections
     (see below)
4. Any step already computed for a given natural key is reused, never recomputed — e.g. buying premium
   after the free flow reuses `calculo_json` and only adds the missing interpretation.

### The three (independent) Claude calls per premium chart

`app/services/interpretation_service.py` makes three separate `AsyncAnthropic` calls, each with its own
system prompt, Pydantic response schema (`app/models/schemas.py`), and admin trigger endpoint — kept
separate so no single response has to carry too many sections:
1. `interpretar_carta_completa` → `InterpretacionCompleta` (planet-by-planet narrative + "carta en una
   mirada" executive summary). Triggered by `/carta-natal/pdf` or `/admin/generar-interpretacion/{id}`.
2. `interpretar_areas_de_vida` → `InterpretacionAreasDeVida` (vocación/dinero/amor/Quirón, aspect
   interpretations, plan de acción, brújula). Triggered by `/admin/generar-areas-de-vida/{id}`. Uses
   `regentes_service` to interpret houses with no natal planets via their ruling planet ("regente").
3. `interpretar_transitos` → `InterpretacionTransitos` (today's transits vs natal chart, next 3-6
   months). Triggered by `/admin/generar-transitos/{id}` — this is a snapshot at approval time, not
   live/recomputed on each view.

All three (plus `generar_horoscopos`) parse the model's raw text, strip markdown code fences
(`_limpiar_json_markdown`), `json.loads`, then validate against the Pydantic schema. On failure
(`JSONDecodeError` or `ValidationError`), they return `{"_validation_error": ..., "_raw_response": ...}`
instead of raising — callers (endpoints, `guardar_areas_de_vida`/`guardar_transitos`) check for
`_validation_error` in the dict to detect this failure mode rather than catching an exception.

Gender agreement (`genero`: `"femenino"`/`"masculino"`/`None`) is threaded through each prompt to
control Spanish grammatical concordance, with explicit instructions to avoid naming gender as a noun
("esta mujer"/"este hombre").

### Free vs. premium vs. admin-approval split

- `POST /carta-natal/resumen` — public, rate-limited (5/min), generates only the deterministic free
  teaser (`resumen_deterministico_service`, no Claude call at all — distinct from the free flow, which
  used to call Claude via `interpretar_resumen_gratuito`).
- `POST /carta-natal/compra` — public, called from the post-Hotmart-purchase `gracias.html` page. Only
  computes the chart and stores `nombre_reporte`/`email`; does **not** call Claude automatically.
  Interpretation generation for purchases is a deliberate manual step from the admin panel, not
  automatic — see `/admin/generar-interpretacion/{id}`.
- `/admin/*` endpoints all require the `X-Admin-Secret` header (`admin_auth.verificar_admin_secret`),
  matched against `settings.admin_secret`. This is the panel used to review chart quality before
  approving (`/admin/aprobar/{id}` generates an opaque `secrets.token_urlsafe` access token — no login
  system, Notion/Loom-style share links) and send the customer their link manually (no SMTP wired up
  yet, per code comments).
- `GET /carta-natal/token/{token}` — the public, no-auth endpoint the customer's link resolves to.

### Generic horoscopes (separate from natal charts)

`HoroscopoGenerado` is unrelated to `CartaNatalGuardada` — it stores daily/weekly horoscopes for all 12
signs (not per-customer). `POST /admin/generar-horoscopos/{cadencia}` (`cadencia`: `diario`/`semanal`)
computes today's transits per sign via `transitos_service.calcular_transitos_por_signo` (which uses
`astro_service.calcular_casa_natural` to place transits into a generic house wheel per sun sign, with no
real birth data) and generates copy using Haiku (cheaper model, since this content is generic and short)
instead of Sonnet. Each generation is inserted as a new row (history is kept, not overwritten).
`GET /horoscopos/{cadencia}` is the public read endpoint, always serving the most recently generated row.

### Report rendering

`report_service.construir_contexto` is the single place that joins calculated planet data with its
matching interpretation text (via `MAPEO_INTERPRETACION`, since calc uses names like `NodoNorte` and the
interpretation schema uses `nodo_norte`). It's reused for both HTML rendering (`/carta-natal/html`, via
Jinja2 template `app/templates/carta_report.html`) and the raw JSON endpoint consumed by the frontend
(`/carta-natal/data`, `/carta-natal/token/{token}`). PDF generation (`pdf_service`) renders that same HTML
through WeasyPrint (not a headless browser) — page layout/margins live entirely in the template's CSS
`@page` rules.

### Swiss Ephemeris details worth knowing

- Ephemeris data files live in `ephe/`; the path is set once at import time in `astro_service.py`.
- House system is fixed to Placidus (`b'P'`) throughout.
- Planet codes, sign lists, modern rulerships, essential dignity tables (domicile/exaltation/fall/exile),
  and elements/modalities-per-sign are all centralized as constants in `app/core/config.py` — extend
  these tables there, not inline in services.
- `determinar_casa_natal` expects natal house data as it comes back from JSON deserialization (string
  keys), so it always indexes with `str(numero_casa)` — a common gotcha if calling it with the raw dict
  from `calcular_casas()` directly (which was int-keyed before serialization).
>>>>>>> origin/main

# CLAUDE.md

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

- **Dominio** — reglas de negocio puras, sin dependencias externas (FastAPI, SQLAlchemy, Anthropic, Nominatim). Ya vive en `app/domain/`: cálculos astrológicos puros (`aspectos_service.py`, `dignidades_service.py`, `regentes_service.py`, `resumen_deterministico_service.py`). Reglas del funnel de una carta siguen mezcladas en `app/services/` por ahora.
- **Aplicación** — casos de uso que orquestan dominio + infraestructura para cumplir una operación completa (ej. "generar la interpretación premium de una carta"). Hoy vive mezclada dentro de `app/services/` y de `_calcular_todo` en `app/api/carta_natal.py`.
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

El límite dominio/infraestructura ya es explícito para una parte del árbol (Horizonte 3, en progreso): `app/domain/` contiene la lógica de dominio pura sin efectos secundarios que ya se extrajo (`aspectos_service.py`, `dignidades_service.py`, `regentes_service.py`, `resumen_deterministico_service.py`). Todavía no existe `app/infrastructure/` — `app/services/` sigue mezclando dominio parcial (gran parte de `astro_service.py`) con infraestructura (llamadas HTTP a Anthropic/Nominatim, acceso a SQLAlchemy en `persistence_service.py`, WeasyPrint en `pdf_service.py`). No crear carpetas nuevas por prurito — pero si una tarea agrega responsabilidades nuevas a un servicio que ya mezcla ambas cosas, ese es el momento de separarlas, no antes.

### 2. Responsabilidad única, en la práctica

Un módulo tiene una única razón de cambio. Ejemplos ya correctos en el repo: `time_service.py` cambia solo si cambia cómo se calculan husos horarios o el día juliano; `geocoding_service.py` cambia solo si cambia el proveedor de geocodificación.

Ejemplo ya corregido en el repo: `interpretation_service.py` mezclaba construcción de 5 prompts distintos, 5 llamadas a la API de Claude, parseo de markdown y validación de schema — al menos 3 razones de cambio distintas (cambiar un prompt, cambiar de proveedor de LLM, cambiar un esquema de validación) en un archivo de 563 líneas. Se dividió en `interpretation_common.py` (lo compartido: cliente por defecto, parseo/validación, instrucción de género) y un archivo por caso de uso (`interpretation_carta_completa.py`, `interpretation_resumen_gratuito.py`, `interpretation_areas_de_vida.py`, `interpretation_transitos.py`, `interpretation_horoscopos.py`) — cada uno cambia solo si cambia ese prompt específico.

Regla práctica: si el cambio que necesitás hacer no tiene relación con la mayoría del archivo que estás tocando, es señal de que ya debería estar dividido. Extraé la pieza que estás tocando a su propio módulo como parte del cambio, no como tarea aparte "para después".

### 3. God-files: regla split-first

Los dos god-files originales del proyecto ya se dividieron (Horizonte 2): `app/api/endpoints.py` en `app/api/carta_natal.py`, `app/api/admin.py`, `app/api/horoscopos.py` y `app/api/dev_test.py`; `app/services/interpretation_service.py` en `interpretation_common.py` + un archivo por caso de uso (ver sección "Integración con Claude" más abajo). Endpoint nuevo → va directo al archivo de dominio correspondiente. Prompt nuevo de Claude → evaluar si merece su propio módulo `interpretation_*.py` en vez de sumarlo a uno existente que ya tiene su propia razón de cambio.

Es migración incremental real: cada pieza movida a su propio archivo reduce el tamaño relativo del problema sin tocar lo que ya funciona.

### 4. Inversión de dependencias donde habilita testing

Cada uno de los 5 módulos `interpretation_*.py` acepta `client: AsyncAnthropic` como parámetro en su función pública (`interpretar_carta_completa`, `interpretar_resumen_gratuito`, `interpretar_areas_de_vida`, `interpretar_transitos`, `generar_horoscopos`), con `_client_default` (el singleton definido en `interpretation_common.py`) como valor por defecto — así los call sites existentes en `app/api/carta_natal.py`, `admin.py` y `dev_test.py` no cambian, pero los tests pueden inyectar un doble sin llamar a la API real (ver `tests/test_interpretation_service.py`). Si una tarea agrega un 6º caso de uso de Claude, seguir el mismo patrón.

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

- Nunca reescribir un módulo completo para cumplir una tarea chica. Si un caso de uso de Claude necesita ajustarse, no es la ocasión de tocar los otros 4 módulos `interpretation_*.py` — se agrega en su lugar correcto y se deja el resto intacto.
- Boy-scout rule acotada: si tocás una función, dejala mejor de como la encontraste — pero no extiendas el refactor a código vecino que la tarea no te pidió tocar.
- Cuando haya más de una solución válida, elegí la que reduzca acoplamiento y facilite el próximo cambio, aunque tome un poco más de código hoy.
- Ejemplo real ya en el repo: al agregar el cuarto prompt de Claude (`generar_horoscopos`), se replicó el patrón existente (prompt + llamada + `_limpiar_json_markdown` + validación) en vez de generalizarlo de entrada — correcto en su momento, porque todavía no había una segunda necesidad real de abstracción. Ahora que son 4 casos casi idénticos, sí es candidato real a un helper compartido la próxima vez que se toque ese archivo — la repetición dejó de pagar su costo.

## Deuda técnica conocida

El proyecto tiene deuda técnica identificada y priorizada — hallazgos de consistencia de datos y operación pendientes (ver Fases 3-4 del plan de migración). Los dos god-files originales (`endpoints.py`, `interpretation_service.py`), la inyección de dependencias en la integración con Claude y la ausencia de tests ya se resolvieron.

**`TECH_DEBT.md` es la fuente única y oficial para el seguimiento de esta deuda** (inventario completo, impacto, prioridad y plan de migración por fases). No se duplica el inventario acá — antes de tocar código en una zona con deuda conocida, revisar ese archivo. Si `TECH_DEBT.md` no existe o quedó desactualizado, tratarlo como una alerta a resolver, no como ausencia de deuda.

## Comandos

```bash
# Levantar el server en dev (con reload)
uvicorn app.main:app --reload

# Instalar dependencias (produccion)
pip install -r requirements.txt

# Instalar dependencias de desarrollo (incluye pytest, sobre requirements.txt)
pip install -r requirements-dev.txt

# Correr la suite de tests
pytest

# Migraciones de DB (SQLite, archivo ./astrea.db en local)
alembic revision --autogenerate -m "descripcion"
alembic upgrade head

# Build/run con Docker (usado para el deploy en Railway)
docker build -t astrea-api .
docker run -p 8000:8000 astrea-api
```

Hay una suite de tests (`pytest`, `pytest-asyncio`) en `tests/`, en construcción incremental como parte del Horizonte 1 de `ROADMAP.md` — no asumas cobertura donde no la hay, pero sí usa `pytest` como comando real. No hay tooling de lint/format configurado en el repo — no inventes comandos para eso.

Los commits son en español, estilo `tipo: descripcion` (`feat:`, `fix:`), consistente con `git log`.

## Arquitectura de dominio

Esta sección describe cómo funciona el sistema hoy — es el mapa, no el criterio de decisión (eso está arriba).

**Flujo de un request:** `app/api/{carta_natal,admin,horoscopos,dev_test}.py` (routers de FastAPI por dominio, todos con prefijo `/api/v1` definido en `app/main.py`) → `app/services/*` para toda la lógica de negocio → `app/models/db_models.py` (SQLAlchemy) para persistencia y `app/models/schemas.py` (Pydantic) para request/response y para validar el JSON que devuelve Claude.

**Pipeline de cálculo de carta** (orquestado por `_calcular_todo` en `app/api/carta_natal.py`):
1. `geocoding_service.geocodificar_ciudad` — ciudad/país → lat/lon (Nominatim, rate-limited a 1 req/s, lanza `ValueError` si falla).
2. `time_service.calcular_hora_utc` — hora local de nacimiento → UTC usando el huso horario histórico real de esas coordenadas (`timezonefinder` + `zoneinfo`), luego `calcular_dia_juliano` para Swiss Ephemeris.
3. `astro_service.calcular_casas` / `calcular_posiciones_planetarias` — casas (Placidus) y posiciones planetarias vía `pyswisseph`. Los archivos de efemérides viven en `ephe/`.
4. `domain.aspectos_service.calcular_todos_los_aspectos` — aspectos mayores entre todos los puntos.
5. `domain.dignidades_service.calcular_dignidades_de_carta` / `calcular_elementos_y_modalidades` — dignidades esenciales, balance de elemento/modalidad.

Las tablas de referencia astrológica (códigos de planetas, signos, dispositores, dignidades, elementos/modalidades) son constantes en `app/core/config.py`, no viven en los servicios.

**Modelo de persistencia — una fila que crece a lo largo del funnel** (`CartaNatalGuardada` en `db_models.py`): una carta se identifica de forma única por `(fecha_hora_local, latitud, longitud)`. La misma fila acumula, en orden, a medida que el cliente avanza en el funnel: `calculo_json` (siempre) → `resumen_json` (teaser gratis) → `interpretacion_json` (premium, narrativa completa) → `areas_de_vida_json` (2da llamada a Claude) → `transitos_json` (3ra llamada a Claude) → `token`/`enviado` (aprobado manualmente y enviado). La etapa que ya existe se reutiliza en vez de recalcular Swiss Ephemeris o volver a pagar una llamada a Claude — revisar `deserializar_carta` y los `obtener_*` de `persistence_service.py` antes de regenerar cualquier cosa.

**Integración con Claude** (`app/services/interpretation_common.py` + un `interpretation_*.py` por caso de uso): 5 llamadas independientes, cada una con su propio system prompt, schema Pydantic y propósito:
- `interpretation_carta_completa.interpretar_carta_completa` — interpretación premium completa (una sola llamada para que la narrativa pueda tejer conexiones entre puntos de la carta).
- `interpretation_resumen_gratuito.interpretar_resumen_gratuito` — teaser gratuito, deliberadamente superficial (solo Big Three), llamada separada de la interpretación completa.
- `interpretation_areas_de_vida.interpretar_areas_de_vida` — 2da llamada premium: vocación/dinero/amor/herida (Quirón)/plan de acción/brújula. Usa `domain.regentes_service.calcular_regentes_de_casas` para poder interpretar casas vacías a través de su regente.
- `interpretation_transitos.interpretar_transitos` — 3ra llamada premium: tránsitos actuales vs. carta natal, foto fija tomada en el momento de aprobación, nunca se actualiza sola.
- `interpretation_horoscopos.generar_horoscopos` — horóscopos genéricos diarios/semanales para los 12 signos, usa Haiku (más barato, contenido no personalizado) en vez de Sonnet.

Las 5 parsean la respuesta cruda de Claude con `interpretation_common._parsear_respuesta` (que a su vez usa `_limpiar_json_markdown` para sacar los ```json que Claude a veces agrega aunque se le pida no hacerlo), y validan contra un schema Pydantic de `app/models/schemas.py`. Ante `json.JSONDecodeError`/`ValidationError` devuelven `{"_validation_error": ..., "_raw_response": ...}` en vez de lanzar — los callers (endpoints, `guardar_horoscopo`, etc.) chequean `"_validation_error"` en el dict en vez de depender de excepciones. `interpretar_carta_completa`, `interpretar_areas_de_vida` y `interpretar_transitos` inyectan `genero` (femenino/masculino/None) vía `interpretation_common._instruccion_genero` para controlar la concordancia gramatical de género en español del texto generado, con instrucción explícita de evitar nombrar el género como sustantivo ("esta mujer") a favor de sujeto tácito en español (excepto en `interpretar_transitos`, que pide tercera persona fluida en su lugar).

**Tránsitos vs. natal, y vs. casas "naturales":** `transitos_service.calcular_transitos_actuales` compara las posiciones planetarias de hoy contra las casas natales de una persona específica (usado en su reporte premium). `calcular_transitos_por_signo` en cambio mapea los tránsitos de hoy sobre la rueda genérica casa-por-signo (Aries=Casa1, Tauro=Casa2, ...) sin datos reales de nacimiento — esto es lo que alimenta los horóscopos genéricos, vía `astro_service.calcular_casa_natural`.

**Renderizado del reporte:** `report_service.construir_contexto` junta el cálculo crudo de la carta con la interpretación de Claude en un solo dict (ej. adjunta a cada planeta su texto de interpretación por nombre), y se usa tanto para el template del PDF como para el endpoint JSON que consume el frontend — mantené esta lógica de join ahí en vez de duplicarla. `generar_html_reporte` renderiza `app/templates/carta_report.html` vía Jinja2; `pdf_service.generar_pdf_desde_html` convierte ese HTML a PDF con WeasyPrint (el layout de página/márgenes vive en las reglas CSS `@page` del template, no en Python).

**Auth:** las rutas de admin dependen de `verificar_admin_secret` (`app/core/admin_auth.py`), que chequea un header `X-Admin-Secret` contra `settings.admin_secret`. Las rutas públicas no tienen auth; los endpoints costosos de `carta_natal.py` (`/resumen`, `/html`, `/data`, `/pdf`, `/compra`) tienen rate limit vía `app/core/limiter.py` (`slowapi`, por IP). `limiter` vive en su propio módulo específicamente para evitar un import circular entre `main.py` y los routers de `app/api/`.

**Fechas:** los datetimes naive guardados como UTC se serializan con `_iso_utc()` (`app/api/admin.py`), que agrega `Z` explícito — nunca usar `.isoformat()` a secas para estos casos, porque un datetime naive sin sufijo se interpreta mal como hora local en el frontend (bug real ya ocurrido).

## Convenciones para nuevos endpoints

Estas convenciones son la aplicación concreta de los principios de la sección de arriba (SRP, validación en el borde, split-first) a este dominio específico:

- Endpoints públicos que dependen de geocodificación envuelven la lógica en `try/except ValueError as e: raise HTTPException(400, ...)`. No encontrado → 404. Recurso existe pero en estado inválido (ej. interpretación aún no generada) → 409.
- Sin lógica de negocio en la función del endpoint (cálculos, construcción de prompts, manipulación de JSON no trivial) — eso vive en `app/services/`. El endpoint solo recibe el request, llama funciones de servicio, y devuelve la respuesta.
- Todo endpoint que toca la DB recibe `db: Session = Depends(get_db)`.
- Toda ruta bajo `/admin/*` (excepto la pública `/horoscopos/{cadencia}`) debe tener `dependencies=[Depends(verificar_admin_secret)]` — su ausencia es un hueco de seguridad real, no un detalle de estilo.
- Campos opcionales del request (ej. `genero`, `forzar`) van en un modelo Pydantic dedicado (`class XRequest(BaseModel): ...`), no como parámetros sueltos. Un booleano de "forzar regeneración" se llama `forzar`, default `False` (ver `ConversionAPremium`, `GenerarAreasDeVidaRequest`, `GenerarTransitosRequest`).
- Endpoints de generación (`/admin/generar-*`) devuelven `{"status": ..., "mensaje": ...}` con status en `generada`/`ya_existia`/`error`. Endpoints de listado devuelven dicts planos, nunca objetos SQLAlchemy crudos.
- Antes de escribir lógica nueva, buscar si ya existe una función de servicio equivalente (`obtener_carta_por_id`, `deserializar_carta`, `_iso_utc`, etc.) — no duplicar.

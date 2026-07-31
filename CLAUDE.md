# CLAUDE.md

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

# 🔮 astrea-API

API backend en **FastAPI** para generar cartas natales astrológicas: cálculo astronómico preciso con **Swiss Ephemeris** e interpretación narrativa con **IA (Claude)**. Incluye un flujo gratuito, un flujo premium con aprobación manual vía panel de admin, y horóscopos genéricos diarios/semanales.

---

## ✨ Características

- 🪐 **Cálculo astronómico real** con `pyswisseph`: planetas, casas (sistema Placidus), aspectos, dignidades esenciales y balance de elementos/modalidades.
- 🌍 **Geolocalización y zona horaria histórica** a partir de ciudad + país (Nominatim + `timezonefinder`), para convertir la hora local de nacimiento a UTC correctamente.
- 🤖 **Interpretación con IA (Claude/Anthropic)** en tres llamadas independientes: interpretación completa de la carta, áreas de vida (vocación, dinero, amor, herida y don), y clima energético según tránsitos actuales.
- 🆓 **Flujo gratuito**: resumen teaser determinístico (sin IA), pensado como preview del reporte premium.
- 💎 **Flujo premium**: cálculo automático al momento de la compra + generación manual de la interpretación desde un panel de administración, antes de aprobar el envío al cliente.
- 🔗 **Enlaces de acceso sin login**, tipo Notion/Loom, mediante tokens opacos únicos.
- 📄 **Reportes en PDF y HTML** generados desde el mismo template Jinja2, renderizados a PDF con WeasyPrint.
- ♈ **Horóscopos genéricos** (diarios/semanales) para los 12 signos, generados con un modelo más económico (Haiku).
- 🛡️ **Rate limiting** en endpoints públicos y autenticación simple por header para el panel de admin.

---

## 🧱 Stack tecnológico

| Área | Tecnología |
|---|---|
| Framework web | FastAPI + Uvicorn |
| Cálculo astrológico | pyswisseph (Swiss Ephemeris) |
| IA / interpretación | Anthropic (Claude Sonnet y Haiku) |
| Base de datos | SQLAlchemy + SQLite |
| Migraciones | Alembic |
| Geocodificación | geopy (Nominatim) |
| Zona horaria | timezonefinder |
| Renderizado de reportes | Jinja2 + WeasyPrint (HTML → PDF) |
| Rate limiting | slowapi |
| Validación | Pydantic / pydantic-settings |

---

## 📂 Estructura del proyecto

```
app/
├── main.py                # Setup de FastAPI: CORS, rate limiter, estáticos, router
├── api/
│   ├── carta_natal.py       # Rutas publicas de carta natal (/resumen, /html, /data, /pdf, /compra, /token)
│   ├── admin.py             # Rutas /admin/* (requieren X-Admin-Secret)
│   ├── horoscopos.py        # Ruta publica /horoscopos/{cadencia}
│   └── dev_test.py          # Rutas /test-* (requieren X-Admin-Secret)
├── core/
│   ├── config.py            # Settings + constantes astrológicas (signos, regentes, dignidades...)
│   ├── database.py           # Engine, sesión de SQLAlchemy y dependencia get_db
│   ├── admin_auth.py          # Verificación del header X-Admin-Secret
│   └── limiter.py             # Instancia compartida del rate limiter
├── models/
│   ├── db_models.py           # Modelos SQLAlchemy: CartaNatalGuardada, HoroscopoGenerado
│   └── schemas.py              # Esquemas Pydantic (requests y respuestas validadas de Claude)
├── domain/
│   ├── aspectos_service.py             # Cálculo de aspectos entre puntos de la carta (puro)
│   ├── dignidades_service.py           # Dignidades esenciales + elementos/modalidades (puro)
│   ├── regentes_service.py             # Regente de cada casa (para casas vacías) (puro)
│   └── resumen_deterministico_service.py  # Resumen gratuito, basado en reglas (sin IA) (puro)
├── services/
│   ├── astro_service.py               # Casas, posiciones planetarias, signo/casa
│   ├── time_service.py                 # Conversión hora local → UTC + día juliano
│   ├── transitos_service.py            # Tránsitos actuales vs. carta natal / rueda genérica
│   ├── geocoding_service.py            # Ciudad + país → coordenadas
│   ├── interpretation_common.py        # Compartido por las llamadas a Claude: cliente, parseo/validacion, genero
│   ├── interpretation_carta_completa.py    # Llamada a Claude: interpretacion premium completa
│   ├── interpretation_resumen_gratuito.py  # Llamada a Claude: teaser gratuito
│   ├── interpretation_areas_de_vida.py     # Llamada a Claude: vocacion/dinero/amor/herida/plan de accion
│   ├── interpretation_transitos.py         # Llamada a Claude: transitos actuales vs. carta natal
│   ├── interpretation_horoscopos.py        # Llamada a Claude: horoscopos genericos diarios/semanales
│   ├── report_service.py               # Une cálculo + interpretación en el contexto de render
│   ├── pdf_service.py                  # HTML → PDF con WeasyPrint
│   └── persistence_service.py          # CRUD y (de)serialización de las cartas guardadas
├── templates/
│   ├── carta_report.html      # Template Jinja2 compartido por el HTML y el PDF
│   └── assets/                 # Imágenes usadas por el template
static/assets/                # Servido en /static, usado por la vista web (no PDF)
ephe/                          # Archivos de efemérides de Swiss Ephemeris
alembic/                       # Migraciones de base de datos
```

---

## ⚙️ Instalación y configuración

### 1. Cloná el repo e instalá dependencias

```bash
git clone <url-del-repo>
cd astrea-API
pip install -r requirements.txt
```

> 💡 WeasyPrint requiere dependencias del sistema (Pango, Cairo, GDK-Pixbuf). Ver `Dockerfile` para la lista exacta en Debian/Ubuntu.

### 2. Variables de entorno

Creá un archivo `.env` en la raíz:

```env
ANTHROPIC_API_KEY=sk-ant-...
ADMIN_SECRET=un-secreto-elegido-por-vos
DATABASE_URL=sqlite:///./astrea.db
```

| Variable | Descripción |
|---|---|
| `ANTHROPIC_API_KEY` | Clave de la API de Anthropic, usada para todas las interpretaciones con IA |
| `ADMIN_SECRET` | Valor exigido en el header `X-Admin-Secret` para acceder a los endpoints `/admin/*` |
| `DATABASE_URL` | Opcional. Por defecto `sqlite:///./astrea.db` en local; en producción apunta a un volumen persistente |

### 3. Corré las migraciones

```bash
alembic upgrade head
```

### 4. Levantá el servidor

```bash
uvicorn app.main:app --reload
```

La API queda disponible en `http://localhost:8000`, con salud en `GET /health`.

---

## 🐳 Docker

```bash
docker build -t astrea-api .
docker run -p 8000:8000 --env-file .env astrea-api
```

---

## 🚦 Flujo de una carta natal

1. **Geocodificación**: ciudad + país → latitud/longitud (Nominatim, con límite de 1 req/seg).
2. **Búsqueda de carta existente**: se identifica de forma única por `(fecha_hora_local, latitud, longitud)`. Si ya existe, se reutiliza en vez de recalcular.
3. **Cálculo astronómico** (si no existía): hora UTC real según coordenadas, día juliano, casas (Placidus), posiciones planetarias, aspectos, dignidades y balance de elementos.
4. **Persistencia progresiva**: cada carta guarda su estado según qué columnas tiene pobladas — `calculo_json` → `+ resumen_json` (gratis) → `+ interpretacion_json` (premium) → `+ token` y `enviado=True` (aprobada y enviada).
5. **Interpretación con IA** (premium, en 3 llamadas independientes a Claude): carta completa, áreas de vida, y clima energético (tránsitos), cada una disparada manualmente desde el panel de admin.
6. **Aprobación manual**: el admin revisa la calidad del contenido generado y aprueba el envío, lo que genera un token de acceso único para el cliente final.

---

## 🔑 Endpoints principales

### Públicos

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/api/v1/carta-natal/resumen` | Resumen gratuito (rate-limited, sin IA) |
| `POST` | `/api/v1/carta-natal/compra` | Registra una compra y calcula la carta (sin IA todavía) |
| `POST` | `/api/v1/carta-natal/html` | Reporte en HTML de una carta ya generada |
| `POST` | `/api/v1/carta-natal/data` | Reporte en JSON, para consumo del frontend |
| `POST` | `/api/v1/carta-natal/pdf` | Reporte en PDF (genera la interpretación si falta) |
| `GET` | `/api/v1/carta-natal/token/{token}` | Reporte de acceso público vía link de token |
| `GET` | `/api/v1/horoscopos/{cadencia}` | Horóscopo genérico más reciente (`diario`/`semanal`) |
| `GET` | `/health` | Health check |

### Administración (requieren header `X-Admin-Secret`)

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/v1/admin/pendientes` | Cartas compradas pendientes de aprobación |
| `GET` | `/api/v1/admin/carta/{id}` | Detalle completo de una carta |
| `POST` | `/api/v1/admin/generar-interpretacion/{id}` | Genera la interpretación completa vía IA |
| `POST` | `/api/v1/admin/generar-areas-de-vida/{id}` | Genera vocación/dinero/amor/herida y don |
| `POST` | `/api/v1/admin/generar-transitos/{id}` | Genera el clima energético actual |
| `POST` | `/api/v1/admin/aprobar/{id}` | Aprueba el envío y genera el token de acceso |
| `GET` | `/api/v1/admin/enviadas` | Cartas ya aprobadas y enviadas |
| `POST` | `/api/v1/admin/generar-horoscopos/{cadencia}` | Genera los horóscopos genéricos del día/semana |

---

## 🗺️ Migraciones (Alembic)

```bash
# Crear una nueva migración a partir de cambios en los modelos
alembic revision --autogenerate -m "descripcion"

# Aplicar migraciones pendientes
alembic upgrade head
```

`alembic/env.py` usa la misma variable `DATABASE_URL` que la app en tiempo de ejecución, para no desincronizar el esquema de la base real (por ejemplo, el volumen persistente en producción).

---

## 📝 Notas

- No hay suite de tests ni linter configurado todavía.
- El idioma de dominio de todo el proyecto (código, prompts, respuestas) es español latinoamericano neutro — mantené esa consistencia en cualquier contribución.

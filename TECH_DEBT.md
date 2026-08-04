# TECH_DEBT.md

Auditoría completa de astrea-API y plan de migración incremental hacia el objetivo arquitectónico descrito en `CLAUDE.md`. Este documento es el backlog detallado y priorizado; la sección "Deuda técnica conocida" de `CLAUDE.md` es su resumen operativo de referencia rápida — si diverge de este archivo, este archivo es la fuente de verdad.

**Alcance de la auditoría:** lectura completa de `app/` (api, services, models, core), `alembic/`, `Dockerfile`, `requirements.txt`, `.gitignore`, archivos sueltos en la raíz del repo, y el historial de commits relevante para entender decisiones ya tomadas.

**Cómo se prioriza:** cada hallazgo tiene Impacto, Prioridad (Crítica/Alta/Media/Baja), esfuerzo estimado y si bloquea trabajo futuro. "Crítica" se reserva para riesgo activo en producción (seguridad, costo, pérdida de datos) — se resuelve fuera del roadmap de arquitectura, cuanto antes. El resto se paga de forma incremental, tocando el código por una razón real, nunca en una tarea aislada de "limpieza".

---

## Resumen ejecutivo

| # | Hallazgo | Categoría | Prioridad |
|---|---|---|---|
| 1 | Endpoints públicos sin rate limit ni auth disparan llamadas pagas a Claude sin control | Seguridad / costo | **Crítica** |
| 2 | Sin `.dockerignore`: `.env` y secretos pueden terminar dentro de la imagen Docker | Seguridad | **Crítica** |
| 3 | `app/api/endpoints.py` — 591 líneas, todas las rutas del proyecto en un archivo | Arquitectura | Alta |
| 4 | `app/services/interpretation_service.py` — 563 líneas, 4 responsabilidades mezcladas | Arquitectura | Alta |
| 5 | `AsyncAnthropic` como singleton de módulo, sin inyección de dependencias | Testabilidad | Alta |
| 6 | Cero tests en el repo | Testing | Media |
| 7 | `Base.metadata.create_all()` y Alembic coexisten sin una única fuente de verdad de schema | Datos | Media |
| 8 | `requirements.txt` sin versión pinneada en la mayoría de las dependencias | Operación | Media |
| 9 | Dockerfile corre como root, sin usuario no-privilegiado | Seguridad | Media |
| 10 | Bloques de instrucción de género duplicados 3 veces en `interpretation_service.py` | Mantenibilidad | Media |
| 11 | Código muerto versionado en la raíz del repo (`vista_web.html`, `reporte.html`, `carta_preview.html`, `borrar_cache.py`) | Housekeeping | Baja |
| 12 | `app/core/config.py` mezcla `Settings` de entorno con constantes astrológicas de dominio | Arquitectura | Baja |
| 13 | Coincidencia de carta existente por igualdad exacta de floats (lat/lon) | Datos | Baja |
| 14 | `print()` de debug en código productivo (`astro_service.py`) | Housekeeping | Baja |
| 15 | Copia de base de datos de producción en el entorno de desarrollo local | Datos / privacidad | Baja (operativo) |

---

## Hallazgos detallados

### 1. Endpoints públicos que disparan llamadas pagas a Claude sin control — Crítica

- **Dónde:** `app/api/endpoints.py`. En particular `/carta-natal/pdf` (línea 199), `/carta-natal/html` y `/carta-natal/data` (menos graves, requieren carta ya existente), y sobre todo `/test-interpretacion-completa` (línea 372) — endpoint sin auth, sin rate limit, que llama directamente a `interpretar_carta_completa` (Claude Sonnet) por cada request.
- **Impacto:** `/carta-natal/resumen`, `/carta-natal/html`, `/carta-natal/data`, `/carta-natal/pdf` y `/carta-natal/compra` ya tienen `@limiter.limit("5/minute")`. Sigue pendiente `/test-*` (pensados para desarrollo, a juzgar por el nombre y por estar fuera de la convención de `revisor-endpoint.md`) — quedan expuestos en producción sin ningún control, cualquiera puede generar costo de Claude repetidamente sin límite.
- **Prioridad:** Crítica — mientras `/test-*` siga sin restricción, la exposición económica activa no está mitigada del todo.
- **Esfuerzo:** bajo (horas). Falta sacar `/test-*` de producción (flag de entorno, o quitarlos del router en prod, o exigir `verificar_admin_secret`).
- **¿Bloquea funcionalidades futuras?** No, pero es el ítem con mayor riesgo de daño real si no se atiende — tratar fuera del roadmap de arquitectura, como fix inmediato.

### 2. Sin `.dockerignore` — riesgo de fuga de secretos en la imagen

- **Dónde:** raíz del repo, `Dockerfile` línea 17 (`COPY . .`).
- **Impacto:** no existe `.dockerignore`. El build de Docker copia todo el contexto, incluyendo `.env` (con `ANTHROPIC_API_KEY` y `ADMIN_SECRET`) si está presente en el directorio al momento del build, además de `venv/`, `*.db` y los PDFs de prueba. Si esa imagen se publica en cualquier registry, los secretos quedan en una capa de la imagen de forma permanente, incluso si se borran después.
- **Prioridad:** Crítica — es una fuga de secretos, no una preferencia de estilo.
- **Esfuerzo:** trivial (minutos): crear `.dockerignore` con al menos `.env`, `venv/`, `*.db`, `*.pdf`, `.git/`.
- **¿Bloquea funcionalidades futuras?** No, pero debe resolverse antes que cualquier otra tarea de infraestructura.

### 3. `app/api/endpoints.py` — god-file de rutas

- **Dónde:** `app/api/endpoints.py` (591 líneas).
- **Impacto:** carta natal, admin, horóscopos y endpoints de test mezclados en un único router. Ya documentado en `CLAUDE.md` ("God-files: regla split-first"), con convención de destino ya definida en `.claude/agents/revisor-endpoint.md` (`carta_natal.py`, `admin.py`, `horoscopos.py`, `dev_test.py`).
- **Prioridad:** Alta.
- **Esfuerzo:** medio, pero se paga incrementalmente (ver Fase 2 del plan).
- **¿Bloquea funcionalidades futuras?** Sí — dificulta aislar la capa de interfaz de la de aplicación, y cada endpoint nuevo aumenta el costo de separar después.

### 4. `app/services/interpretation_service.py` — god-file de generación de contenido

- **Dónde:** `app/services/interpretation_service.py` (563 líneas).
- **Impacto:** 4 prompts, 4 llamadas a Claude, parseo de markdown y validación de schema en un archivo. Es el servicio más grande del repo y el que concentra el mayor riesgo de negocio (es lo que el cliente paga).
- **Prioridad:** Alta.
- **Esfuerzo:** medio-alto, requiere primero la Fase 1 (tests + inyección de dependencias) para hacerlo con seguridad.
- **¿Bloquea funcionalidades futuras?** Sí — bloquea testear la generación de contenido de forma aislada y bloquea cambiar de proveedor de LLM sin tocar los 4 casos de uso a la vez.

### 5. `AsyncAnthropic` como singleton de módulo

- **Dónde:** `app/services/interpretation_service.py`, línea 10 (`client = AsyncAnthropic(api_key=settings.anthropic_api_key)`).
- **Impacto:** acopla la lógica de negocio directamente al SDK; imposible mockear el cliente para testear construcción de prompts o parseo sin llamar a la API real (y generar costo).
- **Prioridad:** Alta — es la precondición técnica para poder testear el servicio más crítico del producto.
- **Esfuerzo:** bajo — inyectar el cliente como parámetro con default al singleton actual, sin cambiar la forma pública de las funciones que ya se llaman desde `endpoints.py`.
- **¿Bloquea funcionalidades futuras?** Sí, directamente bloquea la Fase 1 del plan de migración.

### 6. Cero tests en el repo

- **Dónde:** todo el repo — no hay `tests/`, no hay `pytest` en `requirements.txt`, no hay CI configurado (no existe ningún workflow en `.github/`).
- **Impacto:** no hay red de seguridad contra regresiones, especialmente riesgoso en cálculos astronómicos donde un bug (ej. una casa mal calculada) no es evidente a simple vista y afecta directamente lo que el cliente recibe.
- **Prioridad:** Media — no bloquea nada hoy, pero el riesgo compuesto crece con cada cambio futuro sin cobertura, y es prerrequisito para tocar los god-files con confianza.
- **Esfuerzo:** bajo para arrancar (funciones puras), alto para cobertura completa — no se busca lo segundo de entrada.
- **¿Bloquea funcionalidades futuras?** No bloquea directamente, pero aumenta el costo y riesgo de cualquier refactor de los hallazgos #3 y #4.

### 7. `Base.metadata.create_all()` y Alembic sin una única fuente de verdad

- **Dónde:** `app/main.py` línea 15 (`Base.metadata.create_all(bind=engine)`, ejecutado en cada arranque) conviviendo con `alembic/` como sistema de migraciones versionado.
- **Impacto:** en un entorno completamente nuevo (clon local nuevo, disaster recovery, o un futuro segundo entorno), levantar la app por primera vez crea automáticamente **todas** las columnas actuales del modelo (porque `db_models.py` ya las declara todas). Si después se corre `alembic upgrade head` sobre esa misma base, las migraciones que agregan columnas (`add_column`) fallarán porque esas columnas ya existen — los dos mecanismos de creación de schema no son compatibles entre sí en un arranque desde cero. Hoy "funciona" solo porque la base de datos de cada entorno ya existía antes de que se agregaran las migraciones más recientes.
- **Prioridad:** Media — no afecta el día a día actual, pero es una trampa real para el próximo setup desde cero (nuevo desarrollador, nuevo entorno, recuperación ante desastre).
- **Esfuerzo:** bajo — decidir una única fuente de verdad (recomendado: quitar `create_all()` de `main.py` y depender solo de `alembic upgrade head` como paso de deploy/setup).
- **¿Bloquea funcionalidades futuras?** No bloquea features, pero sí bloquea un onboarding u disaster recovery confiables.

### 8. `requirements.txt` sin versiones pinneadas

- **Dónde:** `requirements.txt`. Pinneados: `weasyprint==69.0`, `alembic==1.18.5`, `email-validator==2.3.0`. Sin pinnear: `fastapi`, `uvicorn`, `pyswisseph`, `pydantic`, `pydantic-settings`, `timezonefinder`, `jinja2`, `anthropic`, `sqlalchemy`, `geopy`, `python-dotenv`, `slowapi`.
- **Impacto:** un `pip install -r requirements.txt` en una fecha distinta puede traer una versión mayor con breaking changes (particularmente riesgoso en `fastapi`, `pydantic` y `anthropic`, que cambian API con frecuencia) sin ningún control ni aviso.
- **Prioridad:** Media.
- **Esfuerzo:** bajo — correr `pip freeze` sobre el entorno que ya funciona y fijar versiones, o migrar a un lockfile (`pip-tools`, `poetry`, `uv`) si se quiere ir más allá de pinning simple.
- **¿Bloquea funcionalidades futuras?** No, pero es la causa más probable de un build roto "sin que nadie haya tocado nada".

### 9. Dockerfile corre como root

- **Dónde:** `Dockerfile` — no hay directiva `USER`, el proceso corre como root dentro del contenedor.
- **Impacto:** endurecimiento estándar de contenedores; si el proceso se compromete, el atacante tiene privilegios de root dentro del contenedor (que en la mayoría de los setups modernos igual está aislado del host, pero es una capa de defensa que falta gratis).
- **Prioridad:** Media.
- **Esfuerzo:** bajo — agregar un usuario no-root y `USER` al final del Dockerfile.
- **¿Bloquea funcionalidades futuras?** No.

### 10. Bloques de instrucción de género duplicados

- **Dónde:** `interpretation_service.py`, 3 apariciones casi idénticas del bloque femenino/masculino/neutro (`_construir_prompt_usuario`, `_construir_prompt_areas_de_vida`, `_construir_prompt_transitos`).
- **Impacto:** si se ajusta la instrucción en un lugar y se olvida en los otros, los 3 flujos de Claude quedan inconsistentes en tono/concordancia entre sí.
- **Prioridad:** Media.
- **Esfuerzo:** trivial — extraer a `_instruccion_genero(genero: str | None) -> str`.
- **¿Bloquea funcionalidades futuras?** No bloquea, pero cada prompt nuevo que copie el bloque (ya pasó 3 veces) aumenta el costo de arreglarlo después.

### 11. Código muerto versionado en la raíz del repo

- **Dónde:** `vista_web.html` (528 líneas), `reporte.html` (279 líneas), `carta_preview.html` (1034 líneas), `borrar_cache.py` (19 líneas) — todos tracked en git en la raíz del proyecto.
- **Impacto:** el propio historial de commits (`4780d33 chore: elimina vista web basada en Jinja2, se reemplaza por frontend JS + endpoint JSON`) confirma que el flujo que estos archivos servían ya fue reemplazado. `borrar_cache.py` es un script ad-hoc de un solo uso con datos de una carta específica hardcodeados. Ninguno de los 4 es importado ni referenciado por `app/`. Generan confusión sobre qué es código vivo.
- **Prioridad:** Baja.
- **Esfuerzo:** trivial — confirmar que nada los referencia (`grep`) y eliminarlos.
- **¿Bloquea funcionalidades futuras?** No, es limpieza pura.

### 12. `app/core/config.py` mezcla `Settings` con constantes de dominio

- **Dónde:** `app/core/config.py` (139 líneas) — `Settings` (config de entorno vía pydantic-settings) y tablas astrológicas estáticas (`PLANETAS`, `SIGNOS`, `DOMICILIOS`, etc.) en el mismo archivo.
- **Prioridad:** Baja — cosmético mientras el archivo no siga creciendo.
- **Esfuerzo:** bajo.
- **¿Bloquea funcionalidades futuras?** No.

### 13. Coincidencia de carta existente por igualdad exacta de floats

- **Dónde:** `persistence_service.buscar_carta_existente` — filtra por `CartaNatalGuardada.latitud == latitud` y `longitud == longitud` (igualdad exacta de `float`).
- **Impacto:** si Nominatim devuelve coordenadas con una precisión ligeramente distinta entre dos consultas para la misma ciudad (actualización del dataset de OSM, redondeo), la misma persona generaría una fila duplicada en vez de reutilizar la carta existente — no se detectaría en tests manuales porque Nominatim suele ser estable para la misma query, pero no está garantizado.
- **Prioridad:** Baja — no hay evidencia de que haya ocurrido, es un riesgo latente.
- **Esfuerzo:** bajo si se decide atacarlo (redondear lat/lon a N decimales antes de guardar/comparar).
- **¿Bloquea funcionalidades futuras?** No.

### 14. `print()` de debug en código productivo

- **Dónde:** `app/services/astro_service.py`, línea 7 (`print(f"[DEBUG] Ruta ephemeris configurada: {_RUTA_EPHE}")`).
- **Prioridad:** Baja.
- **Esfuerzo:** trivial.
- **¿Bloquea funcionalidades futuras?** No.

### 15. Copia de base de datos de producción en desarrollo local

- **Dónde:** `astrea_prod_copy.db` (471 KB) presente en el directorio de trabajo local (correctamente en `.gitignore`, no se sube a git).
- **Impacto:** contiene datos reales de clientes (nombre, email, fecha/hora/lugar de nacimiento) fuera del entorno de producción controlado. No es un hallazgo de código, sino una práctica operativa a revisar — considerar anonimizar o evitar mantener copias completas de producción en local para debugging.
- **Prioridad:** Baja (no bloquea nada técnico), pero vale la pena que quede registrado como nota de higiene de datos.
- **¿Bloquea funcionalidades futuras?** No.

---

## Plan de migración por fases

Coherente con "Objetivo arquitectónico del proyecto" y "Forma de trabajar" en `CLAUDE.md`: sin reescrituras masivas, cada fase deja el sistema funcionando de punta a punta, y una fase habilita a la siguiente con menos riesgo.

### Fase 0 — Contención inmediata

**Objetivo:** eliminar el riesgo activo (#1 y #2) sin tocar arquitectura. Esto no es parte de la migración a Clean Architecture — es un fix de seguridad/costo que no debería esperar a ninguna fase posterior.

- [x] Agregar rate limit a los endpoints públicos costosos que no lo tienen (`/carta-natal/pdf`, `/carta-natal/html`, `/carta-natal/data`, `/carta-natal/compra`).
- [ ] Sacar `/test-*` de producción (flag de entorno, o exigir `verificar_admin_secret`, o eliminarlos si ya no se usan).
- [x] Crear `.dockerignore` (`.env`, `venv/`, `*.db`, `*.pdf`, `.git/`).
- [ ] Eliminar código muerto versionado (#11), ya que es trabajo de minutos y reduce ruido para el resto del plan.

**Criterio de salida:** ningún endpoint público puede disparar una llamada a Claude sin límite; `.env` no puede terminar en una imagen Docker construida a partir de este repo.

### Fase 1 — Cimientos de testing e inyección de dependencias

**Objetivo:** hacer testeable el código antes de reorganizarlo — reduce el riesgo de las fases siguientes. No se toca la estructura de carpetas todavía.

- Inyectar `AsyncAnthropic` como parámetro en las funciones de `interpretation_service.py` (con el singleton actual como default, para no romper los call sites existentes).
- Agregar `pytest` a `requirements.txt` (o a un `requirements-dev.txt` separado) y un comando en `CLAUDE.md`.
- Primeros tests sobre funciones puras que ya están aisladas y no requieren mocks: `astro_service.calcular_casa_natural` / `obtener_signo`, `aspectos_service.detectar_aspecto` / `calcular_todos_los_aspectos`, `dignidades_service.calcular_dignidad`, `regentes_service.calcular_regentes_de_casas`, `resumen_deterministico_service.generar_resumen_deterministico`.

**Criterio de salida:** hay una suite de tests corriendo (aunque chica), y `interpretation_service.py` puede testearse con un cliente Claude mockeado.

**Depende de:** nada — puede empezar en paralelo a la Fase 0.

### Fase 2 — Split de los god-files

**Objetivo:** ejecutar la convención ya decidida por el equipo (`.claude/agents/revisor-endpoint.md`) para las rutas, y aplicar el mismo criterio a `interpretation_service.py`.

- Partir `app/api/endpoints.py` en `app/api/carta_natal.py`, `app/api/admin.py`, `app/api/horoscopos.py`, `app/api/dev_test.py`, moviendo cada endpoint a su archivo de dominio sin cambiar su comportamiento.
- Partir `interpretation_service.py` por caso de uso — como mínimo, separar el bloque compartido (parseo + validación) de los 4 prompts, y evaluar si cada prompt merece su propio módulo.
- Extraer el bloque de instrucción de género duplicado (#10) a un helper compartido, aprovechando que ya se está tocando el archivo.

**Criterio de salida:** ningún archivo de `app/api/` o `app/services/` mezcla responsabilidades que no comparten una única razón de cambio.

**Depende de:** Fase 1 (tener tests hace este split seguro de verificar).

### Fase 3 — Separación explícita dominio/infraestructura

**Objetivo:** introducir las capas conceptuales descritas en "Objetivo arquitectónico del proyecto" (`CLAUDE.md`) como estructura real, migrando de forma incremental — no de una vez.

- Mover cálculo puro sin efectos secundarios (`aspectos_service.py`, `dignidades_service.py`, `regentes_service.py`, la parte de `astro_service.py` que no llama a `swisseph` directamente si se decide aislarlo, `resumen_deterministico_service.py`) hacia un paquete de dominio.
- Mover clientes de infraestructura (Anthropic, Nominatim, el acceso a SQLAlchemy hoy en `persistence_service.py`, WeasyPrint) hacia un paquete de infraestructura.
- Los servicios de aplicación que queden en `app/services/` se convierten en orquestadores finos que llaman dominio + infraestructura, no en el lugar donde vive la lógica.

**Criterio de salida:** el código de dominio no importa nada de FastAPI, SQLAlchemy ni del SDK de Anthropic.

**Depende de:** Fase 2 (mover código ya dividido por responsabilidad es mucho más simple que mover un god-file).

### Fase 4 — Consolidación operativa

**Objetivo:** cerrar los hallazgos de infraestructura/operación que no son arquitectónicos pero sí necesarios para el "nivel profesional" mencionado en el objetivo del proyecto.

- Pinnear versiones en `requirements.txt` (#8) o migrar a un lockfile.
- Agregar usuario no-root al Dockerfile (#9).
- Resolver la coexistencia de `create_all()` y Alembic (#7) — recomendado: `main.py` deja de crear tablas, el setup de cualquier entorno pasa siempre por `alembic upgrade head`.
- Si se decide adoptar CI, este es el punto natural para agregarlo (correr la suite de tests de la Fase 1-2 en cada PR).

**Depende de:** nada estructuralmente, pero tiene más sentido una vez que hay tests (Fase 1) que un CI pueda correr.

---

Ningún ítem de este documento se resuelve en una tarea dedicada a "pagar deuda técnica". Se aborda cada uno cuando una tarea real toca esa zona del código (ver "Forma de trabajar" en `CLAUDE.md`), salvo la Fase 0, que amerita atención inmediata por ser riesgo activo.

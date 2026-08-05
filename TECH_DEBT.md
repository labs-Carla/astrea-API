# TECH_DEBT.md

Auditoría completa de astrea-API y plan de migración incremental hacia el objetivo arquitectónico descrito en `CLAUDE.md`. Este documento es el backlog detallado y priorizado; la sección "Deuda técnica conocida" de `CLAUDE.md` es su resumen operativo de referencia rápida — si diverge de este archivo, este archivo es la fuente de verdad.

**Alcance de la auditoría:** lectura completa de `app/` (api, services, models, core), `alembic/`, `Dockerfile`, `requirements.txt`, `.gitignore`, archivos sueltos en la raíz del repo, y el historial de commits relevante para entender decisiones ya tomadas.

**Cómo se prioriza:** cada hallazgo tiene Impacto, Prioridad (Crítica/Alta/Media/Baja), esfuerzo estimado y si bloquea trabajo futuro. "Crítica" se reserva para riesgo activo en producción (seguridad, costo, pérdida de datos) — se resuelve fuera del roadmap de arquitectura, cuanto antes. El resto se paga de forma incremental, tocando el código por una razón real, nunca en una tarea aislada de "limpieza".

---

## Resumen ejecutivo

| # | Hallazgo | Categoría | Prioridad |
|---|---|---|---|
| 1 | ~~Endpoints públicos sin rate limit ni auth disparan llamadas pagas a Claude sin control~~ | Seguridad / costo | **Resuelto** |
| 2 | ~~Sin `.dockerignore`: `.env` y secretos pueden terminar dentro de la imagen Docker~~ | Seguridad | **Resuelto** |
| 3 | ~~`app/api/endpoints.py` — 591 líneas, todas las rutas del proyecto en un archivo~~ | Arquitectura | **Resuelto** |
| 4 | ~~`app/services/interpretation_service.py` — 563 líneas, 4 responsabilidades mezcladas~~ | Arquitectura | **Resuelto** |
| 5 | ~~`AsyncAnthropic` como singleton de módulo, sin inyección de dependencias~~ | Testabilidad | **Resuelto** |
| 6 | ~~Cero tests en el repo~~ | Testing | **Resuelto** (cobertura inicial) |
| 7 | ~~`Base.metadata.create_all()` y Alembic coexisten sin una única fuente de verdad de schema~~ | Datos | **Resuelto** |
| 8 | ~~`requirements.txt` sin versión pinneada en la mayoría de las dependencias~~ | Operación | **Resuelto** |
| 9 | ~~Dockerfile corre como root, sin usuario no-privilegiado~~ | Seguridad | **Resuelto** |
| 10 | ~~Bloques de instrucción de género duplicados 3 veces en `interpretation_service.py`~~ | Mantenibilidad | **Resuelto** |
| 11 | ~~Código muerto versionado en la raíz del repo~~ | Housekeeping | **Resuelto** |
| 12 | ~~`app/core/config.py` mezcla `Settings` de entorno con constantes astrológicas de dominio~~ | Arquitectura | **Resuelto** |
| 13 | Coincidencia de carta existente por igualdad exacta de floats (lat/lon) | Datos | Baja |
| 14 | ~~`print()` de debug en código productivo (`astro_service.py`)~~ | Housekeeping | **Resuelto** |
| 15 | Copia de base de datos de producción en el entorno de desarrollo local | Datos / privacidad | Baja (operativo) |

---

## Hallazgos detallados

### 1. Endpoints públicos que disparan llamadas pagas a Claude sin control — Resuelto

- **Dónde:** `app/api/carta_natal.py` y `app/api/dev_test.py` (antes, ambos vivían en el ya dividido `app/api/endpoints.py`).
- **Impacto:** resuelto. `/carta-natal/resumen`, `/carta-natal/html`, `/carta-natal/data`, `/carta-natal/pdf` y `/carta-natal/compra` tienen `@limiter.limit("5/minute")`; `/test-interpretacion-completa`, `/test-aspectos` y `/test-dignidades-elementos` ahora exigen `verificar_admin_secret` (mismo patrón que `/admin/*`), en vez de estar abiertos sin control.
- **Prioridad:** Resuelto — ya no hay exposición económica activa sin mitigación.
- **Esfuerzo:** —
- **¿Bloquea funcionalidades futuras?** No.

### 2. Sin `.dockerignore` — Resuelto

- **Dónde:** raíz del repo. Existe `.dockerignore` con `.env`, `venv/`, `*.db`, `*.pdf`, `.git/`, `.github/`, `.claude/` y la documentación de ingeniería.
- **¿Bloquea funcionalidades futuras?** No.

### 3. `app/api/endpoints.py` — Resuelto

- **Dónde:** el god-file de 591 líneas se dividió en `app/api/carta_natal.py`, `app/api/admin.py`, `app/api/horoscopos.py` y `app/api/dev_test.py`, siguiendo la convención ya definida en `CLAUDE.md`. Verificado sin cambios de comportamiento: el `openapi.json` generado es idéntico antes y después del split (mismas 18 rutas, mismos parámetros, mismas dependencias de auth).
- **¿Bloquea funcionalidades futuras?** No.

### 4. `app/services/interpretation_service.py` — Resuelto

- **Dónde:** el god-file de 563 líneas se dividió en `interpretation_common.py` (cliente por defecto, parseo/validación compartidos, `_instruccion_genero`) y un archivo por caso de uso: `interpretation_carta_completa.py`, `interpretation_resumen_gratuito.py`, `interpretation_areas_de_vida.py`, `interpretation_transitos.py`, `interpretation_horoscopos.py`. Verificado sin cambios de comportamiento: los prompts generados son idénticos byte a byte (para los 3 valores de `genero`) antes y después del split, y el `openapi.json` de la app no cambió.
- **¿Bloquea funcionalidades futuras?** No.

### 5. `AsyncAnthropic` como singleton de módulo — Resuelto

- **Dónde:** `app/services/interpretation_common.py` (el singleton, ahora `_client_default`). Cada una de las 5 funciones públicas repartidas en `interpretation_*.py` acepta `client: AsyncAnthropic = _client_default` como parámetro — los call sites existentes en `app/api/` no cambiaron (siguen usando el default).
- **¿Bloquea funcionalidades futuras?** No, ya no bloquea la Fase 1.

### 6. Cero tests en el repo — Resuelto (cobertura inicial)

- **Dónde:** `tests/` con `pytest` + `pytest-asyncio` en `requirements-dev.txt` y `pytest.ini` (`asyncio_mode = auto`, `testpaths = tests`). 31 tests corriendo: `test_interpretation_service.py` cubre las 5 funciones públicas repartidas en `interpretation_*.py` con un cliente Claude mockeado (sin red), y `test_astro_service.py` / `test_aspectos_service.py` / `test_dignidades_service.py` / `test_regentes_service.py` / `test_resumen_deterministico_service.py` cubren todas las funciones de dominio puro del plan de Fase 1.
- **Impacto restante:** no hay tests de integración de endpoints (`app/api/`) ni de `infrastructure/persistence_service.py` — quedan fuera del alcance de Fase 1. La suite ya corre en CI (job `unit-tests`, ver Fase 4).
- **¿Bloquea funcionalidades futuras?** No.

### 7. `Base.metadata.create_all()` y Alembic sin una única fuente de verdad — Resuelto

- **Dónde:** `app/main.py` ya no llama a `create_all()`. `Dockerfile` corre `alembic upgrade head` antes de levantar `uvicorn` en cada arranque del contenedor, para que el schema se gestione exclusivamente vía Alembic también en producción.
- **Hallazgo real, más grave que lo documentado originalmente:** al probar `alembic upgrade head` contra una base de datos vacía (sin `create_all()` corriendo antes), la migración raíz de la cadena (`ebe4e784d7ff`) fallaba con `NoSuchTableError` — no agregaba columnas a una tabla ya creada por Alembic, sino que asumía que `cartas_natales` ya existía (fue escrita cuando la tabla ya existía en producción vía `create_all()`, y esa creación inicial nunca quedó capturada como migración). Es decir: Alembic por sí solo nunca pudo levantar un entorno desde cero, no solo que "competía" con `create_all()`.
- **Fix:** se agregó la migración faltante `cd41b1f78898` (`crea tabla cartas natales base`) al inicio de la cadena, con el schema exacto que tenía la tabla antes de `ebe4e784d7ff` (verificado contra `astrea_prod_copy.db`, una copia de producción de esa época). Verificado programáticamente que `alembic upgrade head` contra una DB nueva reproduce el mismo schema (columnas, tipos, nullability, índices) que `Base.metadata.create_all()` — con una sola diferencia real donde Alembic es más correcto: `enviado` tiene `DEFAULT 0` a nivel de base de datos (así está en la `astrea.db` real), algo que un `create_all()` fresco con el modelo actual no aplica.
- **Incidente real post-deploy (2026-08-04, ~15 min de downtime, 502 en producción):** la verificación de este fix se hizo contra una base de datos vacía y contra una copia de producción vieja (`astrea_prod_copy.db`) — nunca contra el `alembic_version` **real** de producción en el momento del deploy. Producción tenía un segundo gap, distinto del que motivó el fix: su `alembic_version` estaba en `a8a53f98f794` (un paso antes de la migración que crea `horoscopos_generados`), pero esa tabla ya existía físicamente en el volumen — la había creado el viejo `create_all()` en un boot anterior sin que Alembic lo registrara como aplicado. Al sacar `create_all()`, `alembic upgrade head` intentó recrear esa tabla y `sqlite3.OperationalError: table horoscopos_generados already exists` tumbó el contenedor en crash loop. Fix: `alembic stamp head` contra el volumen real de producción (vía `railway ssh`), sin tocar datos ni schema, solo el puntero de versión.
- **Lección para la próxima migración de infraestructura de este tipo:** verificar contra una DB vacía prueba que la cadena de Alembic es *internamente consistente*; no prueba que coincida con el `alembic_version` real de un entorno que vivió parcialmente fuera de Alembic (via `create_all()`) durante años. Antes de sacar cualquier red de seguridad tipo `create_all()`, inspeccionar el `alembic_version` real del entorno de destino (`railway ssh` + `sqlite3`/`python3`, no asumir) y compararlo contra lo que la cadena de migraciones espera en ese punto.
- **¿Bloquea funcionalidades futuras?** No bloquea features, pero destraba onboarding y disaster recovery confiables.

### 8. `requirements.txt` sin versiones pinneadas — Resuelto

- **Dónde:** `requirements.txt` y `requirements-dev.txt`, las 15 + 2 dependencias ahora pinneadas a la versión del entorno que ya funciona (via `pip freeze`). Verificado instalando desde cero en un venv limpio y confirmando que la app importa sin errores.
- **¿Bloquea funcionalidades futuras?** No.

### 9. Dockerfile corre como root — Resuelto

- **Dónde:** `Dockerfile` crea `appuser` (`useradd`), le da ownership de `/app` y agrega `USER appuser` antes del `CMD`. No se pudo correr `docker build` localmente en esta sesión (Docker no disponible en este entorno) — pendiente de confirmar en el job `docker-build` de CI.
- **¿Bloquea funcionalidades futuras?** No.

### 10. Bloques de instrucción de género duplicados — Resuelto

- **Dónde:** extraído a `interpretation_common._instruccion_genero(genero, *, tercera_persona=False)`. Las 2 apariciones idénticas (`interpretar_carta_completa`, `interpretar_areas_de_vida`) y la variante distinta de `interpretar_transitos` (pide tercera persona en vez de prohibir el sustantivo de género) ahora comparten una única función — texto verificado idéntico al original para los 3 valores de `genero` en las 3 llamadas.
- **¿Bloquea funcionalidades futuras?** No.

### 11. Código muerto versionado en la raíz del repo — Resuelto

- **Dónde:** `vista_web.html`, `reporte.html`, `carta_preview.html`, `borrar_cache.py` — eliminados del repo (confirmado sin referencias en `app/` antes de borrarlos). El bloque correspondiente en `.dockerignore` también se quitó por quedar obsoleto.
- **¿Bloquea funcionalidades futuras?** No, era limpieza pura.

### 12. `app/core/config.py` mezcla `Settings` con constantes de dominio — Resuelto

- **Dónde:** `app/core/config.py` ahora solo tiene `Settings` (config de entorno). Las tablas astrológicas estáticas (`PLANETAS`, `SIGNOS`, `DOMICILIOS`, etc.) se movieron a `app/domain/astro_constants.py`.
- **¿Bloquea funcionalidades futuras?** No.

### 13. Coincidencia de carta existente por igualdad exacta de floats

- **Dónde:** `persistence_service.buscar_carta_existente` — filtra por `CartaNatalGuardada.latitud == latitud` y `longitud == longitud` (igualdad exacta de `float`).
- **Impacto:** si Nominatim devuelve coordenadas con una precisión ligeramente distinta entre dos consultas para la misma ciudad (actualización del dataset de OSM, redondeo), la misma persona generaría una fila duplicada en vez de reutilizar la carta existente — no se detectaría en tests manuales porque Nominatim suele ser estable para la misma query, pero no está garantizado.
- **Prioridad:** Baja — no hay evidencia de que haya ocurrido, es un riesgo latente.
- **Esfuerzo:** bajo si se decide atacarlo (redondear lat/lon a N decimales antes de guardar/comparar).
- **¿Bloquea funcionalidades futuras?** No.

### 14. `print()` de debug en código productivo — Resuelto

- **Dónde:** `app/services/astro_service.py` usa `logging.getLogger(__name__).debug(...)` en vez de `print()`. No hay más `print()` en `app/` (verificado con grep).
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
- [x] Sacar `/test-*` de producción (exige `verificar_admin_secret`, mismo patrón que `/admin/*`).
- [x] Crear `.dockerignore` (`.env`, `venv/`, `*.db`, `*.pdf`, `.git/`).
- [x] Eliminar código muerto versionado (#11).

**Criterio de salida:** ningún endpoint público puede disparar una llamada a Claude sin límite; `.env` no puede terminar en una imagen Docker construida a partir de este repo.

### Fase 1 — Cimientos de testing e inyección de dependencias

**Objetivo:** hacer testeable el código antes de reorganizarlo — reduce el riesgo de las fases siguientes. No se toca la estructura de carpetas todavía.

- [x] Inyectar `AsyncAnthropic` como parámetro en las funciones de `interpretation_service.py` (con el singleton actual como default, para no romper los call sites existentes).
- [x] Agregar `pytest` a un `requirements-dev.txt` separado y un comando en `CLAUDE.md`.
- [x] Primer test de `interpretation_service.py` con cliente Claude mockeado (`tests/test_interpretation_service.py`).
- [x] Primeros tests sobre funciones puras que ya están aisladas y no requieren mocks: `astro_service.calcular_casa_natural` / `obtener_signo`, `aspectos_service.detectar_aspecto` / `calcular_todos_los_aspectos`, `dignidades_service.calcular_dignidad`, `regentes_service.calcular_regentes_de_casas`, `resumen_deterministico_service.generar_resumen_deterministico`.
- [x] Replicar el mock de Claude para los 4 casos de uso restantes (`interpretar_carta_completa`, `interpretar_areas_de_vida`, `interpretar_transitos`, `generar_horoscopos`).

**Criterio de salida:** hay una suite de tests corriendo (aunque chica), y `interpretation_service.py` puede testearse con un cliente Claude mockeado. *(cumplido — Fase 1 completa)*

**Depende de:** nada — puede empezar en paralelo a la Fase 0.

### Fase 2 — Split de los god-files — Completa

**Objetivo:** dividir `app/api/endpoints.py` por dominio de rutas, y aplicar el mismo criterio a `interpretation_service.py`.

- [x] Partir `app/api/endpoints.py` en `app/api/carta_natal.py`, `app/api/admin.py`, `app/api/horoscopos.py`, `app/api/dev_test.py`, moviendo cada endpoint a su archivo de dominio sin cambiar su comportamiento.
- [x] Partir `interpretation_service.py` por caso de uso: `interpretation_common.py` (compartido) + un archivo por caso (`interpretation_carta_completa.py`, `interpretation_resumen_gratuito.py`, `interpretation_areas_de_vida.py`, `interpretation_transitos.py`, `interpretation_horoscopos.py`).
- [x] Extraer el bloque de instrucción de género duplicado (#10) a `interpretation_common._instruccion_genero`.

**Criterio de salida:** ningún archivo de `app/api/` o `app/services/` mezcla responsabilidades que no comparten una única razón de cambio. *(cumplido)*

**Depende de:** Fase 1 (tener tests hace este split seguro de verificar).

### Fase 3 — Separación explícita dominio/infraestructura — En progreso

**Objetivo:** introducir las capas conceptuales descritas en "Objetivo arquitectónico del proyecto" (`CLAUDE.md`) como estructura real, migrando de forma incremental — no de una vez.

- [x] Mover cálculo puro sin efectos secundarios (`aspectos_service.py`, `dignidades_service.py`, `regentes_service.py`, `resumen_deterministico_service.py`) a `app/domain/`. Verificado: ninguno de los 4 importa FastAPI, SQLAlchemy ni el SDK de Anthropic.
- [x] Separar `app/core/config.py` (#12): `Settings` de entorno se queda ahí; las constantes astrológicas se mueven a `app/domain/astro_constants.py`, para que el paquete de dominio no dependa de nada relacionado a configuración.
- [ ] Evaluar si aislar la parte de `astro_service.py` que no llama a `swisseph` directamente. **Evaluado (2026-08-05):** de las 7 funciones del archivo, solo 3 son puras (`obtener_signo`, `determinar_casa_natal`, `calcular_casa_natural`, ~50 líneas) y candidatas reales a `app/domain/`. Las otras 4 (`calcular_casas`, `calcular_casa_de_planeta`, `calcular_posiciones_planetarias`, `calcular_posiciones_transito`) intercalan 1-2 llamadas a `swe.*` con formateo de dict en pocas líneas cada una — separarlas exigiría pasar tuplas crudas de swisseph entre capas por una transformación cosmética, exactamente el over-engineering que evita CLAUDE.md "No abstracción especulativa" (#6). Hallazgo colateral más relevante que la arquitectura: esas 4 funciones no tenían ningún test — **cerrado (2026-08-05):** se agregaron 9 tests en `tests/test_astro_service.py` (invariantes astrológicas verificables sin datos hardcodeados, como que la cúspide de Casa 1 es el Ascendente y la de Casa 10 el Medio Cielo, más regresión con valores reales de Swiss Ephemeris para una fecha/lugar fijos — J2000.0 en Buenos Aires). El split en sí sigue diferido — moverlo cuando una tarea real toque el archivo, ya con la cobertura que lo hace seguro de verificar.
- [x] Mover clientes de infraestructura hacia `app/infrastructure/`: `geocoding_service.py` (Nominatim), `persistence_service.py` (acceso a SQLAlchemy) y `pdf_service.py` (WeasyPrint). El cliente de Anthropic queda en `app/services/interpretation_common.py` por ahora — separarlo del resto de `interpretation_*.py` (prompt + llamada mezclados) es la reescritura más grande que evita este horizonte, ver nota abajo. **Evaluado (2026-08-05):** la llamada real al SDK (`client.messages.create`) ocupa 5-8 líneas por archivo (de 69-142 totales); el resto (75-88%) es construcción de prompt. Parseo/validación/costo ya están 100% centralizados en `interpretation_common.py`, y la inyección de `client: AsyncAnthropic` (Fase 1) ya resolvió el problema real de testabilidad — los tests ya mockean el cliente sin red. Partir cada archivo en dos módulos envolvería una llamada de 8 líneas en su propio archivo sin ganancia real. Confirmado como YAGNI — revisar solo si aparece un segundo proveedor de LLM real (regla CLAUDE.md #6).
- [x] Los servicios de aplicación que queden en `app/services/` se convierten en orquestadores finos que llaman dominio + infraestructura, no en el lugar donde vive la lógica. **Resuelto (2026-08-05):** se evaluaron `report_service.py`, `transitos_service.py` y `time_service.py` — ya son orquestadores finos o dominio legítimo (`time_service.py` ya está citado en CLAUDE.md como ejemplo correcto de SRP). El único hallazgo real fue `_calcular_todo` (36 líneas de pipeline de orquestación) viviendo en `app/api/carta_natal.py` en vez de en un servicio, violando la convención propia del proyecto ("Sin lógica de negocio en la función del endpoint"). Se extrajo a `app/services/calculo_carta_service.py::calcular_todo`, sin cambio de comportamiento (verificado: `import app.main` limpio, 34/34 tests en verde).

**Criterio de salida:** el código de dominio no importa nada de FastAPI, SQLAlchemy ni del SDK de Anthropic. *(cumplido para lo ya movido a `app/domain/` y para los orquestadores de `app/services/`; falta separar el cliente de Anthropic de la construcción de prompt en `interpretation_*.py`, confirmado como diferido por YAGNI)*

**Depende de:** Fase 2 (mover código ya dividido por responsabilidad es mucho más simple que mover un god-file).

### Fase 4 — Consolidación operativa — Completa

**Objetivo:** cerrar los hallazgos de infraestructura/operación que no son arquitectónicos pero sí necesarios para el "nivel profesional" mencionado en el objetivo del proyecto.

- [x] Resolver la coexistencia de `create_all()` y Alembic (#7) — `main.py` deja de crear tablas, el setup de cualquier entorno pasa siempre por `alembic upgrade head` (el propio `Dockerfile` ya lo corre antes de arrancar `uvicorn`).
- [x] Pinnear versiones en `requirements.txt` (#8).
- [x] Agregar usuario no-root al Dockerfile (#9).
- [x] Correr la suite de tests (Fase 1) en el pipeline de CI ya existente (`.github/workflows/ci.yml`): nuevo job `unit-tests` corre `pytest`, además de los ya existentes `app-smoke-test` (que ahora corre `alembic upgrade head` antes del boot check, ver #7) y `docker-build`.
- [x] Reemplazar el `print()` de debug en `astro_service.py` por logging real (#14).
- [x] Logging estructurado central (`app/core/logging_config.py`, `setup_logging()` llamado desde `main.py`) y visibilidad de costo/uso de Claude (`interpretation_common._log_uso_claude`, logueado en las 5 llamadas). Estos dos últimos no tenían ítem numerado propio en este documento — estaban solo en el DoD de Horizonte 4 de `ROADMAP.md`.

**Depende de:** nada estructuralmente, pero tiene más sentido una vez que hay tests (Fase 1) que un CI pueda correr.

---

Ningún ítem de este documento se resuelve en una tarea dedicada a "pagar deuda técnica". Se aborda cada uno cuando una tarea real toca esa zona del código (ver "Forma de trabajar" en `CLAUDE.md`), salvo la Fase 0, que amerita atención inmediata por ser riesgo activo.

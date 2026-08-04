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
| 7 | `Base.metadata.create_all()` y Alembic coexisten sin una única fuente de verdad de schema | Datos | Media |
| 8 | `requirements.txt` sin versión pinneada en la mayoría de las dependencias | Operación | Media |
| 9 | Dockerfile corre como root, sin usuario no-privilegiado | Seguridad | Media |
| 10 | ~~Bloques de instrucción de género duplicados 3 veces en `interpretation_service.py`~~ | Mantenibilidad | **Resuelto** |
| 11 | ~~Código muerto versionado en la raíz del repo~~ | Housekeeping | **Resuelto** |
| 12 | ~~`app/core/config.py` mezcla `Settings` de entorno con constantes astrológicas de dominio~~ | Arquitectura | **Resuelto** |
| 13 | Coincidencia de carta existente por igualdad exacta de floats (lat/lon) | Datos | Baja |
| 14 | `print()` de debug en código productivo (`astro_service.py`) | Housekeeping | Baja |
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
- **Impacto restante:** no hay tests de integración de endpoints (`app/api/`) ni de `persistence_service.py` — quedan fuera del alcance de Fase 1, son candidatos naturales para si se agrega CI (Horizonte 4).
- **¿Bloquea funcionalidades futuras?** No.

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
- [ ] Evaluar si aislar la parte de `astro_service.py` que no llama a `swisseph` directamente (queda pendiente por ahora — separarla exigiría partir un módulo ya cohesivo sin una segunda necesidad real, ver CLAUDE.md "No abstracción especulativa").
- [x] Mover clientes de infraestructura hacia `app/infrastructure/`: `geocoding_service.py` (Nominatim), `persistence_service.py` (acceso a SQLAlchemy) y `pdf_service.py` (WeasyPrint). El cliente de Anthropic queda en `app/services/interpretation_common.py` por ahora — separarlo del resto de `interpretation_*.py` (prompt + llamada mezclados) es la reescritura más grande que evita este horizonte, ver nota abajo.
- [ ] Los servicios de aplicación que queden en `app/services/` se convierten en orquestadores finos que llaman dominio + infraestructura, no en el lugar donde vive la lógica.

**Criterio de salida:** el código de dominio no importa nada de FastAPI, SQLAlchemy ni del SDK de Anthropic. *(cumplido para lo ya movido a `app/domain/`; falta el resto de la fase)*

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

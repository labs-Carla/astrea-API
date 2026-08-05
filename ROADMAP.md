# ROADMAP.md

Plan técnico de evolución arquitectónica de Astrea. No es un backlog de funcionalidades ni una lista de tareas — es el mapa de cómo el backend se transforma, de forma incremental y a lo largo de varios años, en la plataforma profesional descrita en el "Objetivo arquitectónico" de `CLAUDE.md`.

## Cómo se relaciona con los otros documentos

- **`CLAUDE.md`** — los principios de ingeniería y el objetivo arquitectónico (el *por qué* y los criterios de decisión del día a día).
- **`TECH_DEBT.md`** — el inventario detallado de deuda ya identificada hoy, con impacto/prioridad por ítem (el *qué está mal, concretamente, ahora mismo*).
- **`ROADMAP.md`** (este documento) — el plan estratégico de varios años que da contexto a por qué existen esas fases y hacia dónde sigue el proyecto después de pagada la deuda actual (el *viaje completo*, no solo el tramo ya mapeado).

Los Horizontes 0 a 4 de este roadmap corresponden 1 a 1 con las Fases 0 a 4 del plan de migración de `TECH_DEBT.md` — mismo trabajo, descrito acá en su contexto estratégico en vez de a nivel de archivo y línea. El Horizonte 5 es terreno nuevo: no es deuda técnica hoy, son límites de diseño que se convertirán en deuda si el producto crece sin atenderlos a tiempo.

## Principio rector

La migración es incremental. Nunca se ejecuta un horizonte completo de una vez ni se detiene el desarrollo de producto para "hacer arquitectura" — cada paso de cada horizonte se ejecuta cuando una tarea real toca esa zona del código (ver "Forma de trabajar" en `CLAUDE.md`), salvo que el propio horizonte marque explícitamente lo contrario.

Cuando dos horizontes o dos decisiones dentro de un horizonte compiten por atención, el orden de prioridad es siempre:

**Seguridad → Mantenibilidad → Testabilidad → Escalabilidad → Rendimiento**

Esto no es arbitrario: un sistema inseguro pone en riesgo el negocio antes que cualquier otra cosa; un sistema no mantenible hace que todo lo demás (incluida la seguridad futura) sea cada vez más caro de sostener; sin testabilidad, cualquier cambio de mantenibilidad es una apuesta; y no tiene sentido optimizar escalabilidad o rendimiento de un sistema que todavía no está probado ni es seguro escalar.

## Mapa de horizontes

| Horizonte | Foco principal | Qué desbloquea |
|---|---|---|
| 0 — Base segura | Seguridad | Que el resto del roadmap se ejecute sin riesgo activo de fondo |
| 1 — Cimientos de testabilidad | Mantenibilidad, Testabilidad | Que los refactors de los horizontes siguientes sean seguros de verificar |
| 2 — Modularización por dominio | Mantenibilidad | Que el código tenga límites claros antes de formalizar capas |
| 3 — Clean Architecture explícita | Mantenibilidad, Testabilidad | Que dominio e infraestructura puedan evolucionar y reemplazarse por separado |
| 4 — Consolidación operativa y observabilidad | Seguridad, Mantenibilidad | Que los problemas se detecten solos y cada cambio se valide automáticamente |
| 5 — Escalabilidad y rendimiento bajo crecimiento real | Escalabilidad, Rendimiento | Que el sistema absorba crecimiento de tráfico y datos sin degradarse ni reescribirse |

---

## Horizonte 0 — Base segura

**Prioridad que atiende:** Seguridad, ante todo.

**Objetivo.** Eliminar el riesgo activo de seguridad y de costo antes de invertir cualquier esfuerzo en arquitectura.

**Justificación.** No tiene sentido migrar hacia Clean Architecture mientras existen endpoints capaces de generar costo de IA sin límite, o secretos que pueden filtrarse en una imagen de Docker. La seguridad no es un horizonte más entre otros — es la precondición para que el resto del roadmap tenga sentido invertirlo.

**Problemas que resuelve.** `TECH_DEBT.md` #1 (endpoints públicos sin rate limit ni auth que disparan llamadas pagas a Claude) y #2 (ausencia de `.dockerignore`, riesgo de fuga de `.env` en la imagen).

**Dependencias.** Ninguna — es el punto de partida del roadmap.

**Criterios de entrada.** Ninguno — se ejecuta de inmediato, en paralelo a cualquier trabajo de producto en curso.

**Definition of Done.**
- Ningún endpoint público puede disparar una llamada a Claude sin límite de frecuencia.
- Los endpoints `/test-*` no están accesibles sin autenticación en producción.
- Existe `.dockerignore` y se verificó que un build desde cero no incluye `.env` ni artefactos sensibles.

**Riesgos.** Que se subestime la urgencia por no bloquear ninguna funcionalidad visible para el usuario, y se postergue indefinidamente mientras el riesgo sigue activo. Mitigación: tratarlo como incidente de seguridad a resolver en días, no como ítem de backlog.

**Impacto esperado.** Elimina la exposición financiera y de secretos más severa del sistema, con un esfuerzo de horas — la mejor relación impacto/costo de todo el roadmap.

---

## Horizonte 1 — Cimientos de testabilidad

**Prioridad que atiende:** Mantenibilidad y Testabilidad.

**Objetivo.** Hacer el código testeable e introducir inyección de dependencias donde bloquea testing, antes de reorganizar ninguna estructura de archivos.

**Justificación.** Todo refactor de los horizontes siguientes (dividir archivos, mover código a capas) es una apuesta sin una red de tests que confirme que el comportamiento no cambió. Construir esa red primero reduce el riesgo compuesto de todo lo que viene después, en vez de intentar testear y refactorizar al mismo tiempo.

**Problemas que resuelve.** `TECH_DEBT.md` #5 (`AsyncAnthropic` como singleton sin inyección, bloquea mockear el proveedor de IA en tests) y #6 (cero tests en el repo).

**Dependencias.** Ninguna estructural — puede ejecutarse en paralelo al Horizonte 0, ya que no tocan los mismos archivos.

**Criterios de entrada.** Ninguno estricto, pero se recomienda no dejarlo esperando a que el Horizonte 0 cierre formalmente — ambos pueden avanzar a la vez.

**Definition of Done.**
- El cliente de Claude es inyectable como parámetro en `interpretation_service.py`, con el singleton actual como valor por defecto (sin romper los call sites existentes).
- Existe una suite de tests corriendo localmente, con al menos las funciones de dominio puro cubiertas (cálculo de aspectos, dignidades, regentes, casa natural, resumen determinístico).
- Es posible testear la construcción de un prompt y el parseo de una respuesta de Claude sin llamar a la API real.

**Riesgos.** Escribir tests solo para "tener cobertura" en lugar de cubrir el código de mayor riesgo real del producto (`interpretation_service.py`, que es lo que el cliente paga). Mitigación: priorizar explícitamente ese archivo apenas sea inyectable, no dejarlo para el final por ser el más grande.

**Impacto esperado.** A partir de este horizonte, cualquier refactor posterior deja de ser un acto de fe — hay una forma objetiva de verificar que el comportamiento se preservó.

---

## Horizonte 2 — Modularización por dominio

**Prioridad que atiende:** Mantenibilidad.

**Objetivo.** Dividir los dos god-files del proyecto (`app/api/endpoints.py` y `app/services/interpretation_service.py`) siguiendo la convención de dominio ya acordada por el equipo, logrando que cada archivo tenga una única razón de cambio.

**Justificación.** Son los dos archivos que concentran más responsabilidades mezcladas y más riesgo de conflicto entre cambios paralelos. Con la red de tests del Horizonte 1 ya en pie, dividirlos es un cambio mecánico de bajo riesgo — sin ella, sería un refactor a ciegas sobre el código más crítico del negocio.

**Problemas que resuelve.** `TECH_DEBT.md` #3 (`endpoints.py`, 591 líneas, todas las rutas mezcladas), #4 (`interpretation_service.py`, 563 líneas, 4 responsabilidades) y #10 (bloques de instrucción de género duplicados 3 veces).

**Dependencias.** Horizonte 1 — dividir sin tests que confirmen equivalencia de comportamiento es exactamente el tipo de refactor riesgoso que este roadmap busca evitar.

**Criterios de entrada.** La suite de tests del Horizonte 1 cubre al menos los flujos principales de carta natal (cálculo, resumen, interpretación) y de horóscopos.

**Definition of Done.**
- Las rutas están distribuidas en `app/api/carta_natal.py`, `admin.py`, `horoscopos.py` y `dev_test.py`, según la convención ya definida en `.claude/agents/revisor-endpoint.md`, sin cambios de comportamiento.
- `interpretation_service.py` está dividido de forma que ningún archivo mezcle construcción de prompt, llamada a Claude, parseo y validación para más de un caso de uso a la vez.
- El bloque de instrucción de género vive en una única función compartida.
- Ningún archivo de `app/api/` o `app/services/` mezcla responsabilidades que no comparten una única razón de cambio.

**Riesgos.** Hacer el split "a medias" — dejar código repartido entre el archivo viejo y el nuevo por un tiempo prolongado, aumentando la confusión en vez de reducirla. Mitigación: mover un endpoint o un prompt completo por vez, nunca dejar referencias cruzadas a mitad de camino entre commits.

**Impacto esperado.** El costo de agregar o modificar un endpoint o un prompt baja de forma sostenida; los límites de dominio quedan visibles en el filesystem, no solo en la cabeza de quien escribió el código.

---

## Horizonte 3 — Clean Architecture explícita

**Prioridad que atiende:** Mantenibilidad y Testabilidad, sentando la base para Escalabilidad.

**Objetivo.** Introducir como estructura real de carpetas las capas conceptuales ya descritas en "Objetivo arquitectónico del proyecto" de `CLAUDE.md`: dominio, aplicación e infraestructura, con dirección de dependencias verificable.

**Justificación.** Es el objetivo arquitectónico declarado del proyecto. Una vez que el código está dividido por responsabilidad (Horizonte 2) y cubierto por tests (Horizonte 1), moverlo a capas explícitas es un cambio de bajo riesgo técnico y alto valor a largo plazo — es la diferencia entre "el código está ordenado" y "el código no puede volver a desordenarse sin que alguien lo note".

**Problemas que resuelve.** `TECH_DEBT.md` #12 (`config.py` mezclando configuración de entorno con constantes de dominio) y, de forma más amplia, hace cumplible en la práctica el principio de "Dirección de dependencias" de `CLAUDE.md`, hoy solo aspiracional para el límite dominio/infraestructura.

**Dependencias.** Horizonte 2 — mover código ya dividido por responsabilidad a su capa correspondiente es mucho más simple y seguro que intentar mover un god-file de una vez.

**Criterios de entrada.** Los god-files del Horizonte 2 ya están divididos por dominio.

**Definition of Done.**
- Existe un paquete de dominio (cálculo astrológico puro, reglas del funnel de una carta) que no importa nada de FastAPI, SQLAlchemy ni del SDK de Anthropic.
- Existe un paquete de infraestructura que concentra los detalles externos reemplazables (Anthropic, Nominatim, SQLAlchemy, WeasyPrint, Swiss Ephemeris).
- Los servicios de aplicación que quedan son orquestadores finos que llaman a dominio e infraestructura, no el lugar donde vive la lógica de negocio. *(cumplido — ver TECH_DEBT.md Fase 3; queda pendiente, deliberadamente diferido por YAGNI, separar el cliente de Anthropic de la construcción de prompt en `interpretation_*.py`)*
- `app/core/config.py` separa configuración de entorno de constantes de dominio.

**Riesgos.** Sobre-diseñar la separación antes de tiempo: crear interfaces o capas vacías sin una segunda implementación real que las justifique. Mitigación: aplicar el mismo criterio YAGNI de `CLAUDE.md` — mover código real que ya existe, no construir estructura especulativa para un futuro hipotético.

**Impacto esperado.** El dominio (reglas astrológicas, reglas de negocio del funnel de venta) queda protegido de cambios en proveedores externos. Es la condición necesaria para poder cambiar de proveedor de LLM, de geocodificación o de motor de base de datos sin reescribir lógica de negocio — y para que un equipo más grande pueda trabajar en paralelo sin pisarse.

---

## Horizonte 4 — Consolidación operativa y observabilidad — Completo

**Prioridad que atiende:** Seguridad y Mantenibilidad, preparando el terreno para Escalabilidad.

**Objetivo.** Cerrar los hallazgos de infraestructura y operación que no son arquitectónicos pero sí necesarios para sostener el proyecto de forma profesional, y ganar visibilidad real de lo que pasa en producción.

**Justificación.** Un backend que va a crecer durante varios años necesita que los problemas se detecten antes de que el cliente los reporte, que cada cambio se valide automáticamente antes de llegar a producción, y que el schema de datos tenga una única fuente de verdad. Ninguno de estos ítems requiere que la arquitectura esté terminada — pueden avanzar en paralelo a los Horizontes 2 y 3.

**Problemas que resuelve.** `TECH_DEBT.md` #7 (`create_all()` y Alembic sin fuente única de verdad), #8 (dependencias sin pinnear), #9 (Docker corriendo como root) y #14 (`print()` de debug en vez de logging real). Además, extiende ese trabajo con dos capacidades que hoy no existen: logging estructurado y visibilidad de costo/uso de la API de Claude (crítico en un producto que paga por llamada a un LLM).

**Dependencias.** Horizonte 1 — un pipeline de CI necesita una suite de tests real para tener sentido; sin eso, correr CI es solo teatro.

**Criterios de entrada.** Ninguno estricto más allá de la suite de tests del Horizonte 1 — es transversal, no bloquea ni es bloqueado por los Horizontes 2 y 3.

**Definition of Done.**
- [x] `main.py` deja de crear tablas automáticamente; el setup de cualquier entorno pasa siempre por `alembic upgrade head`.
- [x] Las dependencias en `requirements.txt` están pinneadas (o migradas a un lockfile).
- [x] El contenedor corre con un usuario no privilegiado.
- [x] Hay logging estructurado reemplazando los `print()` de debug — `app/core/logging_config.py` (`setup_logging()`, llamado una vez desde `main.py`).
- [x] Hay visibilidad (aunque sea básica) de cuánto cuesta en tokens/USD cada tipo de llamada a Claude — `interpretation_common._log_uso_claude`, logueado en cada una de las 5 llamadas.
- [x] Existe un pipeline de CI que corre la suite de tests en cada cambio propuesto.

**Riesgos.** Tratar este horizonte como "nice to have" indefinidamente por no bloquear features nuevas, postergándolo sin fecha. Mitigación: ejecutarlo en paralelo a los Horizontes 2-3 desde el principio, no como algo para "cuando haya tiempo".

**Impacto esperado.** El tiempo de detección de bugs e incidentes baja de días a minutos; hay datos reales de costo de IA para decisiones de producto y pricing; un despliegue desde cero deja de ser un riesgo de inconsistencia de schema.

---

## Horizonte 5 — Escalabilidad y rendimiento bajo crecimiento real

**Prioridad que atiende:** Escalabilidad y Rendimiento — deliberadamente los últimos en la lista de prioridades.

**Objetivo.** Preparar el sistema para picos de tráfico y crecimiento de datos sin degradar la experiencia del cliente ni el costo operativo, cuando la evidencia de crecimiento lo justifique.

**Justificación.** Hoy las 4 llamadas a Claude se ejecutan de forma síncrona dentro del ciclo request-response (quien pide un PDF completo espera minutos con la conexión abierta), el rate limiting vive en memoria de proceso (no sobrevive a más de una instancia del backend), y SQLite tiene un único escritor concurrente. Ninguno de estos tres puntos es un problema con el volumen actual — pero los tres se convertirán en deuda técnica real si el producto crece sin haberlos anticipado. Este horizonte existe para que esa transición sea planeada y no una emergencia.

**Problemas que resuelve.** Ninguno está en `TECH_DEBT.md` hoy, precisamente porque no son deuda todavía — son límites de diseño conocidos y aceptados mientras el volumen actual los sostenga.

**Dependencias.** Horizonte 3 — introducir una cola de trabajos asíncronos o cambiar el motor de base de datos es mucho más simple cuando la infraestructura ya está separada del dominio; hacerlo antes significaría tocar lógica de negocio mezclada con detalles de implementación.

**Criterios de entrada — este horizonte no se activa por calendario, sino por señales concretas de crecimiento.** Ejemplos de disparadores válidos: el tiempo de espera en `/carta-natal/pdf` se vuelve un problema de producto reportado por usuarios; se planea desplegar más de una instancia del backend (el rate limiting en memoria deja de ser confiable); se observan errores de "database is locked" por escrituras concurrentes en SQLite. Sin al menos una de estas señales, ejecutar este horizonte es complejidad prematura.

**Definition of Done.**
- Las llamadas costosas a Claude no bloquean el ciclo request-response del cliente (patrón de job asíncrono con polling o webhook, en vez de un `await` directo dentro del handler HTTP).
- El rate limiting sobrevive a múltiples instancias del backend (backend distribuido, ej. Redis, en vez de memoria de proceso).
- Existe un plan de migración de datos probado — no necesariamente ejecutado de antemano — de SQLite a un motor con mejor concurrencia de escritura (ej. PostgreSQL), listo para activarse cuando el disparador correspondiente ocurra.

**Riesgos.** El riesgo dominante de este horizonte es ejecutarlo antes de tiempo: introducir colas de trabajos, infraestructura distribuida o Postgres cuando SQLite y las llamadas síncronas todavía son suficientes, agregando complejidad operativa sin necesidad real. Por eso este horizonte, a diferencia de los anteriores, tiene criterios de entrada basados en señales de negocio y no solo en dependencias técnicas.

**Impacto esperado.** El sistema deja de degradarse bajo carga creciente; escalar deja de requerir una reescritura y pasa a ser una extensión sobre una base ya preparada para eso.

---

## Cómo evoluciona este documento

Este roadmap no es un contrato fijo. Se revisa cuando la realidad del proyecto cambia lo suficiente como para invalidar una justificación, una dependencia o un criterio de entrada — por ejemplo, si aparece una señal de crecimiento que activa el Horizonte 5 antes de lo previsto, o si un nuevo hallazgo en `TECH_DEBT.md` cambia la prioridad relativa de un horizonte. Cuando eso pase, se actualiza este documento explícitamente en vez de desviarse de él en silencio — el mismo criterio de "Forma de trabajar" que aplica al código aplica a su propio roadmap.

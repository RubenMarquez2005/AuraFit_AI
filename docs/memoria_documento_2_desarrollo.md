# Memoria TFG - Documento 2

## Desarrollo

Este documento corresponde al apartado central de la memoria. Incluye fundamentacion teorica, materiales y metodos, resultados y analisis, con nivel de detalle tecnico orientado a defensa academica.

### Version breve del desarrollo

Se implementa una arquitectura por capas (Flutter + FastAPI + RASA + MySQL), se construyen flujos completos de paciente y profesional, se incorpora trazabilidad clinica avanzada y se valida la calidad con pruebas automatizadas en rutas criticas.

### Desarrollo amplio

El desarrollo se ejecuta por bloques incrementalmente validados. Cada bloque se cierra con una de estas evidencias:

- disponibilidad funcional en UI o endpoint,
- verificacion de permisos por rol,
- persistencia en base de datos,
- evidencia de ejecucion y/o test.

---

## 1. Fundamentacion teorica

### 1.1 Enfoque arquitectonico

AuraFit AI utiliza una arquitectura por capas para desacoplar responsabilidades y facilitar evolucion:

1. Capa de presentacion (Flutter).
- Gestiona experiencia de usuario.
- Consume API HTTP.
- Organiza navegacion y secciones por contexto.

2. Capa de negocio (FastAPI).
- Centraliza reglas de dominio.
- Valida autenticacion y autorizacion.
- Aplica controles de seguridad por rol.

3. Capa NLU (RASA).
- Procesa lenguaje natural.
- Extrae intenciones y entidades.
- Permite explicabilidad por entrenamiento local.

4. Capa de persistencia (MySQL + SQLAlchemy).
- Estructura entidades relacionales.
- Conserva historico de seguimiento y auditoria.

Principios aplicados:

- separacion de responsabilidades,
- trazabilidad de decisiones,
- validacion de entrada,
- seguridad server-side,
- evolucion incremental con evidencia.

### 1.2 Marco teorico funcional

El sistema se diseña sobre tres conceptos:

1. Continuidad asistencial.
- El dato no termina en almacenamiento, se convierte en accion de seguimiento.

2. Interdisciplinariedad.
- Se habilitan derivaciones entre perfiles para coordinacion real.

3. Trazabilidad clinica.
- Los cambios relevantes se versionan y se auditan.

### 1.3 Tecnologias y justificacion

- Flutter: unifica interfaz en web y macOS, acelerando iteracion visual.
- FastAPI: tipado fuerte, alta productividad, Swagger automatico.
- SQLAlchemy: modelado robusto con relaciones explicitas.
- Pydantic: contratos y validacion de payloads.
- MySQL: persistencia estable y conocida en entorno formativo/profesional.
- RASA: NLU local con control de datos y reproducibilidad.
- FPDF: export documental de casos en formato estandar.

### 1.4 Seguridad y gobernanza

La frontera de seguridad se define en backend:

- token Bearer obligatorio en rutas protegidas,
- validacion de rol por endpoint,
- restriccion de acciones sensibles,
- alta profesional con clave privada.

Este criterio evita delegar seguridad en decisiones visuales del frontend.

---

## 2. Materiales y metodos

### 2.1 Materiales de desarrollo

- Sistema operativo de trabajo: macOS.
- IDE principal: Visual Studio Code.
- Lenguaje backend: Python.
- Framework backend: FastAPI.
- ORM: SQLAlchemy.
- Frontend: Flutter.
- Motor NLU: RASA.
- Base de datos: MySQL.
- Pruebas: unittest y TestClient.
- Versionado: Git/GitHub.

### 2.2 Metodo de implementacion

Se siguio una estrategia incremental por bloques:

1. Consolidar estructura base de repositorio.
2. Levantar backend con conexion DB y modelos nucleares.
3. Implementar autenticacion y sesiones.
4. Integrar frontend con backend.
5. Implementar modulos paciente.
6. Implementar modulos profesional.
7. Añadir capa hospitalaria (protocolos, checklist, auditoria, PDF).
8. Integrar NLU RASA y flujos conversacionales.
9. Validar con pruebas y ampliar documentacion.

#### Metodo de control de cambios

Para evitar regresiones durante el crecimiento funcional, se aplica:

- desarrollo por dominio (auth, seguimiento, profesional, hospitalario),
- validacion tras cada bloque,
- refuerzo documental continuo en bitacora y memoria.

### 2.3 Estructura del proyecto (inventario real)

#### 2.3.1 Frontend

Mapa principal de frontend:

- [frontend/lib/main.dart](frontend/lib/main.dart)
- [frontend/lib/config/app_colors.dart](frontend/lib/config/app_colors.dart)
- [frontend/lib/services/backend_service.dart](frontend/lib/services/backend_service.dart)
- [frontend/lib/providers/auth_provider.dart](frontend/lib/providers/auth_provider.dart)
- [frontend/lib/providers/chat_provider.dart](frontend/lib/providers/chat_provider.dart)
- [frontend/lib/providers/assessment_provider.dart](frontend/lib/providers/assessment_provider.dart)
- [frontend/lib/widgets/patient_support_form_card.dart](frontend/lib/widgets/patient_support_form_card.dart)
- [frontend/lib/widgets/section_ai_gate.dart](frontend/lib/widgets/section_ai_gate.dart)

Paginas funcionales:

- [frontend/lib/pages/auth_page.dart](frontend/lib/pages/auth_page.dart)
- [frontend/lib/pages/home_page.dart](frontend/lib/pages/home_page.dart)
- [frontend/lib/pages/nutrition_page.dart](frontend/lib/pages/nutrition_page.dart)
- [frontend/lib/pages/gym_page.dart](frontend/lib/pages/gym_page.dart)
- [frontend/lib/pages/mental_health_page.dart](frontend/lib/pages/mental_health_page.dart)
- [frontend/lib/pages/habits_page.dart](frontend/lib/pages/habits_page.dart)
- [frontend/lib/pages/evolution_page.dart](frontend/lib/pages/evolution_page.dart)
- [frontend/lib/pages/statistics_page.dart](frontend/lib/pages/statistics_page.dart)
- [frontend/lib/pages/report_page.dart](frontend/lib/pages/report_page.dart)
- [frontend/lib/pages/resources_page.dart](frontend/lib/pages/resources_page.dart)
- [frontend/lib/pages/chat_page.dart](frontend/lib/pages/chat_page.dart)
- [frontend/lib/pages/admin_panel.dart](frontend/lib/pages/admin_panel.dart)

#### 2.3.2 Backend

Archivos troncales backend:

- [backend/main.py](backend/main.py)
- [backend/app/api/auth.py](backend/app/api/auth.py)
- [backend/app/services/auth_service.py](backend/app/services/auth_service.py)
- [backend/services/rasa_service.py](backend/services/rasa_service.py)
- [backend/services/gemini_service.py](backend/services/gemini_service.py)
- [backend/app/models/database.py](backend/app/models/database.py)
- [backend/app/config/settings.py](backend/app/config/settings.py)
- [backend/requirements.txt](backend/requirements.txt)

#### 2.3.3 Base de datos y scripts

- [database/db_AuraFIT.sql](database/db_AuraFIT.sql)

#### 2.3.4 Pruebas automatizadas

- [backend/tests/test_rbac_clinico.py](backend/tests/test_rbac_clinico.py)
- [backend/tests/test_cita_nutricion.py](backend/tests/test_cita_nutricion.py)

### 2.4 Modelo de datos y dominio

Entidades principales implementadas:

- Rol
- Usuario
- PerfilSalud
- RegistroDiario
- Derivacion
- HabitoAgenda
- EvaluacionIA
- MensajeChat
- MedicacionAsignada
- PlanNutricionalClinico
- ProtocoloHospitalario
- ChecklistClinicoPaciente
- ChecklistClinicoHistorial
- RecursoClinico

Justificacion del modelo:

- separar datos de identidad y datos clinicos,
- permitir seguimiento temporal,
- permitir coordinacion entre especialidades,
- conservar historico auditable.

### 2.5 Casos de uso y flujos

#### 2.5.1 Casos de uso del paciente

- Registrarse e iniciar sesion.
- Completar perfil de salud.
- Consultar IMC y estado asociado.
- Solicitar cita nutricional.
- Registrar check-in diario.
- Consultar derivaciones.
- Interactuar con modulo conversacional.

#### 2.5.2 Casos de uso profesional

- Consultar pacientes asignados.
- Revisar KPIs y evolucion.
- Gestionar medicacion.
- Gestionar plan nutricional.
- Emitir derivaciones.
- Recibir y actualizar derivaciones.
- Gestionar protocolos y checklist.
- Consultar auditoria de checklist.
- Consultar severidad sugerida.
- Descargar informe hospitalario PDF.

#### 2.5.3 Flujo critico A: IMC -> cita nutricional

1. Paciente registra metricas.
2. Backend calcula IMC.
3. UI muestra estado IMC.
4. Paciente solicita cita.
5. Backend valida rol paciente.
6. Backend crea o reutiliza derivacion abierta.
7. Profesional visualiza derivacion en bandeja.

#### 2.5.4 Flujo critico B: checklist + auditoria

1. Profesional selecciona paciente y contexto clinico.
2. Edita checklist y escalado.
3. Backend guarda checklist actual.
4. Backend genera snapshot versionado.
5. Auditoria muestra timeline de cambios.

#### 2.5.5 Flujo critico C: severidad sugerida

1. Backend agrega KPIs clinicos.
2. Calcula puntuacion de riesgo.
3. Devuelve severidad + motivos.
4. Profesional toma decision final.

### 2.6 Inventario de API (detalle completo)

#### 2.6.1 Autenticacion y sesion

- POST /login
- POST /register
- POST /register-profesional
- GET /roles
- GET /me
- POST /reset-password

#### 2.6.2 Chat y evaluacion IA

- POST /chat/test
- POST /chat
- GET /chat/historial
- DELETE /chat/historial
- POST /chat/rasa

#### 2.6.3 Perfil y metricas

- POST /perfil/completar
- PATCH /perfil/metricas-imc
- GET /perfil/resumen

#### 2.6.4 Evaluaciones por seccion

- GET /evaluaciones/ia
- PUT /evaluaciones/ia/{seccion}
- DELETE /evaluaciones/ia/{seccion}

#### 2.6.5 Seguimiento emocional y reportes

- GET /usuarios/grafica-animo
- GET /usuarios/informe-pdf
- POST /seguimiento/checkin
- GET /seguimiento/resumen-semanal
- GET /seguimiento/historico
- GET /seguimiento/racha

#### 2.6.6 Habitos

- GET /habitos/agenda
- PATCH /habitos/agenda/{habito_id}

#### 2.6.7 Profesional: pacientes, KPIs y medicacion

- GET /profesionales/pacientes
- GET /profesionales/pacientes/{paciente_id}/kpis
- GET /profesionales/pacientes/{paciente_id}/medicacion
- POST /profesionales/pacientes/{paciente_id}/medicacion
- PATCH /profesionales/medicacion/{medicacion_id}/estado

#### 2.6.8 Profesional: plan nutricional

- GET /profesionales/pacientes/{paciente_id}/plan-nutricional
- PUT /profesionales/pacientes/{paciente_id}/plan-nutricional

#### 2.6.9 Profesional: protocolos, checklist, auditoria, severidad, PDF

- GET /profesionales/protocolos-hospitalarios
- PUT /profesionales/protocolos-hospitalarios
- GET /profesionales/pacientes/{paciente_id}/checklist-clinico
- PUT /profesionales/pacientes/{paciente_id}/checklist-clinico
- GET /profesionales/pacientes/{paciente_id}/checklist-clinico/auditoria
- GET /profesionales/pacientes/{paciente_id}/severidad-sugerida
- GET /profesionales/pacientes/{paciente_id}/informe-hospitalario-pdf

#### 2.6.10 Profesional: recursos y derivaciones

- GET /profesionales/recursos-clinicos
- POST /profesionales/recursos-clinicos
- GET /profesionales/asignado
- POST /profesionales/derivaciones
- GET /profesionales/derivaciones/recibidas
- PATCH /profesionales/derivaciones/{derivacion_id}/estado

#### 2.6.11 Paciente: derivaciones

- POST /pacientes/solicitar-cita-nutricion
- GET /pacientes/derivaciones
- PATCH /pacientes/derivaciones/{derivacion_id}/leida

#### 2.6.12 Salud del sistema

- GET /
- GET /health
- GET /health/db

### 2.7 Metodo de validacion aplicado

Validaciones ejecutadas:

- prueba de endpoints en Swagger,
- prueba funcional frontend-backend,
- prueba de integracion backend-RASA,
- prueba de permisos por rol,
- prueba de flujo IMC -> cita.

Pruebas automatizadas:

- [backend/tests/test_rbac_clinico.py](backend/tests/test_rbac_clinico.py)
- [backend/tests/test_cita_nutricion.py](backend/tests/test_cita_nutricion.py)

Comando ejecutado:

/Users/rubenperez/Documents/AuraFit_AI/backend/venv/bin/python -m unittest tests.test_rbac_clinico tests.test_cita_nutricion -v

Resultado observado:

- 9 pruebas ejecutadas,
- 9 pruebas superadas.

### 2.8 Problemas encontrados (muy detallado)

Esta seccion documenta incidencias reales del proyecto con foco en causa, impacto, solucion y evidencia de cierre.

#### Problema 1. Fragmentacion funcional entre modulos

- Sintoma:
	- funcionalidades aisladas sin continuidad clara entre paciente y profesional.
- Causa raiz:
	- crecimiento inicial por componentes sueltos sin circuito completo.
- Impacto:
	- baja accionabilidad y experiencia inconexa.
- Solucion aplicada:
	- rediseño de flujos end-to-end (IMC -> cita -> bandeja profesional).
- Evidencia de cierre:
	- rutas de derivacion paciente/profesional activas y panel clinico operativo.

#### Problema 2. Riesgo de escalado de privilegios en registro

- Sintoma:
	- posibilidad teorica de alta de especialistas en flujo publico.
- Causa raiz:
	- necesidad de separar claramente registro publico y privado.
- Impacto:
	- riesgo funcional de acceso indebido a operaciones profesionales.
- Solucion aplicada:
	- registro publico forzado a paciente + alta profesional con clave privada.
- Evidencia de cierre:
	- endpoints diferenciados de registro y validacion de rol en backend.

#### Problema 3. Dependencias Python inestables en distintas fases

- Sintoma:
	- errores de instalacion/ejecucion por conflicto de versiones.
- Causa raiz:
	- heterogeneidad de dependencias de servicios y entornos.
- Impacto:
	- bloqueos puntuales en pruebas y arranque.
- Solucion aplicada:
	- saneado de entorno virtual y fijacion de versiones compatibles.
- Evidencia de cierre:
	- backend ejecutando y pruebas en verde.

#### Problema 4. Riesgo de decisiones clinicas sin trazabilidad temporal

- Sintoma:
	- el estado actual del checklist no explicaba historia de cambios.
- Causa raiz:
	- ausencia inicial de tabla historica.
- Impacto:
	- dificultad para justificar intervenciones ante revision.
- Solucion aplicada:
	- creacion de checklist versionado y endpoint de auditoria.
- Evidencia de cierre:
	- consulta temporal de versiones por paciente.

#### Problema 5. Duplicidad potencial en solicitud de cita nutricional

- Sintoma:
	- riesgo de crear derivaciones repetidas para un mismo caso abierto.
- Causa raiz:
	- flujo paciente repetible sin filtro de estado inicial.
- Impacto:
	- ruido en bandeja profesional y perdida de claridad operativa.
- Solucion aplicada:
	- logica anti-duplicado que reutiliza derivacion abierta.
- Evidencia de cierre:
	- prueba automatizada dedicada en test_cita_nutricion.

#### Problema 6. Mezcla de orden y jerarquia visual entre pantallas

- Sintoma:
	- pantallas con secciones en orden dispar y densidad visual desigual.
- Causa raiz:
	- crecimiento rapido de UI por funcionalidades.
- Impacto:
	- percepcion de desorden y peor legibilidad clinica.
- Solucion aplicada:
	- reorganizacion global por bloques y ancho maximo consistente.
- Evidencia de cierre:
	- home y panel profesional reestructurados por secciones.

#### Problema 7. Dependencia de motor conversacional sin gobernanza documental

- Sintoma:
	- riesgo de no poder justificar evolucion de NLU ante tribunal.
- Causa raiz:
	- ausencia inicial de protocolo de validacion ampliado.
- Impacto:
	- defensa mas debil en apartado IA.
- Solucion aplicada:
	- ampliacion de documento RASA con criterios de validacion y gobernanza.
- Evidencia de cierre:
	- documento de validacion RASA extendido y alineado a memoria.

#### Problema 8. Permisos cruzados en acciones clinicas sensibles

- Sintoma:
	- riesgo de permitir edicion fuera de especialidad/rol.
- Causa raiz:
	- complejidad creciente del modelo de permisos.
- Impacto:
	- posibles 403 frecuentes o acciones no autorizadas.
- Solucion aplicada:
	- endurecimiento RBAC por endpoint y ajustes de UX de opciones segun rol.
- Evidencia de cierre:
	- suite RBAC clinico con pruebas superadas.

#### Problema 9. Falta de evidencia unificada para defensa

- Sintoma:
	- informacion distribuida en varios archivos sin hilo conductor.
- Causa raiz:
	- evolucion documental por etapas no unificada.
- Impacto:
	- mayor esfuerzo de exposicion y riesgo de omitir detalles.
- Solucion aplicada:
	- separacion de memoria en 3 documentos + guion completo de defensa.
- Evidencia de cierre:
	- documentos estructurados por guia docente y enlazados desde indice maestro.

---

## 3. Resultados

### 3.1 Resultados funcionales por modulo

Paciente:

- autenticacion funcional,
- perfil de salud e IMC,
- CTA de cita nutricional,
- seguimiento diario,
- historial de derivaciones.

Profesional:

- panel clinico organizado,
- derivaciones emitidas/recibidas,
- medicacion y plan nutricional,
- protocolos, checklist y auditoria,
- severidad sugerida,
- PDF hospitalario.

IA/NLU:

- procesamiento conversacional integrado,
- deteccion de intenciones y entidades en espanol,
- capacidad de evolucion por entrenamiento.

### 3.2 Resultados de experiencia de usuario

Mejoras de UX observables:

- estructura visual por secciones,
- jerarquia de contenido paciente/profesional,
- lectura IMC mas clara y accionable,
- reduccion de friccion entre insight y accion.

### 3.3 Resultados de seguridad

- rol paciente forzado en registro publico,
- alta profesional bajo clave privada,
- permisos de edicion restringidos en rutas criticas,
- controles de acceso aplicados en backend.

### 3.4 Resultados de trazabilidad clinica

- historial versionado de checklist,
- auditoria temporal consultable,
- informe PDF de caso,
- salida explicable de severidad sugerida.

### 3.5 Incidencias y solucion durante el desarrollo

Incidencias tecnicas relevantes:

- conflictos de dependencias en entornos Python,
- limitaciones de cuota en servicios IA externos,
- necesidad de endurecer permisos por rol,
- necesidad de reforzar trazabilidad clinica.

Soluciones aplicadas:

- estabilizacion de entornos virtuales,
- estrategia de fallback para continuidad,
- RBAC estricto en backend,
- versionado historico en checklist.

### 3.6 Resultado de madurez por dimension

Dimension funcional:

- integrada y operativa en los flujos troncales.

Dimension seguridad:

- fuerte en backend para acciones sensibles.

Dimension trazabilidad:

- alta, con auditoria temporal y export documental.

Dimension validacion:

- base robusta en rutas criticas con pruebas automatizadas.

---

## 4. Analisis

### 4.1 Interpretacion global

El proyecto alcanza un nivel de integracion notable entre captura de datos, logica de negocio y accion asistencial. Se demuestra una evolucion desde funcionalidades basicas hacia un sistema con criterios de seguridad, coordinacion y trazabilidad.

### 4.2 Comparacion con objetivos iniciales

- Objetivos de arquitectura: alcanzados.
- Objetivos de seguridad por rol: alcanzados.
- Objetivos de continuidad paciente-profesional: alcanzados.
- Objetivos de validacion tecnica: alcanzados en rutas criticas.
- Objetivos de trazabilidad clinica: alcanzados.

### 4.3 Eficacia del software

Evaluacion cualitativa:

- utilidad funcional: alta,
- coherencia arquitectonica: alta,
- mantenibilidad: media-alta,
- robustez en flujos criticos: alta,
- madurez de evidencia para defensa: alta.

### 4.4 Limitaciones actuales

- cobertura de pruebas ampliable en mas modulos,
- faltan pipelines CI/CD formalizados,
- monitorizacion operativa mejorable,
- evolucion futura necesaria para despliegue multientorno mas amplio.

### 4.5 Areas de mejora concretas

- ampliar testing de autenticacion y PDF,
- añadir validaciones de regresion en frontend,
- versionar API por prefijo,
- incorporar telemetria y observabilidad,
- fortalecer catalogo de recursos clinicos con metadatos de evidencia.

### 4.6 Lecciones tecnicas consolidadas

1. Escalar funcionalidad sin romper seguridad exige RBAC desde el inicio.
2. En dominio clinico, "estado actual" no es suficiente sin "historial".
3. La UX debe acompañar al circuito de negocio, no solo al diseño visual.
4. Un buen cierre academico necesita evidencia tecnica trazable, no solo relato.

## 5. Arquitectura hiper-detallada

### 5.1 Topologia de ejecucion

Topologia actual de desarrollo:

1. Frontend Flutter (web/macOS) ejecuta interfaz y consumo de API.
2. Backend FastAPI centraliza negocio en puerto 8001.
3. RASA expone inferencia NLU en puerto 5005.
4. MySQL persiste estado de dominio y trazabilidad.

Cadena de valor tecnico:

UI -> BackendService -> endpoint FastAPI -> validacion/rol -> modelo ORM -> DB

Cuando hay NLU:

UI -> backend /chat o /chat/rasa -> servicio RASA -> respuesta estructurada -> persistencia -> respuesta final al cliente

### 5.2 Responsabilidades internas por capa

Frontend:

- representar estado visual,
- ejecutar validaciones basicas de formulario,
- consumir API y presentar feedback.

Backend:

- resolver identidad del usuario,
- aplicar permisos por rol,
- ejecutar reglas de negocio clinicas,
- serializar respuesta coherente,
- manejar errores con codigos HTTP adecuados.

RASA:

- interpretar lenguaje natural,
- detectar intencion y entidades,
- devolver señal util para el flujo de negocio.

Persistencia:

- conservar estado transaccional,
- mantener historico cuando hay cambio clinico relevante,
- soportar consultas por paciente, rol, fecha y severidad.

### 5.3 Patrón de seguridad transversal

Patron aplicado:

1. autenticacion en login/register,
2. token bearer en rutas protegidas,
3. resolucion de usuario actual,
4. validacion de rol en endpoint,
5. ejecucion de negocio solo si cumple permisos.

Ventaja:

- protege tanto API como integridad de datos,
- evita que la seguridad dependa de controles visuales del cliente.

### 5.4 Gestion de errores y resiliencia

Estrategias observadas:

- codigos 400 para payload invalido,
- codigos 401/403 para acceso no permitido,
- codigos 404 para entidades inexistentes,
- fallback controlado en integracion IA para continuidad de flujo.

Impacto en robustez:

- menor ambiguedad para frontend,
- depuracion mas rapida,
- defensa mas clara ante tribunal.

## 6. Diseno de base de datos hiper-detallado

### 6.1 Entidades de identidad y sesion funcional

Rol:

- define permisos de negocio,
- habilita segmentacion de acciones por perfil.

Usuario:

- identidad principal,
- relaciona perfil, seguimiento, derivaciones y acciones clinicas.

PerfilSalud:

- almacena antropometria y habitos base,
- soporta calculo y lectura de IMC.

### 6.2 Entidades de seguimiento y contexto paciente

RegistroDiario:

- mantiene check-ins de estado,
- permite resumen semanal e historico.

HabitoAgenda:

- agenda persistida por dia,
- seguimiento de completado por habito.

MensajeChat:

- persistencia de conversacion,
- trazabilidad de interacciones IA.

EvaluacionIA:

- captura respuestas y planes por seccion,
- mantiene fecha de creacion/actualizacion.

### 6.3 Entidades de coordinacion profesional

Derivacion:

- conecta paciente, origen profesional y destino,
- soporta estados y lectura de paciente.

MedicacionAsignada:

- define prescripcion, dosis y estado activa,
- restringida por permisos especificos.

PlanNutricionalClinico:

- define objetivo calorico y macros,
- incluye objetivo clinico y riesgo metabolico.

### 6.4 Entidades hospitalarias de trazabilidad

ProtocoloHospitalario:

- plantilla por trastorno/severidad/especialidad,
- guia acciones y ruta de escalado.

ChecklistClinicoPaciente:

- estado clinico aplicado al paciente,
- registro de escalado y observaciones.

ChecklistClinicoHistorial:

- snapshot versionado de cada cambio,
- fundamento de auditoria temporal.

RecursoClinico:

- repositorio estructurado de apoyo,
- filtro por trastorno/especialidad.

### 6.5 Decisiones de diseno relacional

Decisiones clave:

- separar tabla actual de tabla historica en checklist,
- modelar derivaciones con origen y destino explicitos,
- modelar profesional prescriptor y paciente receptor en medicacion,
- mantener fechas de actualizacion en entidades clinicas.

Efecto:

- consultas mas claras,
- mejor auditabilidad,
- menor perdida de contexto temporal.

## 7. Flujos por endpoint (detalle funcional)

### 7.1 Autenticacion y sesion

POST /login:

- valida credenciales,
- devuelve token y rol,
- habilita sesion para frontend.

POST /register:

- crea paciente en canal publico,
- evita alta publica de roles profesionales.

POST /register-profesional:

- exige clave privada,
- restringe roles permitidos,
- crea cuenta profesional validada.

GET /me:

- valida token activo,
- devuelve identidad y rol actual.

### 7.2 Perfil y metricas

POST /perfil/completar:

- recibe datos antropometricos,
- calcula IMC,
- crea/actualiza perfil.

PATCH /perfil/metricas-imc:

- actualiza metricas especificas,
- mantiene coherencia del estado IMC.

GET /perfil/resumen:

- devuelve vista consolidada del perfil paciente.

### 7.3 Conversacion y evaluaciones

POST /chat:

- procesa mensaje,
- integra contexto IA,
- retorna respuesta y posibles metadatos utiles.

POST /chat/rasa:

- delega a RASA,
- devuelve salida unificada para frontend.

GET/DELETE /chat/historial:

- consulta o limpia historial conversacional.

GET/PUT/DELETE /evaluaciones/ia/{seccion}:

- permite persistir y mantener evaluaciones por dominio funcional.

### 7.4 Seguimiento y habitos

POST /seguimiento/checkin:

- guarda check-in diario,
- normaliza estado emocional y notas derivadas.

GET /seguimiento/resumen-semanal:

- calcula promedio de animo/energia/estres/sueno.

GET /seguimiento/historico:

- devuelve puntos para graficas de evolucion.

GET /seguimiento/racha:

- calcula adherencia actual y mejor racha.

GET/PATCH /habitos/agenda:

- recupera agenda del dia,
- permite marcar habitos completados.

### 7.5 Coordinacion profesional

GET /profesionales/pacientes:

- devuelve lista de pacientes con contexto basico.

GET /profesionales/pacientes/{id}/kpis:

- agrega indicadores clinicos relevantes.

GET/POST /profesionales/pacientes/{id}/medicacion:

- consulta y asigna medicacion segun permisos.

PATCH /profesionales/medicacion/{id}/estado:

- activa/desactiva prescripcion vigente.

GET/PUT /profesionales/pacientes/{id}/plan-nutricional:

- consulta/actualiza plan nutricional clinico.

### 7.6 Capa hospitalaria

GET/PUT /profesionales/protocolos-hospitalarios:

- consulta/actualiza protocolos por contexto clinico.

GET/PUT /profesionales/pacientes/{id}/checklist-clinico:

- consulta/actualiza checklist aplicado al paciente.

GET /profesionales/pacientes/{id}/checklist-clinico/auditoria:

- devuelve historial versionado del checklist.

GET /profesionales/pacientes/{id}/severidad-sugerida:

- calcula severidad automatica con motivos.

GET /profesionales/pacientes/{id}/informe-hospitalario-pdf:

- genera informe consolidado descargable.

### 7.7 Derivaciones y recursos

POST /profesionales/derivaciones:

- emite derivacion entre especialidades permitidas.

GET /profesionales/derivaciones/recibidas:

- lista bandeja de casos para profesional destino.

PATCH /profesionales/derivaciones/{id}/estado:

- actualiza estado de seguimiento del caso.

POST /pacientes/solicitar-cita-nutricion:

- inicia flujo de derivacion desde paciente,
- evita duplicados con reuso de caso abierto.

GET/PATCH /pacientes/derivaciones:

- consulta y marca lectura de derivaciones del paciente.

GET/POST /profesionales/recursos-clinicos:

- consulta y crea recursos de apoyo por contexto.

GET /profesionales/asignado:

- retorna profesional de referencia por especialidad.

### 7.8 Observaciones finales de trazabilidad por endpoint

Cada familia de endpoints deja evidencia en uno o varios planos:

- plano funcional (accion visible en UI),
- plano de datos (persistencia),
- plano de seguridad (rol requerido),
- plano de defensa (captura/test/documento).

Este esquema permite justificar ante tribunal que la funcionalidad no solo existe, sino que se comporta de forma controlada y verificable.

---

## Cierre del Documento 2

Este Documento 2 recoge el desarrollo completo del proyecto con enfoque tecnico exhaustivo. El Documento 3 cierra la memoria con conclusiones, lineas futuras, bibliografia, anexos y apartados opcionales.

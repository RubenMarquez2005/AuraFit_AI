# Documentacion Integral TFG - AuraFit AI

## 1. Resumen ejecutivo
AuraFit AI es una plataforma clinica de apoyo al bienestar integral orientada a pacientes y profesionales sanitarios.
El sistema integra frontend Flutter, backend FastAPI, motor conversacional RASA y persistencia SQL para cubrir flujos de nutricion, salud mental, entrenamiento, coordinacion interdisciplinar y trazabilidad hospitalaria.

La version actual del proyecto, consolidada a fecha 06-04-2026, ya incorpora:
- Alta publica de pacientes y alta privada de especialistas con clave interna.
- Control de acceso por rol (paciente, nutricionista, psicologo, coach, medico, administrador).
- Trazabilidad de checklist clinico en modo auditoria temporal versionada.
- Sugerencia automatica de severidad basada en KPIs clinicos.
- Export de informe hospitalario PDF con protocolo activo, checklist aplicado y ruta de escalado.
- Flujo de paciente para solicitar cita de nutricion desde el estado IMC.
- Pruebas unitarias y de integracion para validar rutas criticas.

Objetivo academico del TFG:
- Demostrar una implementacion realista de arquitectura full stack sanitaria.
- Justificar decisiones de seguridad, usabilidad clinica y mantenibilidad.
- Aportar evidencia tecnica reproducible para defensa y evaluacion.

## 2. Alcance funcional entregado
### 2.1 Ambito de usuario paciente
- Registro e inicio de sesion.
- Captura de peso y altura para calculo de IMC.
- Tarjeta de IMC con lectura clinica explicita:
  - Bajo peso
  - Peso normal
  - Sobrepeso
  - Obesidad
- Visualizacion IMC tipo rosca con indicador direccional.
- Solicitud directa de cita con nutricion desde la tarjeta IMC.
- Historial de derivaciones visibles para el paciente.
- Interaccion conversacional con IA mediante backend y RASA.

### 2.2 Ambito de usuario profesional
- Panel clinico por especialidad.
- Consulta y edicion controlada de plan nutricional segun rol.
- Creacion y seguimiento de derivaciones.
- Gestion de protocolos hospitalarios.
- Gestion de checklist clinico por paciente.
- Consulta de auditoria temporal de checklist.
- Consulta de severidad sugerida por KPIs.
- Descarga de informe hospitalario PDF.

### 2.3 Ambito de administracion y seguridad
- Registro de especialistas solo con clave privada de alta.
- Restriccion del registro publico al rol paciente.
- Validacion de sesion basada en token y endpoint de perfil.
- Reglas de permiso backend como frontera real de seguridad.

## 3. Arquitectura tecnica
### 3.1 Capas
- Presentacion: Flutter (web y macOS).
- Servicios API: FastAPI.
- Motor conversacional: RASA (NLU y respuestas)
- Persistencia: MySQL mediante SQLAlchemy.
- Export documental: FPDF para PDF clinico.

### 3.2 Principios aplicados
- Separacion de responsabilidades.
- Validacion explicita de entrada con Pydantic.
- Politica de permisos en servidor, no en cliente.
- Trazabilidad clinica para decisiones hospitalarias.
- Evolucion incremental con evidencia de pruebas.

### 3.3 Flujo de datos simplificado
1. Usuario opera en Flutter.
2. Flutter consume endpoints FastAPI via servicio HTTP.
3. FastAPI valida token y rol.
4. FastAPI persiste o consulta entidades SQL.
5. Cuando aplica chat, FastAPI delega en RASA.
6. Resultados vuelven al frontend con estado tipado.

## 4. Diseno de seguridad y cumplimiento funcional
### 4.1 Registro de cuentas
- Registro publico:
  - Endpoint de registro accesible para alta de paciente.
  - Rol forzado a paciente para evitar escalado de privilegios.
- Registro profesional:
  - Endpoint dedicado de alta privada.
  - Requiere clave interna de registro.
  - Limita roles permitidos a perfiles profesionales.

### 4.2 Control de acceso por rol
Matriz de referencia:
- Paciente:
  - Puede actualizar IMC propio, ver derivaciones propias, solicitar cita nutricional.
  - No puede editar protocolos, checklist hospitalario ni medicacion.
- Coach/Psicologo/Nutricionista/Medico/Administrador:
  - Pueden acceder al panel profesional segun su alcance.
- Medico y administrador:
  - Permisos ampliados en medicacion y coordinacion critica.

### 4.3 Trazabilidad clinica
- Cada actualizacion de checklist clinico genera evento historico versionado.
- La auditoria conserva:
  - Version
  - Fecha
  - Profesional
  - Contenido de checklist
  - Escalado aplicado
  - Observaciones

Este enfoque permite justificar decisiones clinicas en auditorias internas y en revision academica del caso.

## 5. Modulos clinicos implementados
### 5.1 Derivaciones
- Derivacion entre profesionales por especialidad.
- Derivacion iniciada por paciente para nutricion.
- Estado de derivacion y lectura de notificaciones.

### 5.2 Plan nutricional clinico
- Definicion de calorias objetivo y macronutrientes.
- Objetivo clinico y riesgo metabolico.
- Permisos de edicion restringidos a roles autorizados.

### 5.3 Protocolos hospitalarios
- Protocolo por trastorno, severidad y especialidad.
- Checklist base y ruta de escalado.
- Version activa consultable desde panel profesional.

### 5.4 Checklist clinico y auditoria temporal
- Checklist aplicado a paciente.
- Historial de cambios en tabla dedicada.
- Recuperacion por filtros (paciente, trastorno, severidad).

### 5.5 Severidad automatica sugerida
- Calculo desde KPIs clinicos agregados.
- Scoring heuristico explicable.
- Salida con:
  - severidad sugerida
  - puntuacion de riesgo
  - motivos trazables

### 5.6 Export hospitalario PDF
- Documento descargable con:
  - datos basicos del paciente
  - protocolo activo
  - checklist aplicado
  - ruta de escalado
  - observaciones

## 6. Experiencia de usuario y mejora visual IMC
### 6.1 Problema previo
La visualizacion de IMC en formato lineal era funcional, pero de baja expresividad clinica para paciente final.

### 6.2 Solucion aplicada
- Tarjeta IMC redisenada con indicador circular y flecha de posicion.
- Etiqueta clinica textual de interpretacion directa.
- Mensaje de accion recomendado segun rango.
- CTA inmediata para solicitar cita nutricional.

### 6.3 Impacto esperado
- Mayor comprension del estado corporal.
- Menor friccion entre insight y accion.
- Mejor continuidad asistencial entre paciente y nutricion.

## 7. Endpoints clave para defensa
### 7.1 Autenticacion y sesion
- POST /login
- POST /register
- POST /register-profesional
- GET /me
- GET /roles

### 7.2 Paciente
- PATCH /perfil/metricas-imc
- GET /perfil/resumen
- GET /pacientes/derivaciones
- POST /pacientes/solicitar-cita-nutricion

### 7.3 Profesional
- GET /profesionales/pacientes
- GET /profesionales/pacientes/{id}/kpis
- GET/PUT /profesionales/pacientes/{id}/plan-nutricional
- GET/PUT /profesionales/protocolos-hospitalarios
- GET/PUT /profesionales/pacientes/{id}/checklist-clinico
- GET /profesionales/pacientes/{id}/checklist-clinico/auditoria
- GET /profesionales/pacientes/{id}/severidad-sugerida
- GET /profesionales/pacientes/{id}/informe-hospitalario-pdf

## 8. Estrategia de pruebas y evidencia
### 8.1 Enfoque
- Pruebas unitarias y de integracion de backend con TestClient.
- Base SQLite en memoria para ejecucion aislada.
- Overrides de dependencias de autenticacion y DB.

### 8.2 Pruebas existentes
- Suite RBAC clinico previa para permisos de plan/protocolos.

### 8.3 Pruebas nuevas incorporadas
Archivo: backend/tests/test_cita_nutricion.py
Casos:
1. Crea derivacion al solicitar cita nutricional.
2. Reutiliza derivacion abierta (evita duplicados).
3. Flujo integrado IMC -> solicitud -> bandeja de derivaciones.

Resultado validado en ejecucion local:
- 3 tests ejecutados
- 3 tests OK

## 9. Riesgos identificados y mitigaciones
### 9.1 Riesgo de registro no autorizado de especialistas
Mitigacion:
- Endpoint privado con clave de registro.
- Roles permitidos controlados en backend.

### 9.2 Riesgo de cambios clinicos sin trazabilidad
Mitigacion:
- Auditoria temporal versionada por checklist.

### 9.3 Riesgo de decisiones sin explicabilidad
Mitigacion:
- Severidad sugerida con motivos y puntuacion.

### 9.4 Riesgo de informacion fragmentada para comite clinico
Mitigacion:
- Export PDF hospitalario consolidado.

## 10. Procedimiento de demostracion para defensa
### 10.1 Guion de demo recomendado
1. Iniciar backend y verificar docs.
2. Iniciar frontend web.
3. Alta paciente y acceso a home.
4. Introducir peso/altura y visualizar IMC.
5. Solicitar cita de nutricion desde CTA.
6. Entrar como profesional y revisar derivacion.
7. Consultar checklist y auditoria temporal.
8. Ver severidad sugerida por KPIs.
9. Descargar informe hospitalario PDF.
10. Mostrar ejecucion de tests automatizados.

### 10.2 Evidencias a capturar
- Captura de endpoint en Swagger.
- Captura del flujo UI IMC -> cita.
- Captura de tabla/consulta de auditoria.
- Captura del PDF exportado.
- Resultado de test runner en terminal.

## 11. Mantenibilidad y evolucion
### 11.1 Practicas adoptadas
- Modulos separados por dominio.
- Tipado de payloads y respuestas.
- Control de errores consistente.
- Documentacion tecnica progresiva.

### 11.2 Evolucion recomendada tras defensa
- Cobertura automatica adicional (auth y export PDF).
- Instrumentacion de auditoria de acciones de usuario.
- Versionado de APIs por prefijo.
- Pipeline CI para test y lint automaticos.

## 12. Conclusiones tecnicas
AuraFit AI supera el estado de prototipo basico y entra en fase de producto academico avanzado para contexto clinico formativo.
La combinacion de RBAC, trazabilidad, scoring explicable y experiencia accionable para paciente constituye una base solida para la defensa del TFG.

El proyecto esta preparado para ser presentado con evidencia funcional y tecnica, y con una narrativa coherente entre necesidad real, implementacion y validacion.

## 13. Checklist final de documentacion TFG
- Memoria principal actualizada.
- Bitacora cronologica actualizada.
- Validacion RASA documentada.
- Dossier integral tecnico actualizado.
- Evidencia de tests nuevos anexada.
- Estado de arquitectura y seguridad descrito.
- Plan de demo y defensa definido.

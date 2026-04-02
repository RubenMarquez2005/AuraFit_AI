# Memoria TFG - AuraFit AI

## Portada
- Nombre del alumno/alumnos:
- Curso academico:
- Nombre del tutor de FCT:
- Nombre del grado:

## Indice
- 1. Introduccion
- 2. Justificacion del proyecto
- 3. Objetivos
- 4. Requisitos solicitados por la profesora y estado
- 5. Desarrollo tecnico realizado
- 6. Resultados y analisis
- 7. Incidencias y resoluciones
- 8. Conclusiones
- 9. Lineas de trabajo futuras
- 10. Bibliografia / Webgrafia
- 11. Anexos

## Estado actual del proyecto (02-04-2026)
- Estado general: frontend y backend operativos para presentacion en Web + macOS.
- Alcance aplicado en el codigo: se mantienen plataformas objetivo y se eliminan plataformas aplazadas.
- Tarea 1: completada.
- Tarea 2 (login): completada y validada contra BBDD real.
- Tarea 3 (servicio IA): completada con fallback local gratuito cuando Gemini no tiene cuota.
- Tarea 4 (perfil antropometrico): completada con endpoint protegido por token e IMC automatico.
- Integracion RASA: completada con puente FastAPI -> webhook REST de RASA en puerto 5005.
- Proyecto `ai_rasa`: inicializado y entrenado con modelo base funcional para pruebas.
- Repositorio GitHub: activo y con trazabilidad de cambios.
- Documentacion de seguimiento: bitacora y memoria actualizadas con detalle tecnico.

## Introduccion
AuraFit AI es una plataforma de salud digital con enfoque de acompanamiento personalizado.
El sistema se esta construyendo con frontend Flutter, backend FastAPI y base de datos MySQL.
La propuesta de valor es centralizar el seguimiento de habitos y habilitar recomendaciones
segun rol profesional y datos del usuario.

## Justificacion del proyecto
- Problema que se quiere resolver:
Las personas que intentan mejorar habitos de salud suelen usar herramientas separadas,
sin continuidad entre nutricion, estado emocional y seguimiento diario.
- Colectivo al que va dirigido:
Usuarios finales y perfiles profesionales (nutricionista, psicologo, coach),
con sistema de roles para adaptar funcionalidades.
- Utilidad real de la herramienta:
Permitir registro estructurado, trazabilidad de progreso y base tecnica para recomendaciones.
- Diferenciacion inicial:
Arquitectura modular desde el inicio y backend preparado para escalar por servicios.

## Objetivos
### Objetivo general
- Desarrollar una plataforma que ayude a mejorar habitos de salud con apoyo de IA.

### Objetivos especificos
- Gestionar usuarios y roles. Estado: en marcha, base implementada.
- Registrar perfiles de salud y habitos. Estado: base de datos y modelos creados.
- Registrar seguimiento diario de nutricion y estado emocional. Estado: modelo inicial creado.
- Generar recomendaciones personalizadas. Estado: pendiente de siguientes iteraciones.
- Exponer API robusta para integracion con frontend Flutter. Estado: en marcha con endpoints base.

## Requisitos solicitados por la profesora y estado

| Solicitud de la profesora | Estado | Evidencia de trabajo realizado | Comentario |
| --- | --- | --- | --- |
| Estructura clara del proyecto en frontend, backend y database | Completado | Monorepo reorganizado con tres carpetas principales | Base de trabajo establecida |
| Definir main.py para recibir conexiones y exponer health checks | Completado | Backend FastAPI con endpoints raiz, health y health/db | Punto de entrada funcional |
| Preparar requirements.txt inicial del backend | Completado | Dependencias de API, ORM, MySQL y auth definidas | Incluye passlib y bcrypt |
| Conexion a MySQL con variables en .env | Completado | Settings y db configurados con lectura de variables | Credenciales validadas |
| Modelado SQLAlchemy para tablas principales | Completado | Modelos de roles, usuarios, perfiles_salud y registros_diarios | Base ORM lista |
| Verificacion de conexion en startup | Completado | Evento de arranque crea tablas y comprueba DB | Bloquea arranque si falla DB |
| Validacion de datos con Pydantic | Completado | Esquemas de autenticacion y dominio implementados | Validacion estricta |
| Implementar login con endpoint POST /login | Completado | Ruta de login activa y conectada a servicio auth | Flujo de autenticacion construido |
| Verificar password con passlib contra hash almacenado | Completado | Servicio de autenticacion con verificacion bcrypt | Probado con usuario real |
| Devolver rol del usuario en respuesta de login | Completado | Respuesta incluye usuario_id, nombre, email y rol | Requisito funcional cubierto |
| Proteger endpoints de perfil con token de usuario | Completado | Login devuelve access_token y endpoint valida Bearer token | Seguridad aplicada en perfil |
| Crear servicio Gemini con GEMINI_API_KEY desde .env | Completado | Servicio IA configurado y endpoint de prueba operativo | Integracion lista para uso real |
| Detectar mensajes de riesgo en chat IA | Completado | Etiqueta ALERTA_RIESGO_TCA_ANSIEDAD implementada | Trazabilidad para BBDD |
| Preparar soporte futuro para imagenes de comida | Completado | Estructura multimodal lista en servicio IA | Preparado para siguientes iteraciones |
| Endpoint POST /perfil/completar con calculo de IMC | Completado | IMC calculado en backend y devuelto en respuesta | Formula aplicada en servidor |
| Guardar perfil en perfiles_salud y actualizar si existe | Completado | Logica upsert por usuario_id validada en BBDD | No genera duplicados |
| Definir alcance de presentacion por dispositivos | Completado | Objetivo de entrega focalizado en Web y macOS | Alcance acotado para defensa del TFG |
| Adaptar frontend para consumo HTTP y gestion de estado | Completado | Dependencias `http`, `provider` y `google_fonts` integradas | Base preparada para consumo de API y UI de presentacion |
| Implementar puente backend hacia RASA en puerto 5005 | Completado | Endpoint `POST /chat/rasa` y servicio `rasa_service.py` operativos | Integracion conversacional local funcional |
| Crear e inicializar proyecto local `ai_rasa` | Completado | Estructura de RASA creada y modelo inicial entrenado | Entorno de pruebas IA local disponible |
| Validar flujo extremo a extremo FastAPI -> RASA | Completado | Respuesta 200 en `/chat/rasa` con mensajes REST de RASA | Evidencia funcional de integracion |
| Eliminar plataformas no incluidas en alcance de defensa | Completado | Carpetas frontend de Android, iOS, Linux y Windows retiradas | Coherencia tecnica con alcance Web + macOS |
| Estilo de codigo en espanol y sin iconos de IA | Completado | Comentarios y docstrings revisados en backend principal | Criterio de estilo aplicado |
| Subir trabajo a GitHub y guardar evidencia para memoria TFG | Completado | Repo remoto activo y bitacora de avances mantenida | Trazabilidad disponible |

## Desarrollo
Resumen del enfoque tecnico seguido en esta fase.

### Arquitectura aplicada
- Monorepo dividido en capas por responsabilidad:
	frontend (Flutter), backend (FastAPI) y database (scripts SQL).
- Separacion interna en backend por modulos:
	api, services, models, schemas, config y capa de acceso a DB.

### Fundamentacion teorica
- Arquitectura de software: API orientada a servicios, con capa de persistencia separada.
- Tecnologias usadas: Flutter, FastAPI, SQLAlchemy, MySQL, Pydantic, Uvicorn.
- Buenas practicas aplicadas: separacion de responsabilidades, validacion de entrada,
	uso de variables de entorno, control de dependencias y trazabilidad en Git.

### Materiales y metodos
- Casos de uso implementados hasta ahora:
	login por email y contrasena, recuperacion de rol para decision de interfaz,
	prueba de chat IA, registro/actualizacion de perfil antropometrico,
	consulta de asistente RASA desde backend y visualizacion en entorno de presentacion.
- Diseno de base de datos aplicado:
	tablas principales para usuarios, roles, perfiles de salud y registros diarios.
- Prototipo tecnico actual:
	backend operativo con arranque, verificacion de DB, login, chat IA,
	perfil protegido y puente hacia servicio RASA local.
- Componentes principales desarrollados:
	ruta de autenticacion con token Bearer, servicio IA Gemini con fallback,
	endpoint de perfil con calculo de IMC, endpoint `/chat/rasa`,
	cliente HTTP a RASA, modelos ORM y esquemas Pydantic.
- Metodo de validacion:
	pruebas de conexion, validacion de hash bcrypt, pruebas de token,
	pruebas endpoint IA, pruebas de upsert en perfiles_salud,
	prueba E2E FastAPI -> RASA con respuesta real del webhook REST.

### Resultados y analisis
#### Resultados
- Funcionalidades desarrolladas:
	estructura base del proyecto, conexion DB, startup check, login con token,
	servicio IA con deteccion de riesgo, endpoint de perfil antropometrico,
	integracion de backend con RASA y depuracion de plataformas de frontend segun alcance.
- Evidencias de funcionamiento:
	endpoint de salud respondiendo healthy, autenticacion con token,
	perfil actualizado sin duplicados, chat operativo con fallback cuando no hay cuota,
	respuesta real de RASA recibida por `/chat/rasa` con estado 200.
- Incidencias principales resueltas:
	compatibilidad de hashing, ajustes de arranque por ruta,
	modelo Gemini no disponible, limite de cuota free tier,
	conflicto de instalacion RASA por versiones en entorno Python 3.9.

#### Analisis
- Comparacion con objetivos iniciales:
	la base del backend, autenticacion y registro de perfil estan cumplidos.
- Eficacia de la solucion actual:
	el backend valida credenciales, protege endpoints por token,
	calcula IMC, persiste perfil de forma consistente y delega conversacion a RASA cuando se requiere.
- Areas de mejora:
	ampliar CRUD funcional, reforzar pruebas automaticas,
	activar cuota Gemini para respuesta IA real sin fallback,
	automatizar entrenamiento y despliegue de RASA para integracion continua.

## Incidencias y resoluciones
- Incidencia: error de acceso MySQL por credenciales/privilegios.
	Resolucion: ajuste de acceso y validacion de conexion real desde backend.
- Incidencia: diferencia entre entorno de shell y entorno virtual para pip.
	Resolucion: uso del interprete de .venv para ejecucion y gestion de dependencias.
- Incidencia: arranque desde raiz sin contexto de backend.
	Resolucion: ejecutar desde backend o indicar app-dir y env-file al arrancar uvicorn.
- Incidencia: cuota de Gemini agotada en free tier (error 429).
	Resolucion: fallback local gratuito para no bloquear desarrollo y pruebas.
- Incidencia: conflictos de puerto durante pruebas de runtime.
	Resolucion: estandarizar uso de API_PORT=8001 y liberar procesos previos.
- Incidencia: instalacion de RASA con conflicto de dependencias en Python 3.9 (JAX).
	Resolucion: fijar versiones compatibles de `jax` y `jaxlib` para completar la instalacion e inicializacion del asistente local.

## Conclusiones
- Aprendizajes tecnicos:
	importancia de separar capas, validar entorno desde el inicio,
	resolver dependencias complejas y asegurar trazabilidad de cambios.
- Aprendizajes de proceso:
	documentar cada fase facilita justificar decisiones de alcance ante tutor y memoria.
- Grado de cumplimiento hasta la fecha:
	cumplidos requisitos de estructura, autenticacion, IA base,
	perfil antropometrico e integracion inicial con RASA.

## Lineas de investigacion futuras
- Ampliar endpoints CRUD de dominio (usuarios, perfiles y registros diarios).
- Integrar frontend Flutter con login y flujo por rol.
- Incorporar pruebas unitarias e integracion automatizadas.
- Activar cuota Gemini para usar origen real de IA en produccion.
- Evaluar migracion o convivencia con RASA para gestion conversacional on-premise.
- Reintroducir iOS, Android, Linux y Windows una vez superada la defensa y estabilizado el nucleo funcional.
- Definir modulo de recomendaciones personalizadas como siguiente hito.

## Alcance de presentacion
- Dispositivos objetivo para la entrega: navegador web y aplicacion macOS.
- Motivo: concentrar esfuerzo en dos entornos estables para una defensa solida.
- Estrategia: mantener arquitectura preparada para ampliar plataformas en fases posteriores.

## Nota sobre IA y RASA
- Estado actual: backend con servicio Gemini y fallback local gratuito para continuidad.
- Decision de evaluacion: analizar RASA como alternativa o complemento para conversacion guiada.
- Criterio tecnico para decidir: coste, control de datos, facilidad de entrenamiento y mantenimiento.

## Actualizacion extensa de implementacion (02-04-2026)

### 1) Consolidacion del alcance de presentacion
- Se formaliza en codigo la decision de defender el proyecto en Web y macOS.
- Se eliminan carpetas de plataforma aplazada (Android, iOS, Linux y Windows) para evitar dispersion tecnica.
- Se conserva una estructura de frontend enfocada al escenario real de la defensa: estabilidad, claridad y mantenimiento.

### 2) Integracion conversacional local con RASA
- Se crea la carpeta `ai_rasa` como modulo de IA local desacoplado del backend principal.
- Se inicializa un proyecto RASA completo con archivos de dominio, NLU, historias, reglas y acciones.
- Se entrena modelo inicial para disponer de una base funcional de pruebas en entorno local.
- Se configura el backend para consumir el webhook REST de RASA (`/webhooks/rest/webhook`).

### 3) Cambios tecnicos en backend para puente FastAPI -> RASA
- Se anade la dependencia `requests` para comunicacion HTTP saliente.
- Se incorpora configuracion de entorno para URL y timeout de RASA.
- Se implementa servicio dedicado de integracion (`rasa_service.py`) para aislar la logica externa.
- Se expone endpoint `POST /chat/rasa` con contrato tipado (request/response) y manejo de errores 502.
- Se mantiene separacion por capas (rutas, servicios y configuracion), alineada a buenas practicas.

### 4) Ajustes tecnicos de frontend
- Se anaden dependencias `http`, `provider` y `google_fonts` para preparar consumo de API, estado y presentacion visual.
- Se valida la compilacion de dependencias con `flutter pub get`.
- Se mantiene la base de pruebas del frontend y se ajusta test principal al shell real de la app.

### 5) Evidencia de validacion funcional
- Backend iniciado en puerto 8001 con comprobacion de salud y conexion a base de datos.
- Servidor RASA levantado en puerto 5005 con API habilitada.
- Prueba real de integracion:
	- Entrada enviada al backend: mensaje `hola` con `sender` de prueba.
	- Resultado obtenido: respuesta de RASA recibida por backend y devuelta en formato unificado.
	- Estado HTTP: 200 en endpoint `POST /chat/rasa`.

### 6) Incidencias tecnicas de esta fase y resolucion
- Entorno Python principal roto (symlink invalido en `.venv`).
	Resolucion: recreacion completa del entorno y reinstalacion de dependencias.
- Instalacion de RASA con incompatibilidad de dependencias en Python 3.9.
	Resolucion: preinstalacion de versiones compatibles de `jax` y `jaxlib`, seguida de instalacion de RASA.
- Riesgo de incoherencia entre alcance documental y estructura real del frontend.
	Resolucion: limpieza de carpetas de plataformas no objetivo y actualizacion de memoria/bitacora.

### 7) Valor academico y profesional de la actualizacion
- Coherencia entre discurso de defensa y artefacto tecnico entregado.
- Mejora de trazabilidad: cada decision queda reflejada en codigo, documentacion y validacion.
- Reduccion de riesgo operativo durante la presentacion al trabajar sobre un alcance controlado.
- Preparacion para siguientes iteraciones sin bloquear el crecimiento futuro a otras plataformas.

## Bibliografia / Webgrafia
- Documentacion oficial de FastAPI.
- Documentacion oficial de SQLAlchemy.
- Documentacion oficial de Pydantic.
- Documentacion oficial de MySQL Connector/Python.
- Guia de buenas practicas para gestion de entornos Python.

## Opcionales
### Anexos
- Se pueden incluir capturas de pruebas de endpoints y estructura final del repositorio.

### Retos profesionales y personales
- Consolidar un flujo profesional de desarrollo con control de versiones y documentacion.

### Agradecimientos
- Personas y entidades que han ayudado en el proyecto.

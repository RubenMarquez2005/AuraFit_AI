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

## Estado actual del proyecto (18-03-2026)
- Estado general: base tecnica de backend operativa y conectada a MySQL.
- Tarea 1: completada.
- Tarea 2 (login): completada y validada contra BBDD real.
- Repositorio GitHub: activo y con trazabilidad de cambios.
- Documentacion de seguimiento: bitacora y memoria en actualizacion continua.

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
	login por email y contrasena, recuperacion de rol para decision de interfaz.
- Diseno de base de datos aplicado:
	tablas principales para usuarios, roles, perfiles de salud y registros diarios.
- Prototipo tecnico actual:
	backend operativo con arranque, verificacion de DB y endpoints de salud.
- Componentes principales desarrollados:
	ruta de autenticacion, servicio de autenticacion, modelos ORM, esquemas Pydantic.
- Metodo de validacion:
	pruebas de conexion, validacion de hash bcrypt y prueba de endpoint en runtime.

### Resultados y analisis
#### Resultados
- Funcionalidades desarrolladas:
	estructura base del proyecto, conexion DB, startup check, login y respuesta por rol.
- Evidencias de funcionamiento:
	endpoint de salud respondiendo healthy y autenticacion validada con BBDD real.
- Incidencias principales resueltas:
	compatibilidad de hashing y ajustes de ejecucion segun ruta de arranque.

#### Analisis
- Comparacion con objetivos iniciales:
	la base del backend y la autenticacion inicial estan ya cumplidas.
- Eficacia de la solucion actual:
	el backend valida credenciales y devuelve el rol esperado de forma consistente.
- Areas de mejora:
	ampliar CRUD funcional, reforzar pruebas automaticas y cerrar integracion frontend-backend.

## Incidencias y resoluciones
- Incidencia: error de acceso MySQL por credenciales/privilegios.
	Resolucion: ajuste de acceso y validacion de conexion real desde backend.
- Incidencia: diferencia entre entorno de shell y entorno virtual para pip.
	Resolucion: uso del interprete de .venv para ejecucion y gestion de dependencias.
- Incidencia: arranque desde raiz sin contexto de backend.
	Resolucion: ejecutar desde backend o indicar app-dir y env-file al arrancar uvicorn.

## Conclusiones
- Aprendizajes tecnicos:
	importancia de separar capas, validar entorno desde el inicio y asegurar trazabilidad.
- Aprendizajes de proceso:
	documentar cada fase facilita justificar decisiones ante tutor y memoria.
- Grado de cumplimiento hasta la fecha:
	cumplidos los requisitos iniciales de backend y autenticacion solicitados.

## Lineas de investigacion futuras
- Ampliar endpoints CRUD de dominio (usuarios, perfiles y registros diarios).
- Integrar frontend Flutter con login y flujo por rol.
- Incorporar pruebas unitarias e integracion automatizadas.
- Definir modulo de recomendaciones personalizadas como siguiente hito.

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

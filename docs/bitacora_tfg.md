# Bitacora de desarrollo - AuraFit AI

## 2026-03-18
### Avance realizado
- Reorganizacion de monorepo con carpetas frontend, backend y database.
- Inicializacion de frontend Flutter.
- Preparacion de backend FastAPI con SQLAlchemy y lectura de .env.
- Creacion de modelos ORM para: roles, usuarios, perfiles_salud y registros_diarios.
- Creacion de esquemas Pydantic para validacion de datos.
- Implementacion de evento startup para crear tablas y validar conexion DB.
- Revision de estilo del codigo: comentarios y docstrings en espanol.
- Eliminacion de iconos en logs del codigo principal.

### Estado de la tarea 1
- Estado tecnico del codigo: correcto.
- Punto pendiente de entorno: ajustar credenciales reales de MySQL en .env para que la conexion responda OK.

### Siguiente paso (tarea 2)
- Definir endpoints CRUD iniciales para roles, usuarios y perfiles de salud.

### Cierre de la tarea 1
- Se tradujeron comentarios y docstrings del backend principal a espanol.
- Se eliminaron iconos y texto visual en scripts Python.
- Se valido sintaxis con compilacion de archivos Python.
- Se comprobo la funcion de verificacion de DB: la logica funciona, pero el entorno devuelve acceso denegado por credenciales MySQL.

### Tarea 2 - Login
- Se implemento endpoint POST /login.
- El endpoint recibe email y password (tambien acepta clave contrasena para compatibilidad).
- Se agrego verificacion de contrasena con passlib (bcrypt).
- Se consulta la tabla usuarios y su relacion con roles para devolver el rol del usuario.
- La respuesta devuelve: usuario_id, nombre, email y rol.
- Se valido que la ruta /login queda registrada en FastAPI.
- Se agrego script `backend/scripts/crear_usuario.py` para dar de alta usuarios con hash bcrypt y rol.
- Se ajusto `DATABASE_URL` para codificar usuario/contrasena con caracteres especiales (ejemplo: @).

### Incidencia de entorno MySQL
- El usuario `root@%` autentica, pero no tiene privilegios sobre `aurafit_db` (solo USAGE).
- Se intento correccion automatica desde terminal, pero requiere accion con sudo local para recuperar privilegios.

### Resolucion de incidencia MySQL
- Se ejecuto recuperacion de privilegios y se restauro acceso a `aurafit_db` para `root@%`.
- Se creo/confirmo la base de datos `aurafit_db`.
- Se confirmo conexion de backend con `verify_database_connection()` devolviendo True.
- Se crearon tablas ORM y se sembraron roles base.

### Validacion funcional login con BBDD real
- Se creo usuario de prueba con script de alta y hash bcrypt.
- Se valido autenticacion contra BBDD devolviendo rol `cliente`.
- Se fijo compatibilidad de librerias de hashing (`passlib` + `bcrypt==4.0.1`).

### Estado Git y GitHub
- Repositorio Git inicializado en rama main.
- Commits creados para dejar trazabilidad del avance.
- Remoto origin configurado hacia GitHub.
- Primer push de la rama main completado.
- URL del repositorio: https://github.com/RubenMarquez2005/AuraFit_AI
- Identidad global de Git configurada (user.name y user.email) para evitar avisos en commits.

### Revision de memoria TFG y requisitos de profesora
- Se actualizo memoria_tfg.md para pasar de plantilla a documento real de estado.
- Se anadio una matriz de requisitos solicitados por la profesora con estado de cumplimiento.
- Se incorporaron resultados tecnicos ya validados: Tarea 1 y Tarea 2 (login).
- Se dejo documentado el requisito operativo para runtime real: .env valido y usuarios con hash bcrypt.

## 2026-03-19
### Tarea 3 - Servicio de IA
- Se agrego la dependencia `google-generativeai` en requirements del backend.
- Se creo el servicio `backend/services/gemini_service.py`.
- Se configuro lectura de `GEMINI_API_KEY` y `GEMINI_MODEL` desde entorno.
- Se implemento prompt de sistema con rol de nutricion y psicologia positiva.
- Se implemento deteccion de riesgo por palabras clave y etiqueta `ALERTA_RIESGO_TCA_ANSIEDAD`.
- Se dejo preparada estructura para soporte multimodal de imagenes.
- Se creo endpoint de prueba `POST /chat/test`.

### Incidencia en Tarea 3
- Gemini devolvio error 429 por cuota free tier agotada.
- Se implemento fallback local gratuito para mantener el flujo funcional durante desarrollo.

### Tarea 4 - Perfil antropometrico
- Se implemento `POST /perfil/completar` en backend.
- Se protege el endpoint con token Bearer de usuario.
- Se actualizo login para devolver `access_token` y `token_type`.
- Se implemento calculo de IMC en servidor: peso / (altura/100)^2.
- Se persiste en `perfiles_salud` de `aurafit_db`.
- Se implemento upsert (si el perfil existe, se actualiza; no se duplica).

### Evidencia funcional de Tarea 4
- Login con token bearer verificado en runtime.
- Endpoint protegido devuelve 401 sin token.
- Endpoint con token guarda perfil y devuelve IMC calculado.
- Segunda llamada sobre el mismo usuario actualiza y mantiene un solo registro en BBDD.

### Actualizacion de memoria para la profesora
- Se actualizo `docs/memoria_tfg.md` incluyendo Tarea 3 y Tarea 4.
- Se amplio la matriz de requisitos con estado y evidencia tecnica asociada.

## 2026-04-02
### Decision de alcance para presentacion
- Se define alcance de entrega en dos dispositivos: Web y macOS.
- Se aplaza extension a mas plataformas para fases posteriores.

### Decision de evaluacion IA
- Se mantiene implementacion actual de Gemini con fallback local gratuito.
- Se abre linea de evaluacion de RASA como alternativa/complemento para la parte conversacional.

### Actualizacion documental
- Se actualiza memoria_tfg.md con alcance de presentacion y nota tecnica de evaluacion RASA.

### Ejecucion tecnica de los faltantes
- Se anaden dependencias de frontend para fase de integracion: `http`, `provider` y `google_fonts`.
- Se ejecuta `flutter pub get` con resolucion correcta de paquetes.
- Se incorpora en backend la dependencia `requests` para conexion HTTP con servicios externos.
- Se implementa configuracion de RASA en settings (`RASA_WEBHOOK_URL`, `RASA_TIMEOUT_SECONDS`).
- Se crea servicio `backend/services/rasa_service.py` para envio de mensajes al webhook REST.
- Se publica endpoint `POST /chat/rasa` en FastAPI con contratos tipados y manejo de error de pasarela.

### Construccion del modulo local `ai_rasa`
- Se crea carpeta `ai_rasa` en la raiz del monorepo.
- Se crea entorno dedicado `venv_rasa`.
- Se instala RASA y se inicializa proyecto con `rasa init --no-prompt`.
- Se genera modelo inicial de conversacion en `ai_rasa/models`.

### Incidencias resueltas en la fase
- Entorno `.venv` principal roto por symlink invalido de Python.
	Resolucion: recreacion completa de entorno virtual e instalacion de requirements backend.
- Instalacion de RASA fallida inicialmente por incompatibilidad de JAX en Python 3.9.
	Resolucion: fijacion de versiones compatibles de `jax` y `jaxlib` antes de instalar RASA.

### Validacion funcional extremo a extremo
- Se levanta RASA en `127.0.0.1:5005`.
- Se levanta FastAPI en `127.0.0.1:8001`.
- Se ejecuta peticion real a `POST /chat/rasa`.
- Resultado: backend devuelve respuesta real de RASA con estado HTTP 200.

### Limpieza de estructura por alcance de defensa
- Se eliminan plataformas frontend aplazadas: `android`, `ios`, `linux`, `windows`.
- Se elimina tambien salida generada temporal (`build` y `.dart_tool`) para dejar base limpia.
- Se mantiene estructura de entrega enfocada en `web` y `macos`.

### Cierre documental solicitado por profesora
- Se realiza actualizacion extensa de `docs/memoria_tfg.md`.
- Se amplian resultados, incidencias, evidencias, analisis y justificacion de decisiones tecnicas.
- Se deja trazabilidad alineada entre codigo, ejecucion real y documento de memoria.

## 2026-04-06
### Entrega funcional completada (bloque clinico-hospitalario + UX paciente)
- Se cierra el flujo de alta privada para especialistas con clave interna.
- Se mantiene alta publica unicamente para pacientes.
- Se implementa mejora visual del IMC en home de paciente con tarjeta tipo rosca y flecha.
- Se incorpora accion directa para solicitar cita con nutricion desde la misma tarjeta IMC.

### Seguridad y control de acceso
- Backend: endpoint dedicado para alta profesional con validacion de clave y restriccion de roles permitidos.
- Frontend: formulario de auth ampliado con modo de registro profesional privado (rol + clave).
- Se confirma que la frontera real de seguridad se mantiene en backend.

### Funcionalidad hospitalaria avanzada
- Auditoria temporal de checklist clinico por paciente:
	- Modelo persistente de historial.
	- Versionado incremental por cada actualizacion.
	- Endpoint de consulta para timeline clinico.
- Severidad sugerida automatica desde KPIs:
	- Scoring heuristico trazable.
	- Respuesta con severidad, puntuacion y motivos.
- Export PDF hospitalario:
	- Incluye protocolo activo.
	- Incluye checklist aplicado.
	- Incluye ruta de escalado y observaciones.

### Flujo paciente IMC -> cita nutricional
- Se anade endpoint paciente para solicitar cita de nutricion.
- Si existe derivacion abierta de nutricion, se reutiliza para evitar duplicidad.
- Si no existe, se crea derivacion pendiente al nutricionista disponible.
- El flujo queda enlazado con CTA desde tarjeta IMC en frontend.

### Pruebas automatizadas agregadas (backend)
- Nuevo archivo de test: `backend/tests/test_cita_nutricion.py`.
- Casos cubiertos:
	- Creacion de derivacion nutricional desde paciente.
	- Reutilizacion de derivacion abierta.
	- Integracion completa IMC -> solicitud cita -> consulta de bandeja de derivaciones.
- Ejecucion validada:
	- 3 tests ejecutados.
	- 3 tests OK.

### Evidencia de estado final para defensa
- Backend sin errores de analisis en archivos modificados.
- Frontend sin errores de analisis en archivos modificados.
- Documentacion ampliada:
	- Memoria principal actualizada.
	- Dossier integral nuevo en `docs/documentacion_tfg_integral_2026.md`.
	- Validacion RASA extendida con estado actual.

### Siguiente paso recomendado de mantenimiento
- Mantener actualizacion incremental de bitacora tras cada bloque de funcionalidad.
- Adjuntar capturas de demo (UI, endpoints, PDFs, tests) como anexos para defensa.

## 2026-04-06 (ampliacion documental de memoria)
### Reestructuracion completa de memoria segun guia de 3 documentos
- Se rehace `docs/memoria_tfg.md` con estructura formal obligatoria:
	- Portada
	- Indice
	- Resumen/Introduccion
	- Justificacion del proyecto
	- Objetivos (general + especificos en infinitivo)
	- Desarrollo (fundamentacion teorica, materiales y metodos, resultados, analisis)
	- Conclusiones
	- Lineas de investigacion futuras
	- Bibliografia/Webgrafia en formato APA
	- Anexos
	- Apartados opcionales (retos y agradecimientos)
- Se amplian contenidos para version extensa y defendible (narrativa tecnica completa, metodologia, comparativa con objetivos y plan de mejora).
- Se deja la memoria preparada para maquetacion final en PDF (indice con placeholders de pagina).

### Separacion final por documentos independientes
- Se divide formalmente la memoria en tres archivos para respetar el esquema docente por entregas:
	- `docs/memoria_documento_1_portada_indice_resumen_justificacion_objetivos.md`
	- `docs/memoria_documento_2_desarrollo.md`
	- `docs/memoria_documento_3_conclusiones_futuro_bibliografia_anexos.md`
- Se convierte `docs/memoria_tfg.md` en indice maestro con enlaces a los tres documentos y a la documentacion de apoyo de defensa.
- Se amplian contenidos del Documento 2 con inventario tecnico completo (frontend, backend, modelos, endpoints, pruebas y flujos criticos) para no omitir detalle de implementacion.

## 2026-04-06 (ampliacion extrema por detalle)
### Ajuste solicitado: "mucho mas problemas y mas desarrollo"
- Se refuerzan los tres documentos con formato dual por seccion: resumen breve + desarrollo amplio.
- Documento 1:
	- se amplian resumen, justificacion y objetivos con mayor profundidad argumental y trazabilidad objetivo -> evidencia.
- Documento 2:
	- se incorpora bloque detallado de incidencias reales (9 problemas) con causa raiz, impacto, solucion y evidencia de cierre.
	- se anaden lecciones tecnicas consolidadas y madurez por dimension.
- Documento 3:
	- se amplian conclusiones y lineas futuras con plan por fases.
	- se anade checklist operativo de defensa y plantilla requisito -> evidencia en anexos.
- Se actualiza `docs/memoria_tfg.md` para reflejar explicitamente el nuevo formato y alcance ampliado.

## 2026-04-06 (hiper expansion final por solicitud)
### Ajuste solicitado: "mas en todos los apartados de cada documento"
- Documento 2 ampliado a version hiper-extensa:
	- arquitectura interna detallada,
	- diseño de base de datos por bloques funcionales,
	- flujos por endpoint con descripcion operativa.
- Documento 1 reforzado con mayor profundidad en planteamiento, riesgos del enfoque y consistencia objetivo-evidencia.
- Documento 3 reforzado con:
	- retos profesionales/personales ampliados,
	- agradecimientos extendidos incluyendo empresa de practicas,
	- texto formal editable para agradecimientos de entrega final.
- Resultado: memoria separada en 3 documentos con mayor densidad argumental y tecnica en todos los apartados.

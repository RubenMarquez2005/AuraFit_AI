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

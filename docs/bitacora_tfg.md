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

### Estado Git y GitHub
- Repositorio Git inicializado en rama main.
- Commits creados para dejar trazabilidad del avance.
- Remoto origin configurado hacia GitHub.
- Primer push de la rama main completado.
- URL del repositorio: https://github.com/RubenMarquez2005/AuraFit_AI
- Identidad global de Git configurada (user.name y user.email) para evitar avisos en commits.

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

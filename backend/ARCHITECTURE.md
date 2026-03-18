# AuraFit AI Backend - Architecture & Database Setup

## Architecture Overview

```
backend/
├── main.py                 # FastAPI application entry point
├── app/
│   ├── db.py              # SQLAlchemy database connection & session management
│   ├── config/
│   │   └── settings.py    # Configuration from environment variables
│   ├── models/
│   │   └── database.py    # SQLAlchemy ORM models
│   ├── schemas/
│   │   └── users.py       # Pydantic validation schemas
│   ├── api/               # API routes (to be expanded)
│   ├── services/          # Business logic layer
│   └── utils/             # Utility functions
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
└── .env                  # Local configuration (DO NOT COMMIT)
```

## Database Models

### 1. **Rol** (Roles)
- `id`: Primary key
- `nombre`: Role name (administrador, cliente, nutricionista, psicologo, coach)
- **Relationships**: One-to-many with Usuario

### 2. **Usuario** (Users)
- `id`: Primary key
- `nombre`: Full name
- `email`: Unique email address
- `password_hash`: Encrypted password
- `rol_id`: Foreign key to Rol
- `fecha_registro`: Registration timestamp
- **Relationships**: 
  - Many-to-one with Rol
  - One-to-one with PerfilSalud
  - One-to-many with RegistroDiario

### 3. **PerfilSalud** (Health Profile)
- `id`: Primary key
- `usuario_id`: Foreign key to Usuario (unique)
- `peso_actual`: Current weight (decimal)
- `altura`: Height in cm
- `imc_actual`: BMI (Body Mass Index)
- `frecuencia_gym`: Exercise frequency
- `hora_desayuno`, `hora_comida`, `hora_cena`: Meal times
- `momento_critico_picoteo`: Critical snacking moments
- `percepcion_corporal`: Body perception text
- **Relationships**: Many-to-one with Usuario

### 4. **RegistroDiario** (Daily Records)
- `id`: Primary key
- `usuario_id`: Foreign key to Usuario
- `fecha`: Date of record
- `foto_comida_url`: Food photo URL
- `analisis_nutricional_ia`: AI nutrition analysis
- `estado_animo_puntuacion`: Mood score (1-10)
- `sentimiento_detectado_ia`: Detected sentiment by AI
- `notas_diario`: Daily notes
- **Relationships**: Many-to-one with Usuario

## Pydantic Schemas

All schemas follow a pattern:
- **Base**: Common fields
- **Create**: Fields needed for creation (includes validation)
- **Update**: Optional fields for updates
- **Response**: Read-only schema with ID

### Validation Rules

| Field | Rules |
|-------|-------|
| Email | Valid email format (EmailStr) |
| Password | Min 8 chars, 1 uppercase, 1 digit |
| Weight | > 0, <= 300 kg |
| Height | > 0, <= 250 cm |
| BMI | > 0, <= 100 |
| Mood Score | 1-10 |

## Environment Variables

Copy `.env.example` to `.env` and set your values:

```bash
# Application
APP_NAME=AuraFit AI
DEBUG=True

# Database (MySQL)
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=root
DB_NAME=aurafit_db

# API Server
API_HOST=0.0.0.0
API_PORT=8000
```

## Database Connection Flow

1. **Settings Loading** (`app/config/settings.py`)
   - Reads `.env` file
   - Builds MySQL connection URL

2. **SQLAlchemy Engine** (`app/db.py`)
   - Creates connection pool
   - Connection string: `mysql+mysqlconnector://user:pass@host:port/db`
   - Pool size: 5, max overflow: 10

3. **Startup Event** (`main.py`)
   - Creates all tables if they don't exist (`Base.metadata.create_all()`)
   - Verifies database connection with test query
   - Logs success/failure

## Health Check Endpoints

- **GET `/health`** - Application health (always available)
- **GET `/health/db`** - Database connection status
- **GET `/docs`** - Interactive API documentation (Swagger UI)

## Usage Examples

### Creating a Session
```python
from app.db import SessionLocal

db = SessionLocal()
try:
    # Your database operations
    pass
finally:
    db.close()
```

### Using in FastAPI Routes
```python
from fastapi import FastAPI, Depends
from app.db import get_db
from sqlalchemy.orm import Session

@app.get("/users/")
def list_users(db: Session = Depends(get_db)):
    return db.query(Usuario).all()
```

### Creating a User with Pydantic Validation
```python
from app.schemas import UsuarioCreate

user_data = UsuarioCreate(
    nombre="John Doe",
    email="john@example.com",
    password="SecurePass123"
)
# Password is validated automatically
```

## Connection String Format

```
mysql+mysqlconnector://root:root@localhost:3306/aurafit_db
                      │    │    │         │      │
                      user pass host      port   database
```

## Best Practices Implemented

✅ Environment-based configuration  
✅ Connection pooling for performance  
✅ ORM for type-safe queries  
✅ Pydantic for validation  
✅ Async database checks  
✅ Relationship management  
✅ Error handling & logging  
✅ Clean separation of concerns  

## Next Steps

1. Create API routes in `app/api/`
2. Implement authentication
3. Add service layer for business logic
4. Create unit tests
5. Add database migrations (Alembic)

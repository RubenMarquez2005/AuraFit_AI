# AuraFit AI

Monorepo del TFG con frontend en Flutter y backend en FastAPI + MySQL.

## Estructura

```
AuraFit_AI/
├── frontend/                    # Proyecto Flutter
├── backend/                     # API en FastAPI
│   ├── app/
│   │   ├── api/
│   │   ├── config/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── utils/
│   ├── main.py
│   ├── run.py
│   ├── requirements.txt
│   └── .env.example
├── ai_rasa/                     # Asistente conversacional local (RASA)
│   ├── actions/
│   ├── data/
│   ├── models/
│   ├── tests/
│   ├── config.yml
│   ├── domain.yml
│   ├── credentials.yml
│   └── endpoints.yml
├── database/                    # Scripts SQL
└── docs/                        # Memoria y bitacora del proyecto
```

## Backend (macOS)

### Requisitos
- Python 3.9+
- MySQL 8+

### Instalacion

1. Instalar dependencias:
```bash
cd backend
pip3 install -r requirements.txt
```

2. Configurar variables de entorno:
```bash
cp .env.example .env
```

3. Ejecutar API:
```bash
python3 run.py
```

### Endpoints utiles
- http://localhost:8001/docs
- http://localhost:8001/health
- http://localhost:8001/health/db

### Endpoint de autenticacion

`POST /login`

Ejemplo de body JSON:

```json
{
	"email": "usuario@correo.com",
	"password": "TuClave123"
}
```

Respuesta esperada:

```json
{
	"usuario_id": 1,
	"nombre": "Nombre Usuario",
	"email": "usuario@correo.com",
	"rol": "cliente"
}
```

### Alta de usuarios (para pruebas)

Los usuarios se guardan en la tabla `usuarios` y el rol se vincula por `rol_id`.

Script recomendado (genera hash bcrypt automaticamente):

```bash
cd backend
python3 scripts/crear_usuario.py \
	--nombre "Ana Lopez" \
	--email "ana@aurafit.ai" \
	--password "AnaClave123" \
	--rol cliente
```

Roles permitidos: `administrador`, `cliente`, `nutricionista`, `psicologo`, `coach`.

## Frontend

```bash
cd frontend
flutter pub get
flutter run
```

## RASA local (ai_rasa)

1. Crear entorno e instalar RASA:
```bash
cd ai_rasa
python3 -m venv venv_rasa
./venv_rasa/bin/python -m pip install --upgrade pip
./venv_rasa/bin/python -m pip install rasa
```

2. Inicializar proyecto base:
```bash
./venv_rasa/bin/rasa init --no-prompt
```

3. Levantar servidor RASA en puerto 5005:
```bash
./venv_rasa/bin/rasa run --enable-api --cors '*' --port 5005
```

4. Consumir desde backend FastAPI:
- Endpoint: `POST /chat/rasa`
- URL por defecto de RASA usada por backend: `http://127.0.0.1:5005/webhooks/rest/webhook`

## Base de datos

El script SQL base esta en `database/db_AuraFIT.sql`.

## Nota del proyecto

El desarrollo esta orientado a macOS. Los comandos del README se han preparado para este entorno.

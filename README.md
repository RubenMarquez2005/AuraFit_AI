# 🌟 AuraFit AI - Aplicación de Bienestar Integral

Plataforma de IA para salud mental, nutrición, entrenamientos y bienestar integral.

## 📊 Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                    🌐 Frontend (Flutter)                     │
│  ┌──────────────┬──────────────┬──────────────┐             │
│  │ Web Browser  │ macOS Desktop│ (iOS/Android │             │
│  │ (Web/Chrome) │              │  en futuro)  │             │
│  └──────────────┴──────────────┴──────────────┘             │
│              ↓ HTTP (BackendService)                         │
├─────────────────────────────────────────────────────────────┤
│          ⚙️  Backend (FastAPI - Puerto 8001)               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   /chat     │  │ /perfil/*   │  │  /health    │        │
│  │  (INTEGRACION RASA)         │                │        │
│  └─────────────┴──────────────────┴─────────────┘        │
│              ↓ HTTP (requests)                             │
├─────────────────────────────────────────────────────────────┤
│         🤖 RASA Open Source (Puerto 5005)                  │
│  ┌─────────────────────────────────────────────┐          │
│  │  NLU: Intenciones en Español (saludar,     │          │
│  │        informar_peso, estado_animo_mal)    │          │
│  │                                             │          │
│  │  Respuestas: Empáticas y profesionales     │          │
│  └─────────────────────────────────────────────┘          │
│              ↓ SQL (SQLAlchemy)                            │
├─────────────────────────────────────────────────────────────┤
│         💾 MySQL (Puerto 3306)                             │
│  Base de datos: aurafit_db                                 │
│  - Usuarios, Perfiles de Salud, Registros Diarios          │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Inicio Rápido

### Opción 0: Docker (Todo el proyecto con un comando)

Levanta frontend + backend + RASA + MySQL en contenedores.

```bash
./docker-up.sh
```

Servicios disponibles:
- Frontend: http://localhost:3000
- Backend: http://localhost:8001/docs
- RASA: http://localhost:5005
- MySQL: localhost:3307 (por defecto)

Para detener todo:

```bash
./docker-down.sh
```

Si quieres personalizar claves o proveedor IA (Gemini/Qwen), copia y edita:

```bash
cp .env.docker.example .env
```

### Opción 1: Ejecutor Automático (Recomendado)

```bash
chmod +x run-all.sh
./run-all.sh
```

Selecciona:
- **1** para Backend
- **2** para RASA
- **3** para Frontend Web
- **5** para todo junto

### Opción 2: Scripts Individuales

#### Backend FastAPI
```bash
chmod +x run-backend.sh
./run-backend.sh
```
✅ Disponible en: `http://127.0.0.1:8001`
📚 Docs: `http://127.0.0.1:8001/docs`

#### RASA IA
```bash
chmod +x run-rasa.sh
./run-rasa.sh
```
✅ Disponible en: `http://127.0.0.1:5005`

#### Frontend Web
```bash
chmod +x run-web.sh
./run-web.sh
```
✅ Se abrirá automáticamente en navegador

#### Frontend macOS Desktop
```bash
chmod +x run-macos.sh
./run-macos.sh
```
✅ Aplicación nativa de macOS

## 🎨 Sistema de Colores Profesional

Cada sección tiene su propia identidad visual:

| Sección | Color Primario | Uso |
|---------|---|---|
| 🏠 **Inicio** | Azul `#5B8DEE` | Dashboard general |
| 🍽️ **Nutrición** | Naranja `#FF9F43` | Alimentación |
| 💪 **Gym** | Verde `#10B981` | Entrenamientos |
| 🧠 **Salud Mental** | Púrpura `#9F7AEA` | Bienestar emocional |
| 🤖 **Chat IA** | Cian `#06B6D4` | Comunicación IA |

### Paleta General
- **Fondo**: `#F8F9FD` (gris muy claro)
- **Superficie**: `#FFFFFF` (blanco)
- **Texto oscuro**: `#1A1A2E`
- **Texto claro**: `#757575` (gris)

## 📁 Estructura del Proyecto

```
AuraFit_AI/
├── frontend/                      # App Flutter
│   ├── lib/
│   │   ├── main.dart             # Entrada principal
│   │   ├── config/
│   │   │   └── app_colors.dart   # Sistema de colores
│   │   ├── pages/
│   │   │   ├── home_page.dart    # Dashboard
│   │   │   ├── nutrition_page.dart
│   │   │   ├── gym_page.dart
│   │   │   ├── mental_health_page.dart
│   │   │   └── chat_page.dart
│   │   ├── services/
│   │   │   └── backend_service.dart
│   │   └── providers/
│   │       └── chat_provider.dart
│   └── pubspec.yaml              # Dependencias
│
├── backend/                       # API FastAPI
│   ├── main.py                   # Punto de entrada
│   ├── app/
│   │   ├── models/               # Modelos BD
│   │   ├── services/             # Lógica
│   │   └── api/                  # Rutas
│   ├── services/
│   │   ├── rasa_service.py       # Integración RASA
│   │   └── gemini_service.py     # Gemini API
│   └── requirements.txt          # Dependencias
│
├── ai_rasa/                       # Chatbot RASA
│   ├── data/
│   │   └── nlu.yml               # Intenciones en español
│   ├── domain.yml                # Respuestas empáticas
│   └── models/                   # Modelos entrenados
│
├── docs/
│   ├── bitacora_tfg.md           # Log de desarrollo
│   └── memoria_tfg.md            # Documentación académica
│
└── Estos scripts:
    ├── run-all.sh                # Ejecutor maestro
    ├── run-backend.sh
    ├── run-rasa.sh
    ├── run-web.sh
    └── run-macos.sh
```

## 📚 Documentación TFG (Actualizada)

- Documento principal de memoria: `docs/memoria_tfg.md`
- Bitácora cronológica de avances: `docs/bitacora_tfg.md`
- Dossier técnico integral de defensa: `docs/documentacion_tfg_integral_2026.md`
- Guion completo de defensa (narrativa + demo + tribunal): `docs/guion_defensa_tfg_completo.md`
- Validación NLU y estrategia RASA: `RASA_VALIDATION_TFG.md`

## ✅ Evidencia de pruebas backend

- Suite RBAC clínico: `backend/tests/test_rbac_clinico.py`
- Suite cita nutricional e integración IMC->cita: `backend/tests/test_cita_nutricion.py`

Ejecución recomendada desde `backend`:

```bash
/Users/rubenperez/Documents/AuraFit_AI/backend/venv/bin/python -m unittest tests.test_rbac_clinico -v
/Users/rubenperez/Documents/AuraFit_AI/backend/venv/bin/python -m unittest tests.test_cita_nutricion -v
```

## 🔌 Endpoints Principales

### POST /chat
Envía un mensaje y obtiene respuesta de IA con detección de peso

```bash
curl -X POST http://127.0.0.1:8001/chat \
  -H "Content-Type: application/json" \
  -d '{
    "mensaje": "He pesado 80kg hoy",
    "sender": "usuario123"
  }'
```

Respuesta:
```json
{
  "ok": true,
  "sender": "usuario123",
  "respuesta_ia": "Excelente, gracias por registrar tu peso...",
  "peso_registrado": 80.0,
  "mensaje_peso": "Peso registrado: 80kg"
}
```

### GET /health
Verifica estado de la API

```bash
curl http://127.0.0.1:8001/health
```

### GET /docs
Documentación interactiva (Swagger UI)

```
http://127.0.0.1:8001/docs
```

## 🎯 Características Actuales

✅ **Backend**
- API REST con FastAPI
- Integración RASA webhook
- Extracción inteligente de peso
- Detección de consejos de salud
- CORS configurado para Web + macOS
- Documentación Swagger

✅ **Frontend**
- Interfaz responsiva (Web + macOS)
- NavigationRail para desktop
- Chat bot con burbujas modernas
- Gestor de estado con Provider
- Colores temáticos por sección
- Google Fonts (Inter)

✅ **RASA**
- 11 intenciones en español
- Respuestas empáticas
- API REST habilitada
- Modelo entrenado y listo

✅ **Base de Datos**
- MySQL integrada
- Autenticación de usuarios
- Perfiles de salud
- Registros diarios

## 🔐 Configuración

### .env (Backend)
```
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=Curso2026@
DB_NAME=aurafit_db

RASA_WEBHOOK_URL=http://127.0.0.1:5005/webhooks/rest/webhook
RASA_TIMEOUT_SECONDS=30

GEMINI_API_KEY=AIzaSyC...
```

## 🧪 Prueba completa E2E

1. **Inicia RASA**
   ```bash
   ./run-rasa.sh
   ```

2. **Inicia Backend** (nueva terminal)
   ```bash
   ./run-backend.sh
   ```

3. **Inicia Frontend** (nueva terminal)
   ```bash
   ./run-web.sh
   # o
   ./run-macos.sh
   ```

4. **Envía un mensaje** en la UI:
   - Escribe: "Hola, hoy pesé 75kg"
   - Verás: Respuesta empática + peso registrado

## 📊 Monitoreo

### Ver logs de Backend
```bash
# Los logs aparecen en la terminal
tail -f logs/backend.log  # Si existen
```

### Ver estado de RASA
```bash
curl http://127.0.0.1:5005/webhooks/rest/webhook \
  -X POST \
  -d '{"message":"test"}'
```

### Ver estado de Frontend
- Abre: `http://localhost:5000` (web)
- O ejecuta la app macOS

## 🛠️ Desarrollo

### Agregar nueva página
1. Crear archivo en `frontend/lib/pages/nueva_page.dart`
2. Importar en `frontend/lib/main.dart`
3. Agregar a `AppSection` enum
4. Agregar a `_navItems`

### Modificar paleta de colores
- Editar: `frontend/lib/config/app_colors.dart`
- Los cambios se reflejan globalmente

### Entrenar nuevo modelo RASA
```bash
cd ai_rasa
rasa train
```

## 🐛 Troubleshooting

### "Flutter no encontrado"
```bash
export PATH="$PATH:$HOME/flutter/bin"
```

### "Port 8001 already in use"
```bash
lsof -i :8001
kill -9 <PID>
```

### "RASA connection refused"
- Verifica que RASA está corriendo en puerto 5005
- Comprueba con: `curl http://127.0.0.1:5005/health`

### "MySQL connection error"
```bash
# Verifica credenciales en .env
mysql -u root -p -h 127.0.0.1
```

## 📚 Documentación Adicional

- [Bitácora de Desarrollo](docs/bitacora_tfg.md)
- [Memoria TFG](docs/memoria_tfg.md)
- [RASA Docs](https://rasa.com/docs/)
- [Flutter Docs](https://flutter.dev/docs)
- [FastAPI Docs](https://fastapi.tiangolo.com/)

## 🎓 Profesora

Referencia académica para la defensa del TFG: AuraFit AI
Basado en alcance Web + macOS Desktop.

## 📝 Licencia

Proyecto académico - Universidad

---

**Último commit:**
```
9fb95b2 - PASO 2-4: Entrenar RASA, integrar backend, y diseñar UI profesional
```

**Última actualización:** 2 de abril de 2026

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

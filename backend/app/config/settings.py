from pydantic_settings import BaseSettings
from urllib.parse import quote_plus
from pathlib import Path


ENV_PATH = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    """Configuracion de la aplicacion leida desde variables de entorno."""

    # Configuracion de la aplicacion
    APP_NAME: str = "AuraFit AI"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # Configuracion de base de datos
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = "root"
    DB_NAME: str = "aurafit_db"

    # Configuracion de la API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8001

    # Configuracion de autenticacion
    AUTH_SECRET_KEY: str = "aurafit_dev_secret_cambiar"
    AUTH_TOKEN_EXP_MINUTES: int = 1440
    PROFESSIONAL_REGISTRATION_KEY: str = "AURAFIT_PRO_2026"

    # Configuracion del servicio de IA (Gemini)
    IA_PROVIDER: str = "gemini"
    IA_RESPONSE_MODE: str = "ultra_pro"
    IA_AUTONOMOUS_MODE: bool = True
    IA_TESTING_MODE: bool = False
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"
    GEMINI_TEMPERATURE: float = 0.2
    GEMINI_MAX_OUTPUT_TOKENS: int = 2400
    IA_ATTACHMENTS_MAX_MB: int = 25
    IA_FALLBACK_LOCAL: bool = True
    PREMIUM_MEDIA_MOCK: bool = False

    # Configuracion del servicio de IA (Qwen / OpenAI-compatible)
    QWEN_API_KEY: str = ""
    QWEN_BASE_URL: str = ""
    QWEN_MODEL: str = "qwen3-32b-instruct"
    QWEN_SUPPORTS_MULTIMODAL: bool = False

    # Configuracion premium multimodal (generacion real de imagen/video)
    PREMIUM_MEDIA_ENABLED: bool = True
    PREMIUM_IMAGE_PROVIDER: str = "openai"
    PREMIUM_VIDEO_PROVIDER: str = "replicate"
    OPENAI_API_KEY: str = ""
    OPENAI_IMAGE_MODEL: str = "gpt-image-1"
    OPENAI_IMAGE_SIZE: str = "1024x1024"
    PREMIUM_IMAGE_RETRIES: int = 2
    REPLICATE_API_TOKEN: str = ""
    REPLICATE_VIDEO_MODEL: str = "kwaivgi/kling-v1.6-standard"
    REPLICATE_VIDEO_FALLBACK_MODELS: str = ""
    PREMIUM_VIDEO_RETRIES: int = 2
    PREMIUM_VIDEO_POLL_SECONDS: float = 2.0
    PREMIUM_VIDEO_TIMEOUT_SECONDS: int = 120

    # Configuracion del servicio RASA
    RASA_WEBHOOK_URL: str = "http://127.0.0.1:5005/webhooks/rest/webhook"
    RASA_TIMEOUT_SECONDS: int = 20

    class Config:
        env_file = str(ENV_PATH)
        case_sensitive = True
        extra = "ignore"

    @property
    def DATABASE_URL(self) -> str:
        """Construye la URL de conexion MySQL para SQLAlchemy."""
        user = quote_plus(self.DB_USER)
        password = quote_plus(self.DB_PASSWORD)
        return (
            f"mysql+mysqlconnector://"
            f"{user}:{password}@"
            f"{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )


settings = Settings()

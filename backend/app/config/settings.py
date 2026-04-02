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

    # Configuracion del servicio de IA (Gemini)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"
    IA_FALLBACK_LOCAL: bool = True

    # Configuracion del servicio RASA
    RASA_WEBHOOK_URL: str = "http://127.0.0.1:5005/webhooks/rest/webhook"
    RASA_TIMEOUT_SECONDS: int = 20

    class Config:
        env_file = str(ENV_PATH)
        case_sensitive = True

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

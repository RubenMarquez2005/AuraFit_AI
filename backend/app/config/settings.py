from pydantic_settings import BaseSettings


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
    API_PORT: int = 8000

    class Config:
        env_file = ".env"
        case_sensitive = True

    @property
    def DATABASE_URL(self) -> str:
        """Construye la URL de conexion MySQL para SQLAlchemy."""
        return (
            f"mysql+mysqlconnector://"
            f"{self.DB_USER}:{self.DB_PASSWORD}@"
            f"{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )


settings = Settings()

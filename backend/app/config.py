from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    database_url_sync: str
    secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    admin_email: str
    admin_password: str
    cloudinary_cloud_name: str = ""
    cloudinary_api_key: str = ""
    cloudinary_api_secret: str = ""
    upload_dir: str = "uploads"
    site_url: str
    cors_origins: str

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

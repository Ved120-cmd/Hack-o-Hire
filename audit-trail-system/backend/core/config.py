"""
Configuration settings for the Audit Trail System
"""
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, PostgresDsn
import os


class Settings(BaseSettings):
    """Application settings and configuration"""
    
    # Application
    APP_NAME: str = "SAR Audit Trail System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False, env="DEBUG")
    ENVIRONMENT: str = Field(default="production", env="ENVIRONMENT")
    
    # Database
    DATABASE_URL: PostgresDsn = Field(
        default="postgresql://user:password@localhost:5432/sar_audit",
        env="DATABASE_URL"
    )
    DB_ECHO: bool = Field(default=False, env="DB_ECHO")
    DB_POOL_SIZE: int = Field(default=10, env="DB_POOL_SIZE")
    DB_MAX_OVERFLOW: int = Field(default=20, env="DB_MAX_OVERFLOW")
    
    # Audit Settings
    AUDIT_RETENTION_DAYS: int = Field(default=2555, env="AUDIT_RETENTION_DAYS")  # 7 years
    ENABLE_AUDIT_LOGGING: bool = Field(default=True, env="ENABLE_AUDIT_LOGGING")
    AUDIT_BATCH_SIZE: int = Field(default=100, env="AUDIT_BATCH_SIZE")
    
    # Security
    SECRET_KEY: str = Field(default="change-this-secret-key-in-production", env="SECRET_KEY")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = "json"  # json or text
    LOG_FILE_PATH: Optional[str] = Field(default=None, env="LOG_FILE_PATH")
    
    # API
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: list = ["*"]
    
    # Performance
    MAX_AUDIT_QUERY_LIMIT: int = Field(default=1000, env="MAX_AUDIT_QUERY_LIMIT")
    DEFAULT_PAGE_SIZE: int = Field(default=50, env="DEFAULT_PAGE_SIZE")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Dependency to get settings instance"""
    return settings

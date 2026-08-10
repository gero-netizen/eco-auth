from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = "sqlite:///./isp_field.db"
    mkauth_mode: str = "simulated"
    mkauth_base_url: str = "http://mkauth.test.invalid"
    mkauth_client_id: str = ""
    mkauth_client_secret: str = ""
    mkauth_verify_ssl: bool = True
    mkauth_allow_http: bool = False
    mkauth_writes_enabled: bool = False
    routeros_mode: str = "simulated"
    routeros_host: str = "192.168.20.1"
    routeros_port: int = 8728
    routeros_username: str = ""
    routeros_password: str = ""
    olt_mode: str = "simulated"
    jwt_secret: str = "development-only-change-me"
    central_username: str = ""
    central_password: str = ""
    platform_admin_username: str = ""
    platform_admin_password: str = ""
    technician_username: str = ""
    technician_password: str = ""
    default_organization_id: str = "g7-networks"
    default_organization_name: str = "G7 Networks"
    default_organization_slug: str = "g7-networks"
    integration_encryption_key: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()

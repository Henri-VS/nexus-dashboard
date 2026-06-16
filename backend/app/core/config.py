from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"

    # Paths
    nexus_data_dir: str = Field(default="/app/data", validation_alias=AliasChoices("NEXUS_DATA_DIR", "nexus_data_dir"))
    obsidian_vault_path: str = Field(default="/vault", validation_alias=AliasChoices("OBSIDIAN_VAULT_PATH", "obsidian_vault_path"))
    db_path: str = Field(default="/app/data/dashboard.db", validation_alias=AliasChoices("DB_PATH", "db_path"))

    # Ollama — accepts OLLAMA_HOST or OLLAMA_BASE_URL
    ollama_host: str = Field(
        default="http://localhost:11434",
        validation_alias=AliasChoices("OLLAMA_HOST", "OLLAMA_BASE_URL", "ollama_host", "ollama_base_url"),
    )
    ollama_default_model: str = "qwen3.5:9b"

    @field_validator("ollama_host", mode="before")
    @classmethod
    def ensure_ollama_scheme(cls, v: str) -> str:
        if v and not v.startswith(("http://", "https://")):
            return f"http://{v}"
        return v

    # Home Assistant — accepts HA_HOST or HA_URL
    ha_url: str = Field(
        default="http://host.docker.internal:8124",
        validation_alias=AliasChoices("HA_HOST", "HA_URL", "ha_host", "ha_url"),
    )
    ha_token: str = Field(default="", validation_alias=AliasChoices("HA_TOKEN", "ha_token"))

    # Wazuh — accepts WAZUH_HOST / WAZUH_PASS or the older names
    wazuh_api_url: str = Field(
        default="http://host.docker.internal:55000",
        validation_alias=AliasChoices("WAZUH_HOST", "WAZUH_API_URL", "wazuh_host", "wazuh_api_url"),
    )
    wazuh_user: str = Field(default="wazuh", validation_alias=AliasChoices("WAZUH_USER", "wazuh_user"))
    wazuh_password: str = Field(default="", validation_alias=AliasChoices("WAZUH_PASS", "WAZUH_PASSWORD", "wazuh_pass", "wazuh_password"))
    wazuh_verify_ssl: bool = Field(default=True, validation_alias=AliasChoices("WAZUH_VERIFY_SSL", "wazuh_verify_ssl"))

    # MQTT
    mqtt_host: str = "host.docker.internal"
    mqtt_port: int = 1883
    mqtt_username: str = ""
    mqtt_password: str = ""

    # Weather — set your location in .env (see .env.example)
    weather_lat: float = 0.0
    weather_lon: float = 0.0
    weather_location_name: str = ""

    # TryHackMe
    thm_username: str = ""

    # Auth / CORS
    nexus_secret_key: str = Field(default="", validation_alias=AliasChoices("NEXUS_SECRET_KEY", "nexus_secret_key"))
    nexus_frontend_url: str = Field(default="", validation_alias=AliasChoices("NEXUS_FRONTEND_URL", "nexus_frontend_url"))

    # Ntfy push notifications
    ntfy_url: str = Field(default="https://ntfy.sh", validation_alias=AliasChoices("NTFY_URL", "ntfy_url"))
    ntfy_topic: str = Field(default="", validation_alias=AliasChoices("NTFY_TOPIC", "ntfy_topic"))


settings = Settings()

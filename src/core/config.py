# src/core/config.py
import os
import yaml
from pydantic_settings import BaseSettings
from pydantic import Field, PostgresDsn, AnyUrl
import logging

logger = logging.getLogger(__name__)

# ::CONFIG_CLASS:: - Defines application configuration structure
class Config(BaseSettings):
    """Application configuration settings."""
    database_url: AnyUrl | None = None # Accepts various URL types
    default_db_type: str = "sqlite"
    default_sqlite_db_name: str = "vct_data.db"
    config_yaml_path: str = "config.yaml"
    logging_config_path: str = "logging_config.yaml"

    db_username: str | None = Field(None, validation_alias="POSTGRES_USER", env="POSTGRES_USER")
    db_password: str | None = Field(None, validation_alias="POSTGRES_PASSWORD", env="POSTGRES_PASSWORD")
    db_host: str | None = Field(None, validation_alias="POSTGRES_HOST", env="POSTGRES_HOST")
    db_port: int | None = Field(None, validation_alias="POSTGRES_PORT", env="POSTGRES_PORT")
    db_name: str | None = Field(None, validation_alias="POSTGRES_DB", env="POSTGRES_DB")

    class Config:
        env_file = '.env' # Load .env file if exists
        env_file_encoding = 'utf-8'
        extra = 'ignore' # Ignore extra fields found in env file or YAML

# ::HELPER_FUNCTION:: - Loads configuration from YAML and environment
def load_config(config_path: str = "config.yaml", env_file: str | None = ".env") -> Config:
    """
    Loads configuration settings, prioritizing environment variables,
    then .env file, then YAML file, and finally defaults.
    """
    yaml_config = {}
    config_file_to_load = os.getenv("CONFIG_FILE", config_path) # Allow overriding config path via env var

    # Try loading from YAML first (lowest priority besides defaults)
    if os.path.exists(config_file_to_load):
        try:
            with open(config_file_to_load, 'r', encoding='utf-8') as f:
                yaml_config = yaml.safe_load(f) or {}
                logger.info(f"Loaded configuration defaults from: {config_file_to_load}")
        except Exception as e:
            logger.warning(f"Could not load or parse YAML config '{config_file_to_load}': {e}")
            yaml_config = {}
    else:
        logger.info(f"Configuration file '{config_file_to_load}' not found. Using environment variables and defaults.")

    # Pydantic-settings automatically handles .env and environment variables
    # We pass YAML values as initial values if they exist
    # Note: Pydantic-settings prioritizes env vars over initial values
    effective_config_data = yaml_config.get('settings', {}) # Assuming settings are under 'settings' key in YAML

    try:
        # Load using Pydantic, which handles env vars and .env file automatically
        # Pass YAML values using `_init_` mechanism is complex with nested models
        # A simpler way might be to load base settings first, then update with YAML if needed,
        # but Pydantic's priority is usually Env > .env > init > defaults.
        # Let's rely on Pydantic's default behavior for .env and env vars.
        # We'll primarily use YAML for non-sensitive defaults.

        # Create Config instance. Pydantic loads .env and env vars.
        config = Config(_env_file=env_file or '.env')

        # Manually merge YAML *if* env vars didn't provide the value
        # This is tricky because Pydantic already loaded env vars.
        # A common pattern is to use YAML for BASE defaults if env vars are not set.
        # Let's enhance get_database_url to use YAML defaults if env vars aren't complete.

        config.config_yaml_path = config_file_to_load # Store the actual path used

        return config

    except Exception as e:
        logger.error(f"Failed to initialize configuration: {e}", exc_info=True)
        # Return default config on error? Or raise? Let's return default for now.
        return Config()

# ::HELPER_FUNCTION:: - Determines the final database URL
def get_database_url(config: Config) -> str:
    """
    Determines the database URL to use, prioritizing environment variables,
    then values constructed from specific DB env vars (POSTGRES_*),
    then YAML configuration, and finally a default SQLite setup.
    """
    # 1. Explicit DATABASE_URL environment variable (highest priority)
    if os.getenv("DATABASE_URL"):
        db_url = os.getenv("DATABASE_URL")
        print("使用环境变量 'DATABASE_URL'.")
        logger.info("Using DATABASE_URL from environment variable.")
        # Basic validation might be good here, but AnyUrl in Config handles it partially
        return db_url

    # 2. Construct PostgreSQL URL from specific env vars if all are present
    if config.db_username and config.db_password is not None and config.db_host and config.db_port and config.db_name:
        db_url = str(PostgresDsn.build(
            scheme="postgresql+psycopg2", # Or asyncpg if using async
            username=config.db_username,
            password=config.db_password,
            host=config.db_host,
            port=config.db_port,
            path=config.db_name,
        ))
        print("使用环境变量 'POSTGRES_*' 构建 PostgreSQL 连接.")
        logger.info("Constructed PostgreSQL URL from POSTGRES_* environment variables.")
        return db_url

    # 3. Try DATABASE_URL from YAML file (loaded via `load_config` into `config` object)
    # Need to reload YAML here as Pydantic might have ignored it if env vars were present
    yaml_url = None
    if os.path.exists(config.config_yaml_path):
        try:
            with open(config.config_yaml_path, 'r', encoding='utf-8') as f:
                 yaml_data = yaml.safe_load(f) or {}
                 yaml_url = yaml_data.get('settings', {}).get('database_url')
        except Exception:
            pass # Ignore errors reading YAML here, we'll use default

    if yaml_url:
        print(f"使用 config.yaml 中的 'database_url'.")
        logger.info(f"Using database_url from {config.config_yaml_path}.")
        return str(AnyUrl(yaml_url)) # Validate/convert using Pydantic's AnyUrl

    # 4. Default to SQLite in the project root if nothing else is defined
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # Get project root (adjust if needed)
    # Check YAML for default DB type or name if provided
    default_type = yaml_data.get('settings', {}).get('default_db_type', 'sqlite') if 'yaml_data' in locals() else 'sqlite'
    default_name = yaml_data.get('settings', {}).get('default_sqlite_db_name', 'vct_data.db') if 'yaml_data' in locals() else 'vct_data.db'

    # Only use SQLite default if type is explicitly or implicitly sqlite
    if default_type.lower() == "sqlite":
        # Ensure the path is absolute for SQLite
        sqlite_path = os.path.join(project_root, default_name)
        # Use sqlite+pysqlite driver explicitly
        db_url = f"sqlite+pysqlite:///{sqlite_path}"
        print(f"未找到环境变量 'DATABASE_URL'。将使用 config.yaml 中的 SQLite 配置 (或默认)。")
        logger.info(f"Defaulting to SQLite database: {db_url}")
        return db_url
    else:
        # If default type is not SQLite and other options failed, raise error
        error_msg = "数据库配置不完整：未找到DATABASE_URL, POSTGRES_*变量不全，且默认类型不是SQLite。"
        logger.error(error_msg)
        raise ValueError(error_msg)

# Example of loading config (usually done in manage.py or main application entry point)
# if __name__ == "__main__":
#     config = load_config()
#     db_url = get_database_url(config)
#     print(f"Effective DB URL: {db_url}")
#     print(config.model_dump())
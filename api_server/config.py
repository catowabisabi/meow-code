from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 7778
    debug: bool = False
    data_dir: Path = Path.home() / ".claude"

    model_config = {"env_prefix": "CATO_"}
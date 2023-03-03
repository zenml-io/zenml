from functools import lru_cache
from typing import Optional

from pydantic import BaseSettings


class Settings(BaseSettings):
    SERVER_URL: str = "https://staginghub.zenml.io/"
    AUTH_TOKEN: Optional[str] = None

    class Config:
        env_file = ".hub.env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()

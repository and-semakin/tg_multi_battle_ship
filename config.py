from pydantic import BaseSettings


class Config(BaseSettings):
    bot_token: str

    class Config:
        env_prefix = "APP_"

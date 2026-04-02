from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "Boran AI"
    app_version: str = "0.1.0"
    lm_studio_base_url: str = "http://127.0.0.1:1234/v1"
    model_name: str = "qwen2.5-7b-instruct"


settings = Settings()
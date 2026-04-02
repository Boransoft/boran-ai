import requests

from app.config import settings


def run_smoke_test() -> None:
    payload = {
        "model": settings.model_name,
        "messages": [
            {"role": "system", "content": "Sen Turkce cevap veren yardimci asistansin."},
            {"role": "user", "content": "Merhaba, bana kisa bir selam ver."},
        ],
        "temperature": 0.7,
        "max_tokens": 200,
    }

    response = requests.post(
        f"{settings.lm_studio_base_url}/chat/completions",
        json=payload,
        timeout=120,
    )
    response.raise_for_status()
    print(response.status_code)
    print(response.text)


if __name__ == "__main__":
    run_smoke_test()

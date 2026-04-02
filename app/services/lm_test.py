import requests

url = "http://127.0.0.1:1234/v1/chat/completions"

payload = {
    "model": "qwen2.5-7b-instruct",
    "messages": [
        {
            "role": "system",
            "content": "Sen Türkçe cevap veren yardımcı bir asistansın."
        },
        {
            "role": "user",
            "content": "Merhaba, bana kısa bir selam ver."
        }
    ],
    "temperature": 0.7,
    "max_tokens": 200
}

response = requests.post(url, json=payload, timeout=120)
print(response.status_code)
print(response.text)
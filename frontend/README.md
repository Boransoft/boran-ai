# boranizm frontend (mobile-first PWA MVP)

React + Vite + TypeScript + Tailwind ile tek ekranli (login haric) birlesik arayuz.

Ek not: Multi-file document upload desteklenir (ayni anda birden fazla dosya secilebilir, dosya basi varsayilan 100MB siniri, eszamanli en fazla 3 upload).
Ek not: UI'da Turkce karakterlerin bozulmamasi icin tum kaynak dosyalari UTF-8 olmalidir.
Login sonrasi **tek ana ekran** icinde:
- yazili chat (`POST /chat`)
- sesli chat (`POST /voice/chat`)
- ses transcribe (`POST /voice/transcribe`)
- metinden ses (`POST /voice/speak`)
- belge yukleme (`POST /learning/ingest/document`)
- ayni message stream icinde transcript + AI cevap + audio player + sistem mesajlari

## Kurulum

```bash
cd frontend
npm install
```

## Ortam Degiskenleri

`.env.example` dosyasini `.env` olarak kopyala:

```bash
cp .env.example .env
```

Ornek:

```env
VITE_API_BASE_URL=
VITE_MAX_UPLOAD_SIZE_MB=100
```

Not:
- Frontend API URL'i sadece `VITE_API_BASE_URL` degerinden okunur.
- `VITE_API_BASE_URL` bos ise frontend otomatik `http(s)://<mevcut-host>:8000` kullanir.
- Upload limit bilgisi `VITE_MAX_UPLOAD_SIZE_MB` ile ayarlanir (varsayilan 100 MB).
- Mobilde gerekirse acikca `VITE_API_BASE_URL=http://<PC_LAN_IP>:8000` verebilirsin.

## Gelistirme

Backend (repo root):

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cd frontend
npm run dev -- --host 0.0.0.0
```

Ac:
- `http://localhost:5173` (desktop)
- `http://<PC_LAN_IP>:5173` (mobile)

## Production Build

```bash
cd frontend
npm run build
npm run preview -- --host
```

## Mobil Tarayicida Test

1. Backend'i LAN'dan erisilebilir sekilde baslat: `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
2. `frontend/.env` icinde `VITE_API_BASE_URL` degerini bos birak (otomatik host kullanimi) veya `http://<PC_LAN_IP>:8000` olarak ayarla.
3. Frontend env degistiyse yeniden build al: `npm run build`.
4. Preview ac: `npm run preview -- --host`.
5. Telefon ve bilgisayari ayni Wi-Fi agina bagla.
6. Telefonda `http://<PC_LAN_IP>:4173` adresini ac.
7. Login ol, chat + voice + upload akislarini test et.

Notlar:
- Mikrofon icin HTTPS veya localhost gerekebilir (tarayici politikasina bagli).
- Bazi mobil tarayicilarda MediaRecorder codec farki olabilir; uygulama uyumlu mime tipini otomatik secer.

## CORS Notu (Backend)

- Mobil preview origin ornegi: `http://192.168.1.104:4173`
- Backend tarafinda bu origin `allow_origins` veya `CORS_ALLOW_ORIGINS` icinde olmali.
- Bu repo guncellemesi backend kodunu degistirmez; yalnizca konfigurasyon notu ekler.

## PWA Kurulumu (Installable)

Projede sunlar hazir:
- `public/manifest.webmanifest`
- `public/sw.js` (offline shell)
- `src/main.tsx` icinde service worker register

PWA olarak yuklemek icin:
1. Uygulamayi tarayicida ac.
2. Tarayici menusunden "Install app / Add to Home Screen" sec.
3. Acilan kisayol ile standalone modda calistir.

## Mimari Ozeti

- `src/pages/AuthPage.tsx`: Login/Register
- `src/pages/MainAppPage.tsx`: Tek birlesik calisma ekrani
- `src/components/*`: Header, status banner, message list/item, composer, voice/upload controls
- `src/services/*`: auth/chat/voice/document/learning API katmani
- `src/store/*`: auth, message, voice, upload, app(system) state
- `src/types/*`: guclu TypeScript model/tip tanimlari

## Token / Auth Davranisi

- JWT token localStorage'da tutulur.
- `401` durumunda merkezi API katmani otomatik logout tetikler.
- Token suresi dolunca kullanici login ekranina duser.

## Conversation Persistence

- Konusma gecmisi tarayicida kullanici bazli key ile saklanir: `boranizm:messages:{user_id}`.
- Son yuklenen belge baglami (recent docs) kullanici bazli key ile saklanir: `boranizm:recent_docs:{user_id}`.
- Gecici session verisi (draft/system/voice durumu) kullanici bazli key ile saklanir: `boranizm:session:{user_id}`.
- Logout/401/token-expire durumunda aktif kullanicinin `recent_docs` ve `session` cache'i temizlenir.
- Mesaj history temizleme davranisi konfigurasyonludur; varsayilan olarak history korunur (`CLEAR_PERSISTED_MESSAGES_ON_LOGOUT_DEFAULT=false`).
- Bozuk veya parse edilemeyen cache verisi guvenli sekilde yok sayilir ve uygulama bos state ile devam eder.

## Onemli Endpoint Uyumlari

Frontend asagidaki backend endpointleriyle uyumludur:
- `/auth/login`, `/auth/register`, `/auth/me`
- `/chat`
- `/voice/chat`, `/voice/transcribe`, `/voice/speak`, `/voice/health`
- `/learning/ingest/document`
- learning graph/cluster/memory/summary/reflection endpointleri (service katmaninda hazir)



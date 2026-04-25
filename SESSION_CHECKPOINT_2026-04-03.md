# boran.ai Session Checkpoint (2026-04-03)

## Tamamlanan Durum

- Backend ayakta: `uvicorn app.main:app --host 127.0.0.1 --port 8000`
- Frontend ayakta: `http://127.0.0.1:5173`
- Tek sayfalı UI aktif (`Login` + `MainPage`)
- Birleşik akış çalışır halde:
  - text chat -> `/chat`
  - voice chat -> `/voice/chat`
  - document ingest -> `/learning/ingest/document`
- Mesaj akışında transcript + AI reply + audio player gösterimi var
- Durum göstergesi aktif: `idle / recording / processing / playing / uploading / error`
- Mobile-first Tailwind düzeni uygulandı

## Android Mobil App Durumu

- Capacitor kuruldu ve Android platform eklendi
- `frontend/android` native shell oluşturuldu
- `capacitor.config.ts` eklendi
- Android manifest güncellendi:
  - `RECORD_AUDIO` izni eklendi
  - `usesCleartextTraffic=true`
- API fallback Android için eklendi:
  - Native Android fallback: `http://10.0.2.2:8000`
- Android env örnek dosyası eklendi:
  - `frontend/.env.android.example`
- Scriptler eklendi:
  - `android:init`
  - `android:sync`
  - `android:open`
  - `android:run`
- `npm run android:sync` başarılı
- `npx cap doctor` sonucu: Android hazır

## Devam İçin Önerilen Sonraki Adım

1. Android Studio ile aç:
   - `cd frontend`
   - `npm run android:open`
2. Emulator/cihazda debug run al
3. Voice + login + upload E2E test

## Notlar

- Fiziksel cihaz için backend LAN'da açılmalı:
  - `uvicorn app.main:app --host 0.0.0.0 --port 8000`
- Fiziksel cihaz env:
  - `VITE_API_URL=http://<PC_LAN_IP>:8000`

---

## Devam Notu (2026-04-03 / aynı gün)

### Yapılanlar

- Backend health doğrulandı: `GET /health -> 200`
- Frontend yeniden ayağa kaldırıldı: `http://127.0.0.1:5173 -> 200`
- Frontend build doğrulandı: `cd frontend && npm run build` başarılı
- Capacitor doctor doğrulandı: `cd frontend && npx cap doctor` -> `Android looking great`
- Android sync tekrar doğrulandı: `cd frontend && npm run android:sync` başarılı
- Backend testleri doğrulandı:
  - `python -m pytest -q tests` -> `29 passed`
  - `python -m pytest -q` -> `29 passed`
- `pytest` kök koleksiyonunun daha stabil olması için `pyproject.toml` güncellendi:
  - `[tool.pytest.ini_options]`
  - `testpaths = ["tests"]`

### Açık Kalan Sonraki Adım

1. Android Studio'da native run:
   - `cd frontend`
   - `npm run android:open`
2. Emulator/cihazda E2E:
   - Login
   - Voice chat (`/voice/chat`)
   - Document upload (`/learning/ingest/document`)
3. Fiziksel cihaz senaryosunda LAN API testi:
   - backend: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
   - frontend env: `VITE_API_URL=http://<PC_LAN_IP>:8000`

---

## Voice TTS Fallback Güncellemesi (2026-04-03)

### Hedef

- Coqui opsiyonel kalsın
- Coqui yoksa otomatik edge-tts fallback
- Voice pipeline crash olmasın
- `/voice/health` içinde aktif provider net görünsün
- Runtime default provider `edge` olsun

### Yapılan Kod Değişikliği

- `app/config.py`:
  - `voice_tts_provider` default: `edge`
- `app/voice/tts.py`:
  - `TTSService` çoklu provider mantığına alındı (`preferred` + fallback)
  - `coqui` başarısız olursa otomatik `edge` deneniyor
  - Başarılı fallback durumunda warning metni dönülüyor
  - Health çıktısına:
    - `provider` (aktif)
    - `config.preferred_provider`
    - `config.active_provider`
    - `config.fallback_provider`
    - `config.providers` (coqui/edge alt health) eklendi
- `.env.example`:
  - `VOICE_TTS_PROVIDER=edge` varsayılan
  - `coqui` opsiyonel örnek olarak bırakıldı
- `README.md`:
  - voice bölümünde `edge` default + `coqui` opsiyonel/fallback notu güncellendi

### Test / Doğrulama

- Unit/API testleri:
  - `python -m pytest -q tests/test_voice_tts_fallback.py` -> `1 passed`
  - `python -m pytest -q tests/test_voice_api.py` -> `8 passed`
  - `python -m pytest -q` -> `30 passed`
- Runtime smoke test (`127.0.0.1:8000`):
  - `/voice/health` -> `tts.provider=edge`, `active=edge`, `preferred=edge`
  - `/voice/speak` -> `provider=edge` (mp3 üretildi)
  - `/voice/chat` -> `tts_provider=edge` (mp3 üretildi)
- Fallback smoke test (`VOICE_TTS_PROVIDER=coqui`, `127.0.0.1:8002`):
  - `/voice/health` -> `provider=edge`, `preferred=coqui`, `fallback=edge`
  - `/voice/speak` -> `provider=edge`
  - warning -> `tts fallback active: preferred=coqui, active=edge.`

---

## Frontend Mobile-first PWA MVP (2026-04-03)

### Hedef

- Login dışında tek ana ekran
- Chat + voice + document upload aynı akışta
- Mobile-first responsive + PWA installable yapı

### Yapılanlar

- Yeni sayfa akışı:
  - `AuthPage` (login/register)
  - `MainAppPage` (tek birleşik ekran)
- Zustand store katmanı ayrıldı:
  - `authStore`
  - `messageStore`
  - `voiceStore`
  - `uploadStore`
  - `appStore`
- Message model tipleri genişletildi:
  - `user_text`, `user_voice`, `assistant_text`, `assistant_voice`, `system`, `error`
- Birleşik composer:
  - text input
  - mic button
  - upload button
  - send button
- Voice akışı:
  - MediaRecorder start/stop
  - `/voice/chat` çağrısı
  - transcript + reply + audio player stream’e işleniyor
  - voice state: `idle/recording/processing/playing`
- Document akışı:
  - `/learning/ingest/document` upload + progress
  - sonuç system/error message olarak stream’e düşüyor
- Merkezi API katmanı:
  - `VITE_API_BASE_URL` (legacy `VITE_API_URL` fallback)
  - Authorization header yönetimi
  - `401` durumunda merkezi logout handler
- Auth:
  - token + user localStorage
  - expiry kontrolü + otomatik login ekranına dönüş
- PWA:
  - `manifest.webmanifest` + `sw.js` + service worker register aktif

### Doğrulama

- `cd frontend && npm run build` başarılı
- `cd frontend && npm run dev -- --host 127.0.0.1 --port 5173` -> `200`

### Mimari Plan (Uygulanan)

- `App` auth-gate olarak çalışır:
  - token/geçerli oturum varsa `MainAppPage`
  - yoksa `AuthPage`
- Login sonrası **tek ana ekran**:
  - chat + voice + document upload aynı message stream ve aynı composer içinde
- Merkezi API wrapper:
  - `VITE_API_BASE_URL` (fallback: `VITE_API_URL`)
  - `Authorization` header merkezi
  - `401` durumunda merkezi logout
- State katmanı (Zustand):
  - `authStore`, `messageStore`, `voiceStore`, `uploadStore`, `appStore`

### Component Tree (Uygulanan)

- `App`
- `AuthPage`
- `MainAppPage`
  - `TopBar`
  - `StatusIndicator`
  - `MessageList`
    - `MessageBubble`
      - `AudioPlayer`
  - `Composer`
    - `VoiceButton`
    - `UploadButton`

### Data Flow (Uygulanan)

1. Login/Register:
   - `authService` -> `authStore.setAuth` -> `App` -> `MainAppPage`
2. Text chat:
   - composer text -> `POST /chat` -> `user_text` + `assistant_text`
3. Voice chat:
   - MediaRecorder start/stop -> `POST /voice/chat`
   - `transcript + reply + audio_url` -> `user_voice` + `assistant_voice`
4. Document upload:
   - file select -> `POST /learning/ingest/document` (XHR progress)
   - başarı/hata -> `system`/`error` message
5. Token expire / 401:
   - API wrapper unauthorized handler -> `authStore.clearAuth()` -> login ekranı

### Frontend Dosya Envanteri (Yeni/Güncel)

- Sayfalar:
  - `frontend/src/pages/AuthPage.tsx`
  - `frontend/src/pages/MainAppPage.tsx`
  - `frontend/src/pages/LoginPage.tsx` (AuthPage alias)
  - `frontend/src/pages/MainPage.tsx` (MainAppPage alias)
  - `frontend/src/pages/ChatPage.tsx` (MainAppPage alias)
  - `frontend/src/pages/VoiceChatPage.tsx` (MainAppPage alias)
  - `frontend/src/pages/DocumentsPage.tsx` (MainAppPage alias)
  - `frontend/src/pages/LearningPage.tsx` (MainAppPage alias)
  - `frontend/src/pages/SettingsPage.tsx` (MainAppPage alias)
- Bileşenler:
  - `frontend/src/components/TopBar.tsx`
  - `frontend/src/components/StatusIndicator.tsx`
  - `frontend/src/components/MessageList.tsx`
  - `frontend/src/components/MessageBubble.tsx`
  - `frontend/src/components/AudioPlayer.tsx`
  - `frontend/src/components/Composer.tsx`
  - `frontend/src/components/VoiceButton.tsx`
  - `frontend/src/components/UploadButton.tsx`
- Store:
  - `frontend/src/store/authStore.ts`
  - `frontend/src/store/messageStore.ts`
  - `frontend/src/store/voiceStore.ts`
  - `frontend/src/store/uploadStore.ts`
  - `frontend/src/store/appStore.ts`
- Services:
  - `frontend/src/services/api.ts`
  - `frontend/src/services/authService.ts`
  - `frontend/src/services/chatService.ts`
  - `frontend/src/services/voiceService.ts`
  - `frontend/src/services/documentService.ts`
  - `frontend/src/services/learningService.ts`
- Hooks:
  - `frontend/src/hooks/useRecorder.ts`
- Types:
  - `frontend/src/types/auth.ts`
  - `frontend/src/types/message.ts`
  - `frontend/src/types/voice.ts`
  - `frontend/src/types/learning.ts`
  - `frontend/src/types/api.ts`
- Utils:
  - `frontend/src/utils/id.ts`
  - `frontend/src/utils/time.ts`
- Core:
  - `frontend/src/App.tsx`
  - `frontend/src/main.tsx`
  - `frontend/src/styles.css`
- PWA/Env/Docs:
  - `frontend/public/manifest.webmanifest`
  - `frontend/public/sw.js`
  - `frontend/.env.example`
  - `frontend/README.md`

### Message Model (Uygulanan)

- Tipler:
  - `user_text`
  - `user_voice`
  - `assistant_text`
  - `assistant_voice`
  - `system`
  - `error`
- Alanlar:
  - `id`, `type`, `content`, `transcript`, `audioUrl`, `fileName`, `createdAt`, `status`, `meta`

### Son Çalıştırma / Doğrulama Komutları

- Backend:
  - `GET /health` -> `200`
- Test:
  - `python -m pytest -q` -> `30 passed`
- Frontend:
  - `cd frontend && npm run build` -> başarılı
  - `cd frontend && npm run dev -- --host 127.0.0.1 --port 5173` -> `200`
- Voice smoke:
  - `/voice/health`, `/voice/speak`, `/voice/chat` -> `edge` ile başarılı

### Devam Ederken İlk Adım (Kaldığımız Yer)

1. Backend kontrol:
   - `http://127.0.0.1:8000/health`
2. Frontend başlat:
   - `cd frontend`
   - `npm run dev`
3. Login ol
4. Tek ekranda sırayla smoke:
   - text chat
   - mic ile `/voice/chat`
   - PDF ile `/learning/ingest/document`
5. Gerekirse learning endpointlerini UI’da ikinci fazda görünür hale getir:
   - graph/cluster/memory kartları (aynı MainApp ekranı içinde)

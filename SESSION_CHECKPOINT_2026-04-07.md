# Session Checkpoint - 2026-04-07

## Scope
Bu checkpoint, bugune kadar yapilan iki ana calismayi ozetler:
1. Upload size limit artisi (frontend + backend)
2. Frontend/PWA conversation persistence dogrulama

## 1) Upload Size Limit (50 MB)

### Tamamlananlar
- Backend upload limit ayari eklendi:
  - `app/config.py`
  - `upload_max_file_size_mb: int = 50`
- Backend upload kaydetme akisinda byte-level limit enforcement eklendi:
  - `app/api/routes.py` icinde `_save_upload`
  - 1 MB chunk read + toplam byte sayimi
  - limit asiminda `413 (HTTP_413_CONTENT_TOO_LARGE)`
  - hata mesaji: `Dosya boyutu {X} MB sinirini asiyor.`
  - yari yuklenen dosya otomatik temizleniyor
- Frontend 20 MB hardcode kaldirildi, merkezi config kullaniliyor:
  - `frontend/src/config/upload.ts`
  - `MAX_UPLOAD_SIZE_MB` (`VITE_MAX_UPLOAD_SIZE_MB`, default 50)
  - `MAX_UPLOAD_FILE_SIZE_BYTES`
- Frontend upload validation yeni confige baglandi:
  - `frontend/src/pages/MainAppPage.tsx`
- Kullaniciya oversize hata mesaji dinamik hale getirildi:
  - `frontend/src/utils/systemMessages.ts`
  - `oversizedFile(maxUploadSizeMb)`
- UI limit bilgisi guncellendi:
  - `frontend/src/components/Composer.tsx` -> `Maksimum dosya boyutu: {n} MB`
  - `frontend/src/components/UploadButton.tsx` -> tooltip max bilgi
- Env + dokumantasyon guncellendi:
  - `.env.example` -> `UPLOAD_MAX_FILE_SIZE_MB=50`
  - `frontend/.env.example` -> `VITE_MAX_UPLOAD_SIZE_MB=50`
  - `README.md` ve `frontend/README.md` upload limit notlari

### Testler
- Frontend build: `npm run build` -> BASARILI
- Backend test dosyasi eklendi:
  - `tests/test_upload_size_limit.py`
- Calisan testler:
  - kucuk dosya kabul
  - limit ustu dosya reddi (413)
  - 10 MB -> gecer
  - 30 MB -> gecer
  - 55 MB -> limit hatasi

## 2) Conversation Persistence (Frontend/PWA)

### Durum
Istenen persistence ozelliklerinin mevcut kodda zaten uygulandigi dogrulandi.

### Ana noktalar
- Kullanici bazli key yapisi var:
  - `boranizm:messages:{user_id}`
  - `boranizm:recent_docs:{user_id}`
  - `boranizm:session:{user_id}`
- Message type seti uyumlu:
  - `user_text`, `user_voice`, `assistant_text`, `assistant_voice`, `system`, `error`
- Mesaj alanlari korunuyor:
  - `id`, `type`, `content`, `transcript`, `audioUrl`, `fileName`, `createdAt`, `status`, `meta`
- Login sonrasi ilgili kullanicinin cachei yukleniyor
- Logout / 401 / token-expire cleanup var:
  - aktif kullanicinin `session` ve `recent_docs` temizleniyor
  - message history temizligi konfigurasyonlu
- Varsayilan davranis:
  - `CLEAR_PERSISTED_MESSAGES_ON_LOGOUT_DEFAULT=false`
  - yani logoutta message history default olarak korunuyor
- Bozuk cache parse hatalarinda app crash olmuyor, guvenli fallback var
- Throttled write var (`createThrottledStorageWriter`)
- Voice ve upload kaynakli system mesajlari message stream ile birlikte persist ediliyor

### Dogrulanan dosyalar
- `frontend/src/store/persistence.ts`
- `frontend/src/store/messageStore.ts`
- `frontend/src/store/uploadStore.ts`
- `frontend/src/pages/MainAppPage.tsx`
- `frontend/src/App.tsx`
- `frontend/src/types/message.ts`
- `frontend/README.md`

## Devam icin Notlar
- Reverse proxy (nginx vb.) kullaniliyorsa body size limiti ayrica 50 MB+ olacak sekilde kontrol edilmeli.
- Bir sonraki adimda istenirse persistence icin otomatik e2e test senaryolari eklenebilir.

# Session Checkpoint - 2026-04-08

## Scope
Bu checkpoint, 2026-04-07 checkpointinden sonra "conversation persistence icin otomatik test" adimini tamamlar.

## 1) Frontend Test Altyapisi

### Tamamlananlar
- `frontend/package.json` guncellendi:
  - script: `test` -> `vitest`
  - script: `test:run` -> `vitest run`
  - dev dependency: `vitest`
- `frontend/package-lock.json` guncellendi (`npm install` sonrasi)

## 2) Persistence ve Store Testleri

### Eklenen test dosyalari
- `frontend/src/store/persistence.test.ts`
- `frontend/src/store/messageStore.test.ts`
- `frontend/src/store/uploadStore.test.ts`
- `frontend/src/test/localStorageMock.ts`

### Kapsanan davranislar
- Storage key formatlari (`messages`, `recent_docs`, `session`)
- Malformed JSON durumunda guvenli fallback + key temizleme
- Throttled writer davranisi (`schedule`, `flush`, `cancel`)
- Session cache yaziminin iptal/temizleme davranisi
- `messageStore`:
  - aktif kullaniciya gore mesaj cache yukleme
  - kullanici degisiminde onceki kullanicinin cache flush edilmesi
  - logout cleanup benzeri memory-only temizleme
  - `clearPersisted: true` ile kalici mesaj cache silme
- `uploadStore`:
  - yarim kalan upload statuslerinin restore sirasinda `error`a normalize edilmesi
  - kullanici degisiminde onceki kullanici cache flush edilmesi
  - aktif kullanici cache temizliginde persisted `recent_docs` silinmesi

## 3) Dogrulama

### Test
- Komut: `cd frontend && npm run test:run`
- Sonuc: **3 test dosyasi, 13 test, hepsi basarili**

### Build
- Komut: `cd frontend && npm run build`
- Sonuc: **Basarili**

## 4) Component-Level Testler (MainAppPage/App)

### Eklenen test dosyalari
- `frontend/src/pages/MainAppPage.test.tsx`
- `frontend/src/App.test.tsx`

### Kapsanan senaryolar
- `MainAppPage`:
  - user-scoped session cache'ten draft + system state restore
  - auth kullanicisi degisince mesaj baglaminin dogru user cache'ine gecmesi
  - logoutta `session` + `recent_docs` temizlenirken persisted message history'nin korunmasi
- `App`:
  - 401/unauthorized callback tetiklenince cleanup + auth reset + system error state
  - token zaten expired ise mount sirasinda cleanup + auth reset + system error state

### Guncel test ozeti
- Komut: `cd frontend && npm run test:run`
- Sonuc: **5 test dosyasi, 18 test, hepsi basarili**

## Devam icin Notlar
- Istenirse bir sonraki adimda `MainAppPage` icin upload/chat interaction akisi da (servis mocklari ile) e2e-lite testlerine genisletilebilir.

## 5) Mobile PWA "Failed to fetch" Troubleshooting (2026-04-08)

### Yapilan degisiklikler
- `frontend/src/services/api.ts`
  - `VITE_API_BASE_URL` bos ise otomatik `http(s)://<current-host>:8000` kullanimina gecildi.
  - Env'de `localhost/127.0.0.1/0.0.0.0` verilip uygulama LAN hosttan acildiginda host otomatik browser hostuna normalize ediliyor.
- `frontend/.env.example`
  - Varsayilan API URL hardcode kaldirildi (`VITE_API_BASE_URL=`).
  - Mobil/LAN kullanim notu eklendi.
- `frontend/.env`
  - `VITE_API_BASE_URL=http://127.0.0.1:8000` -> `VITE_API_BASE_URL=`
- `.env.example`, `README.md`, `frontend/README.md`
  - Mobil/LAN notlari ve dogru konfig adimlari eklendi.

### Dogrulamalar
- `cd frontend && npm run build` basarili.
- Port kontrolu (`netstat`):
  - Frontend: `0.0.0.0:4173` ve `0.0.0.0:5173` dinliyor.
  - Backend: `127.0.0.1:8000` dinliyor (yalniz local).
- Health testi:
  - `http://127.0.0.1:8000/health` = 200
  - `http://10.155.87.17:8000/health` = baglanamiyor

### Tespit
- Sorun frontend configinden kalan `127.0.0.1` degil; ana blokaj backend'in LAN'a acik olmamasi.
- Telefon PWA'nin `Failed to fetch` almasi bu nedenle beklenen sonuc.

### Sonraki adim (kaldigimiz yer)
1. Backend'i `--host 0.0.0.0 --port 8000` ile calistir.
2. Telefondan `http://10.155.87.17:8000/health` test et.
3. Eski PWA cache'i icin telefonda app/site data temizleyip yeniden ac.
4. Gerekirse CORS/firewall daraltma kontrolu yap.

# boran.ai Mobile MVP (React Native + TypeScript)

Bu klasor, tek ekranli mobil MVP icin kaynak dosyalari icerir.

## 1) React Native app olusturma

```bash
npx react-native init boranMobile --template react-native-template-typescript
```

## 2) Paketler

`boranMobile` klasorunde:

```bash
npm install axios @react-native-async-storage/async-storage react-native-document-picker react-native-audio-record react-native-sound react-native-blob-util
```

Not:
- `react-native-sound` ve `react-native-audio-record` native moduldur. Android icin temiz build alin.
- Bu repodaki `mobile/App.tsx` ve `mobile/src/*` dosyalarini olusan app'e kopyalayin.

## 3) Android izinleri

`android/app/src/main/AndroidManifest.xml` icine:

```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.RECORD_AUDIO" />
```

## 4) API base URL (emulator + cihaz)

`src/utils/env.ts`:

- Android emulator: `http://10.0.2.2:8000`
- Fiziksel cihaz: `http://192.168.1.34:8000` (LAN IP)

`USE_ANDROID_EMULATOR` flag ile secilir.

## 5) Backend

Backend mutlaka `0.0.0.0:8000` uzerinde calismali:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 6) Android emulator calistirma

1. Android Studio > Device Manager > emulator baslat.
2. Uygulama klasorunde:

```bash
npx react-native run-android
```

## 7) Ekranlar

- `LoginScreen`
- `MainScreen` (tek ekran):
  - chat akisi
  - text input
  - mic butonu (baslat/durdur)
  - pdf yukleme
  - AI cevaplari
  - sesli cevap oynatma
  - loading durumlari

## 8) Servis dosyalari

- `src/services/authService.ts`
- `src/services/chatService.ts`
- `src/services/voiceService.ts`
- `src/services/documentService.ts`

## 9) Beklenen backend endpointleri

- `POST /auth/login`
- `POST /chat`
- `POST /voice/chat`
- `POST /learning/ingest/document`

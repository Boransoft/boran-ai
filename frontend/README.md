# boran.ai frontend (PWA-first)

Mobile-first React + Vite frontend for boran.ai backend.

## Features (MVP)

- Login / register
- Text chat (`/chat`)
- Voice chat with MediaRecorder (`/voice/chat`)
- Document upload (`/documents/upload`)
- Learning summary + reflection list
- Settings (reflection context + audio format)
- Installable PWA shell (manifest + service worker)

## Setup

1. Copy `.env.example` to `.env` and adjust API URL if needed.
2. Install dependencies:

```bash
npm install
```

3. Run dev server:

```bash
npm run dev
```

Default frontend URL: `http://127.0.0.1:5173`

## Environment

```env
VITE_API_URL=http://127.0.0.1:8000
```

## Mobile test

- Open Chrome DevTools
- Toggle device toolbar (mobile view)
- Test login, text chat, voice chat flow

## Voice capture

- Uses `navigator.mediaDevices.getUserMedia`
- Uses `MediaRecorder` (`audio/webm` preferred, `wav` fallback)
- Voice chat sends `multipart/form-data` to backend

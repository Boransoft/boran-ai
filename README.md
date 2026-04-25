# boranizm

Personal, continuously-learning AI assistant project.

Encoding note: Frontend source files should be saved as UTF-8 to avoid Turkish character corruption in UI text.

## Current Scope

- JWT auth (register/login/me) with bcrypt password hashing
- Unified ingestion for `pdf/doc/docx/txt/md/csv/json/jsonl/images`
- Metadata-aware ingestion (`category`, `tags`, `user_id`)
- PDF ingestion and semantic search (`ChromaDB`)
- OCR fallback for scanned PDFs (`pdf2image` + `pytesseract`)
- Chat API over local LLM endpoint (LM Studio compatible)
- Conversation memory in vector DB
- User correction learning pipeline
- Long-term memory store (persistent JSONL)
- Lightweight knowledge graph from conversations/corrections
- Typed relation extraction (`uses`, `requires`, `learns_from`, etc.)
- Automatic consolidation/summarization job for continuous learning
- PostgreSQL schema + ORM layer for production persistence

## API Endpoints

- `GET /health`
- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`
- `POST /chat`
- `GET /voice/health`
- `POST /voice/transcribe`
- `POST /voice/speak`
- `POST /voice/chat`
- `GET /voice/audio/{file_name}`
- `GET /voice/demo`
- `POST /documents/upload`
- `POST /ingest/file`
- `POST /ingest/pdf`
- `POST /ingest/folder`
- `POST /learning/ingest/document`
- `POST /learning/ingest/conversation`
- `POST /learning/reflect/{user_id}`
- `GET /learning/concepts/{user_id}`
- `GET /learning/graph/{user_id}`
- `GET /learning/graph/{user_id}/related?term=...`
- `GET /learning/graph/{user_id}/semantic?term=...`
- `GET /learning/clusters/{user_id}`
- `GET /learning/memory/top/{user_id}`
- `GET /learning/reflections/{user_id}`
- `GET /learning/summary/{user_id}`
- `POST /feedback/correction`
- `POST /jobs/consolidation/run`
- `GET /jobs/consolidation/state`
- `GET /db/health`
- `POST /db/init`
- `POST /db/sync/user/{user_id}`
- `GET /memory/long-term/{user_id}`
- `GET /knowledge/graph/{user_id}`

## Suggested Folder Architecture

```text
app/
  config.py
  main.py
  schemas.py
  auth/
    routes.py
    service.py
    schemas.py
    utils.py
  api/
    routes.py
  ingest/
    parsers.py
    service.py
  db/
    models.py
    session.py
    bootstrap.py
    sync.py
  rag/
    embeddings.py
    ingest.py
    search.py
    ocr_utils.py
    conversation_memory.py
  memory/
    long_term.py
  learning/
    concepts.py
    extractor.py
    graph.py
    pipeline.py
    corrections.py
    consolidation.py
    scheduler.py
  knowledge/
    graph.py
  voice/
    stt.py
    tts.py
    service.py
    routes.py
    schemas.py
  services/
    assistant.py
    memory.py
data/
  pdf/
  ingest/
  chroma/
  memory/
  graph/
sql/
  001_init_postgresql.sql
tests/
```

## PostgreSQL Setup

1. Copy `.env.example` to `.env`.
2. Start DB: `docker compose up -d postgres`
3. Start API: `uvicorn app.main:app --host 127.0.0.1 --port 8000`
4. Initialize schema: `POST /db/init`
5. Verify: `GET /db/health`
6. Optional backfill: `POST /db/sync/user/{user_id}`

## Embedding Setup

Embedding model is lazy-loaded on first use.

- Default model:
  - `sentence-transformers/all-MiniLM-L6-v2`
- Alternative model:
  - `BAAI/bge-small-en`

Environment variables:

```env
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_CACHE_PATH=data/models
EMBEDDING_ALLOW_DOWNLOAD=true
UPLOAD_MAX_FILE_SIZE_MB=100
SEMANTIC_LINK_THRESHOLD=0.82
GRAPH_CO_OCCURRENCE_WINDOW=4
CLUSTER_MIN_SIZE=2
MEMORY_DECAY_DAYS=30
MEMORY_IMPORTANCE_DEFAULT=1.0
```

Runtime behavior:

1. First tries local cache (`EMBEDDING_CACHE_PATH`).
2. If cache is missing and internet is available, downloads model and caches it.
3. If internet is unavailable, loads from local cache only.
4. If model still cannot load, system does not crash and uses hash-based fallback embeddings.

## Upload Size Limit

- Backend upload limit varsayilan olarak `100 MB` ve `.env` icindeki `UPLOAD_MAX_FILE_SIZE_MB` ile degistirilir.
- Frontend limiti `frontend/.env` icindeki `VITE_MAX_UPLOAD_SIZE_MB` degeri ile kontrol edilir (varsayilan `100`).
- Frontend ve backend limitleri ayni tutulmalidir.

## Retrieval Diversity Tuning

Document retrieval applies a per-source cap to improve context diversity when multiple files are indexed.

```env
RAG_PER_SOURCE_CAP_MIN=2
RAG_PER_SOURCE_CAP_MAX=4
```

Notes:

- Effective cap still scales with `top_k`; defaults keep existing behavior.
- If only one source is present in candidate results, cap is relaxed automatically.

## Voice Conversation Setup (MVP)

Install voice extras:

```bash
pip install -e .[voice]
```

Recommended providers:

- STT: `faster_whisper` (local-first, CPU-friendly)
- TTS default mode: `edge`
- TTS optional local mode: `coqui` (auto-fallback to `edge` if unavailable)

Environment variables:

```env
VOICE_STT_PROVIDER=faster_whisper
VOICE_TTS_PROVIDER=edge
# optional:
# VOICE_TTS_PROVIDER=coqui
WHISPER_MODEL_SIZE=base
WHISPER_DEFAULT_LANGUAGE=tr
WHISPER_BEAM_SIZE=1
WHISPER_BEST_OF=1
WHISPER_VAD_FILTER=false
WHISPER_COMPUTE_TYPE=int8
TTS_MODEL_NAME=tts_models/en/ljspeech/tacotron2-DDC
VOICE_OUTPUT_DIR=data/voice/output
AUDIO_UPLOAD_DIR=data/voice/uploads
EDGE_TTS_VOICE=auto
EDGE_TTS_VOICE_PROFILE=female
EDGE_TTS_VOICE_FEMALE=tr-TR-EmelNeural
EDGE_TTS_VOICE_MALE=tr-TR-AhmetNeural
EDGE_TTS_RATE=-5%
EDGE_TTS_PITCH=+0Hz
COQUI_SPEAKER=
COQUI_LANGUAGE=
VOICE_OUTPUT_FORMAT=mp3
VOICE_TTS_MAX_CHARS=700
VOICE_WARMUP_ENABLED=true
VOICE_INCLUDE_REFLECTION_DEFAULT=true
VOICE_FILE_TTL_HOURS=24
CORS_ALLOW_ORIGINS=*
CORS_ALLOW_METHODS=*
CORS_ALLOW_HEADERS=*
CORS_ALLOW_CREDENTIALS=true
```

Notes:

- `faster-whisper` and `coqui` download model artifacts on first run.
- `coqui` is optional; if it is selected but unavailable, TTS automatically falls back to `edge`.
- `edge-tts` is practical fallback/default, but it is not fully local.
- Voice files use UUID-based names and are user-isolated by hashed prefix.
- Old uploaded/generated files are auto-cleaned using `VOICE_FILE_TTL_HOURS`.
- Default edge voice is Turkish female (`tr-TR-EmelNeural`) via `EDGE_TTS_VOICE_PROFILE=female`.
- Startup warmup is enabled by default (`VOICE_WARMUP_ENABLED=true`) to reduce first-call latency.
- `VOICE_TTS_MAX_CHARS` limits spoken output length to avoid long TTS delays.

Turkish edge voice quick comparison:

- `tr-TR-EmelNeural` (female): most natural default for general conversation, smooth intonation.
- `tr-TR-AhmetNeural` (male): clearer and slightly slower sounding for instructional content.
- `en-US-AvaMultilingualNeural` (multilingual alt): can read Turkish but accent is less native than `tr-TR-*` voices.

## Auth Usage (curl)

Register:

```bash
curl -X POST http://127.0.0.1:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username":"boran",
    "email":"boran@example.com",
    "password":"StrongPass123",
    "display_name":"Boran"
  }'
```

Login:

```bash
curl -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "identifier":"boran@example.com",
    "password":"StrongPass123"
  }'
```

Use token on protected routes:

```bash
curl http://127.0.0.1:8000/auth/me \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "message":"Bugun ogrendiklerimi ozetle",
    "save_to_long_term":true
  }'
```

## Learning Pipeline (curl)

Document ingest + concept extraction:

```bash
curl -X POST http://127.0.0.1:8000/learning/ingest/document \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -F "file=@C:/path/to/doc_or_pdf_or_txt" \
  -F "category=research" \
  -F "tags=ai,knowledge"
```

Conversation learning ingest:

```bash
curl -X POST http://127.0.0.1:8000/learning/ingest/conversation \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "text":"Kullanici semantik arama kalitesini artirmak istiyor",
    "role":"user",
    "source":"manual_learning_ingest",
    "save_vector_memory":true
  }'
```

Get concepts:

```bash
curl "http://127.0.0.1:8000/learning/concepts/<USER_ID>" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

Get graph:

```bash
curl "http://127.0.0.1:8000/learning/graph/<USER_ID>" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

Related terms:

```bash
curl "http://127.0.0.1:8000/learning/graph/<USER_ID>/related?term=semantic" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

Semantic neighbors:

```bash
curl "http://127.0.0.1:8000/learning/graph/<USER_ID>/semantic?term=ihale" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

Concept clusters:

```bash
curl "http://127.0.0.1:8000/learning/clusters/<USER_ID>" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

Top scored memory for context:

```bash
curl "http://127.0.0.1:8000/learning/memory/top/<USER_ID>?query=ihale&limit=8" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

### Graph Relation + Semantic Linking

- Graph edges are no longer only rule-based; chunk-level co-occurrence edges are generated.
- Repeated co-occurrence in the same document/conversation increases edge `weight`.
- Duplicate edges are merged on normalized `(source, relation, target)`.
- Supported relation types:
  - `related_to`
  - `part_of`
  - `mentions`
  - `uses`
  - `requires`
  - `belongs_to`
  - `defined_as`
  - `semantically_related`
- Semantic linking uses embeddings and `SEMANTIC_LINK_THRESHOLD` to add strong `semantically_related` edges.

### Concept Clustering

- User-scoped clusters are built from:
  - graph connectivity
  - co-occurrence edges
  - semantic links
- Cluster labels are short and human-readable (for example `ihale ve yazisma`).
- Cluster records are persisted as long-term memory with `kind=concept_cluster`.

### Memory Scoring

- Memory retrieval is importance-aware rather than flat.
- Scoring signals include:
  - repetition count
  - correction overlap
  - graph strength
  - reflection overlap
  - cluster centrality overlap
  - explicit emphasis markers (`onemli`, `hatirla`, `kaydet`, etc.)
  - recency decay (`MEMORY_DECAY_DAYS`)
- `/chat` context now prioritizes:
  - top scored memory
  - concept clusters
  - semantic related concepts
  - strongest graph edges

## Voice API (Backend-first Contract)

Contract goals:

- frontend-agnostic (desktop/mobile/PWA/native client friendly)
- multipart upload compatible with browser/mobile recorder outputs
- stable response format for `voice/chat`: `transcript + reply + audio_url`
- auth and user isolation preserved

Upload fields:

- preferred: `audio`
- alternative: `file`

Supported input mime types (normalized):

- `audio/webm`, `video/webm`
- `audio/ogg`, `audio/opus`
- `audio/wav`, `audio/x-wav`, `audio/wave`
- `audio/mpeg`, `audio/mp3`
- `audio/mp4`, `audio/x-m4a`
- `audio/aac`
- `audio/3gpp`, `audio/3gpp2`
- `application/octet-stream` (only if filename extension is recognized)

`/voice/chat` standard response:

```json
{
  "status": "ok",
  "user_id": "user_xxx",
  "transcript": "kullanici sesi metni",
  "reply": "asistan metin yaniti",
  "audio_url": "/voice/audio/<file_name>"
}
```

Health:

```bash
curl "http://127.0.0.1:8000/voice/health" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

Transcribe audio:

```bash
curl -X POST "http://127.0.0.1:8000/voice/transcribe" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -F "audio=@C:/path/to/sample.wav" \
  -F "language=tr"
```

Voice chat (audio in, text+audio out):

```bash
curl -X POST "http://127.0.0.1:8000/voice/chat?debug_timing=true" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -F "audio=@C:/path/to/question.webm" \
  -F "language=tr" \
  -F "include_reflection_context=true" \
  -F "audio_format=mp3"
```

`debug_timing=true` returns stage timings inside `debug_timing`:
- `stt_s`
- `memory_retrieval_s`
- `graph_reasoning_context_s`
- `context_preparation_s`
- `lm_response_s`
- `tts_s`
- `total_s`
- `slowest_step`

Fetch generated audio:

```bash
curl "http://127.0.0.1:8000/voice/audio/<AUDIO_FILE_NAME>" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  --output reply.mp3
```

### CORS / Browser notes

- CORS is configurable via:
  - `CORS_ALLOW_ORIGINS`
  - `CORS_ALLOW_METHODS`
  - `CORS_ALLOW_HEADERS`
  - `CORS_ALLOW_CREDENTIALS`
- Default is permissive (`*`) for local development.
- For production, set explicit origins (for example your PWA domain).

### Desktop + Mobile usage notes

- Recommended output format for browser playback: `mp3`.
- Browser clients should fetch `audio_url` with bearer token and play via blob URL.
- Cleanup runs on voice requests and removes old files based on `VOICE_FILE_TTL_HOURS`.

### Minimal voice demo page

- URL: `GET /voice/demo`
- Single-page test UI with:
  - microphone permission request
  - start/stop recording
  - upload to `/voice/chat`
  - transcript + reply rendering
  - authenticated audio fetch + auto play
  - state labels: `idle / recording / processing / playing`
  - selected TTS settings preview after `/voice/chat` (`voice`, `rate`, `pitch`)

Token alma adimlari (demo icin):

1. `POST /auth/register` ile kullanici olustur (veya mevcut kullaniciyla devam et).
2. `POST /auth/login` ile `access_token` al.
3. `GET /voice/demo` sayfasinda token alanina bu `access_token` degerini yapistir.
4. Demo, `/voice/chat` cagrilarinda `Authorization: Bearer <access_token>` kullanir.

### Browser compatibility

- Desktop:
  - Chrome (recommended)
  - Edge (recommended)
  - Firefox (works, mime/container may vary)
  - Safari 17+ (MediaRecorder support varies by codec)
- Mobile:
  - Android Chrome/Edge: recommended
  - iOS Safari: supported on modern versions, but recording/playback behavior can vary

### Mobile limitations

- Microphone permission requires HTTPS or localhost.
- Autoplay can be blocked until user interaction; manual play may be required.
- Some browsers produce different recording containers (`webm`, `mp4`, `wav`), so upload normalization is necessary.
- Background tab/app transitions can interrupt recording.

### First test steps

1. Start backend (`uvicorn app.main:app --host 127.0.0.1 --port 8000`).
2. Create/login user and copy bearer token (`/auth/login`).
3. Open `http://127.0.0.1:8000/voice/demo`.
4. Paste token into demo page.
5. Record audio and send to `/voice/chat`.
6. Verify transcript, reply text, and audio playback.

## Reflection + Consolidation

Reflection engine combines:

- conversation memory
- semantic document memory
- correction memory
- knowledge graph edges

It creates user-scoped consolidated memory kinds in `memory_items.kind`:

- `recurring_topics`
- `user_preferences`
- `project_focus`
- `stable_rules`
- `concept_clusters`
- `recent_learning_summary`

Run reflection on demand:

```bash
curl -X POST "http://127.0.0.1:8000/learning/reflect/<USER_ID>" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

List stored reflection records:

```bash
curl "http://127.0.0.1:8000/learning/reflections/<USER_ID>?limit=20" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

Get latest reflection summary:

```bash
curl "http://127.0.0.1:8000/learning/summary/<USER_ID>" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

Optional chat-time reflection context:

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "message":"Bu haftaki onceliklerimi ozetle",
    "include_reflection_context":true
  }'
```

## Security Notes

- JWT secret must come from `.env` (`JWT_SECRET_KEY`).
- Access tokens expire via `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`.
- Protected routes are enforced by middleware.

## Missing Components (Next Iterations)

- Stronger semantic summarization (LLM-grade abstractive summary + citations)
- Full ETL for very large datasets (batching, incremental checkpoints)
- Access control and per-user data encryption
- End-to-end tests with fixture PDFs/DOCX/images

## Roadmap

1. Stabilize ingestion/retrieval with retry + observability.
2. Add memory consolidation and decay policy.
3. Upgrade knowledge graph extraction (NER + relation extraction).
4. Add autonomous learning loops (scheduled review of corrections).
5. Add plugin-style module interfaces for independent extensions.

## Frontend (PWA-first)

Frontend lives under `frontend/` and is built with React + Vite (mobile-first).

Run:

```bash
cd frontend
npm install
npm run dev
```

Mobile testing:

1. Open Chrome DevTools.
2. Enable device toolbar (mobile viewport).
3. Test login, chat, voice chat, and document upload pages.

LAN + PWA login testing:

1. Start backend with LAN host: `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
2. In `frontend/.env`, either:
   - leave `VITE_API_BASE_URL` empty (frontend auto-uses current host with `:8000`), or
   - set `VITE_API_BASE_URL=http://<PC_LAN_IP>:8000`.
3. Rebuild frontend when env changes: `cd frontend && npm run build`.
4. Start preview with host: `cd frontend && npm run preview -- --host`.
5. Open on phone: `http://<PC_LAN_IP>:4173`.
6. Ensure phone and PC are on same Wi-Fi network.

CORS note for LAN preview:

- Example frontend origin: `http://192.168.1.104:4173`
- If needed, add this origin in backend `allow_origins` / `CORS_ALLOW_ORIGINS`.

## Native Mobile MVP (React Native)

Native mobile MVP source lives under `mobile/`.

- Main setup command: `npx react-native init boranMobile --template react-native-template-typescript`
- Full package list and Android emulator steps: `mobile/README.md`

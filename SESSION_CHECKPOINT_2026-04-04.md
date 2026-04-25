# boran.ai Session Checkpoint (2026-04-04)

## Ozet
Bu oturumda backend + frontend + PWA + mobil login akisi canli olarak test edildi.
Ana problem login ekraninda `Please wait...` takilmasiydi.
Kok neden frontend degil, backend auth isteklerinin PostgreSQL kapali oldugu icin timeout olmasiydi.

## Calisan Durum (Su an)
- Frontend preview: `http://192.168.1.104:4173`
- Backend health: `http://192.168.1.104:8000/health` -> 200
- DB health: `http://192.168.1.104:8000/db/health` -> 200

## Bu Oturumda Yapilanlar

1. Servisleri ayaga kaldirma
- Backend ve frontend processleri kontrol edildi.
- Frontend `vite`/`preview` sandbox EPERM durumlari icin gerekli yerlerde yetkili calistirildi.

2. PWA production dogrulamasi
- `cd frontend && npm run build` basarili.
- `dist` altinda su dosyalar dogrulandi:
  - `manifest.webmanifest`
  - `sw.js`
  - `icons/`
  - `index.html`
  - `assets/`
- Preview URL'leri dogrulandi (local + network).
- Manifest referansi ve service worker register kontrol edildi.

3. Mobil `Failed to fetch` teshisi ve duzeltmesi
- API tabani `frontend/src/services/api.ts` icinde incelendi.
- `127.0.0.1` fallback problemi tespit edildi.
- API URL yapisi env-zorunlu olacak sekilde duzeltildi:
  - Artik sadece `VITE_API_BASE_URL` kullaniliyor.
  - Bos ise acik hata veriyor (yanlis fallback yok).
- `frontend/.env.example` mobil LAN kullanimina gore guncellendi.
- `frontend/README.md` ve kok `README.md` mobil/LAN/CORS notlariyla guncellendi.

4. Login ekrani gelmeme / `Please wait...` takilma teshisi
- Build icine gomulen `VITE_API_BASE_URL` kontrol edildi.
- `frontend/.env` eksik oldugu icin runtime hata oldugu goruldu ve olusturuldu:
  - `VITE_API_BASE_URL=http://192.168.1.104:8000`
- Frontend yeniden build edildi.

5. Asil login timeout problemi cozuldu
- `/auth/login` ve `/auth/register` timeout oldugu canli testle dogrulandi.
- `DATABASE_URL` kullanan auth akisi incelendi; DB baglantisi odakli kontrol yapildi.
- Docker Desktop kapali oldugu goruldu.
- Docker Desktop acildi.
- `docker compose up -d postgres` ile postgres ayağa kaldirildi.
- Sonrasinda auth endpointleri tekrar test edildi:
  - register -> 200 (~0.48s)
  - login -> 200 (~0.38s)

## Degisen Dosyalar (Bu Oturumda)
- `frontend/src/services/api.ts`
- `frontend/.env.example`
- `frontend/README.md`
- `README.md`
- `frontend/.env` (yeni olusturuldu, local calisma icin)

## Kritik Konfigurasyon
Frontend API URL (mobil icin):

```env
VITE_API_BASE_URL=http://192.168.1.104:8000
```

Backend LAN host ile calismali:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Postgres acik olmali:

```powershell
docker compose up -d postgres
```

Frontend preview:

```powershell
cd frontend
npm run build
npm run preview -- --host
```

## Mobil Test Akisi
1. Telefon ve PC ayni Wi-Fi aginda olsun.
2. Telefonda backend kontrol:
   - `http://192.168.1.104:8000/health`
3. Telefonda frontend ac:
   - `http://192.168.1.104:4173/?v=3`
4. Gerekirse cache temizleyip yeniden ac.

## Canli Test Hesabi (Gecici)
- Email: `probe24a99b@example.com`
- Password: `StrongPass123`

## Devam Icin Not
Sonraki adim: telefondan login + chat + voice + upload E2E akisini adim adim dogrulamak.

---

## Guncelleme 2 (2026-04-04 - Retrieval/Document Context)

### Hedef
Document ingest basarili olsa da chat/retrieval tarafinda belge geri cagiris kalitesini artirmak, file-name bagimliligini azaltmak, source bazli daha stabil context kullanmak.

### Kisa Root Cause
- Chunk id'leri dosya adina bagliydi (`{base_name}_{index}`), ayni dosya adinda cakisma riski vardi.
- Metadata modeli eksikti (`source_id`, `document_id`, `normalized_file_name`, `source_type`, `checksum` vb.).
- Retrieval pipeline file-name/ipucu tarafina asiri bagli kalabiliyordu.
- Buyuk ve cok parcali dokumanlarda ayni kaynaktan fazla benzer chunk gelerek cesitlilik azaliyordu.

### Yapilan Mimari Iyilestirmeler
1. Genel document source modeli eklendi:
- `source_id`, `document_id`, `user_id`
- `original_file_name`, `normalized_file_name`
- `mime_type`, `source_type`
- `upload_time/uploaded_at`, `chunk_count`, `status`, `checksum`

2. Ingest tarafi guclendirildi:
- Her dosya icin UUID tabanli benzersiz `source_id`/`document_id` uretiliyor.
- Chunk id formati: `source_id:chunk:000001` (file-name bagimsiz).
- Tum desteklenen tipler ayni metadata semasiyla yaziliyor.
- `document_sources.jsonl` ile source registry eklendi.

3. Retrieval tarafi gelistirildi:
- Asamalar: `explicit_scope -> last_recent_scope -> recent_scope -> user_scope`.
- `recent_documents`, `source_ids`, `file_names` hint olarak kullaniliyor.
- File-name eslesmesi yumusaklastirildi (normalize + fuzzy fallback).
- `fallback_used`, `matched_source_ids`, `matched_file_names` debug/response alanlari eklendi.

4. Rerank/cesitlilik iyilestirmesi (son ekleme):
- Ayni `source_id` icin `per_source_cap` uygulanir (top_k=12 icin tipik cap=4).
- Once cap ile secim, sonra bos slot kalirsa overflow havuzundan dengeli doldurma.
- Tek source varsa cap gevsetilir (tum slot tek kaynaktan gelebilir).
- Fallback mantigi korunur.

### Frontend Uyumu
- Chat payload: `context_scope`, `source_ids`, `file_names`, `recent_documents`.
- Upload sonucundan `source_id` ve `document_id` state'e yazilir.
- Response tarafinda `doc_context_hits/doc_sources/matched_source_ids` alanlari okunabilir durumda.

### Duzeltilen / Guncellenen Dosyalar
- `app/ingest/parsers.py`
- `app/ingest/service.py`
- `app/rag/document_sources.py` (yeni)
- `app/rag/search.py`
- `app/rag/ingest.py`
- `app/services/assistant.py`
- `app/api/routes.py`
- `app/schemas.py`
- `app/learning/pipeline.py`
- `frontend/src/services/chatService.ts`
- `frontend/src/pages/MainAppPage.tsx`

### Dogrulamalar
- `python -m py_compile ...` geciyor.
- `cd frontend && npm run build` geciyor.
- `pytest tests/test_ingest_parsers.py tests/test_auth_utils.py -q` -> 4 passed.
- Entegrasyon scriptlerinde:
  - Ayni isimli dosya tekrar ingest -> farkli `source_id` (cakisma yok).
  - PDF + text + image ingest -> metadata tutarli.
  - Spesifik dosya sorusu -> ilgili source oncelikleniyor.
  - Genel sorular -> `doc_context_hits > 0`.

### Devam Notu
Siradaki adim canli E2E testte (UI + backend) buyuk dokumanlarda cesitlilik davranisini izlemek ve gerekiyorsa `per_source_cap` degerini config'e tasimak.

---

## Guncelleme 3 (2026-04-07 - Retrieval Diversity Config)

### Yapilanlar
- `per_source_cap` hesabi hardcoded olmaktan cikarildi ve config tabanli hale getirildi.
- Yeni ayarlar:
  - `RAG_PER_SOURCE_CAP_MIN` (default: 2)
  - `RAG_PER_SOURCE_CAP_MAX` (default: 4)
- Retrieval davranisi ayni kaldi:
  - Tek kaynak varsa cap otomatik gevsetiliyor.
  - Cok kaynakli havuzda dinamik cap bu min/max araliginda hesaplanıyor.

### Degisen Dosyalar
- `app/config.py`
- `app/rag/search.py`
- `.env.example`
- `README.md`
- `tests/test_rag_diversity_cap.py` (yeni)

### Dogrulama
- `pytest tests/test_rag_diversity_cap.py tests/test_ingest_parsers.py tests/test_auth_utils.py -q` -> 7 passed

### Sonraki Adim
- Canli E2E'de buyuk dokumanlarda `selected_source_distribution` ve `doc_context_hits` izlenip gerekirse min/max degerlerinin tuning edilmesi.

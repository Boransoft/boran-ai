# Session Checkpoint - 2026-04-09 (DB Architecture)

## Scope
Bu checkpoint, boran-ai icin internal admin panel oncesi veritabani mimarisi ve veri modeli kararlarini toplar.
Odak: sade ama guclu bir PostgreSQL + pgvector tabanli tasarim.

## Baglam
- Sistem akislarinda chat, voice, document upload, ingest/learning, retrieval, memory/graph var.
- Admin panel multi-tenant SaaS olmayacak, internal operasyon paneli olacak.
- Hedef: sistemi izleme, belgeleri ve ingest durumunu takip etme, konusmalari ve hatalari gorme.

## 1) Kisa Mimari Plan

### PostgreSQL (relational)
- users, documents, ingest_jobs, conversations, messages, memory_nodes, memory_edges, system_logs.
- Tum operasyonel durumlar, iliskiler, timestampler, admin panelde listelenecek kayitlar burada.

### pgvector (PostgreSQL icinde)
- Ana: document_chunks.embedding
- Opsiyonel (faz-2): memory_nodes.embedding

### File storage
- Orijinal dosyalar, parse ara ciktilari, audio ciktilari DB disinda tutulur.
- DB tarafinda storage referansi (storage_key/url), checksum, boyut, mime gibi metadata tutulur.

## 2) Onerilen Tablolar
- users
- documents
- document_chunks
- ingest_jobs
- conversations
- messages
- memory_nodes
- memory_edges
- system_logs

## 3) Tablo Detaylari

### users
- Amac: login kullanicilari, internal admin yetki bilgisi.
- Temel kolonlar:
  - id
  - external_id (unique)
  - email (unique)
  - display_name
  - is_admin
  - status
  - last_login_at
  - created_at
  - updated_at
- Iliskiler:
  - users -> documents / conversations / messages / ingest_jobs / memory_nodes / memory_edges
- Onemli indexler:
  - unique(external_id)
  - unique(email)
  - index(is_admin, status)

### documents
- Amac: yuklenen belgenin ana metadata kaydi.
- Temel kolonlar:
  - id (document_id)
  - source_id
  - user_id
  - original_file_name
  - normalized_file_name
  - mime_type
  - source_type
  - storage_key
  - file_size
  - checksum
  - chunk_count
  - status
  - uploaded_at
  - ingested_at
  - meta (jsonb)
- Iliskiler:
  - documents -> document_chunks
  - documents -> ingest_jobs
- Onemli indexler:
  - index(user_id, uploaded_at desc)
  - index(user_id, status)
  - index(source_id)
  - index(checksum)
  - opsiyonel unique(user_id, checksum)

### document_chunks
- Amac: retrieval icin chunk + embedding.
- Temel kolonlar:
  - id
  - document_id
  - source_id
  - user_id
  - chunk_index
  - content
  - token_count
  - embedding vector(n)
  - embedding_model
  - status
  - created_at
  - meta (jsonb)
- Iliskiler:
  - document_chunks.document_id -> documents.id
- Onemli indexler:
  - unique(document_id, chunk_index)
  - index(user_id, document_id)
  - vector index (ivfflat/hnsw) on embedding
  - opsiyonel GIN(to_tsvector(content)) hybrid arama icin

### ingest_jobs
- Amac: ingest pipeline adimlarini izleme.
- Temel kolonlar:
  - id
  - document_id
  - user_id
  - status
  - stage
  - started_at
  - completed_at
  - error_message
  - processing_stats (jsonb)
  - retry_count
  - created_at
  - updated_at
- Iliskiler:
  - ingest_jobs.document_id -> documents.id
  - ingest_jobs.user_id -> users.id
- Onemli indexler:
  - index(status, created_at desc)
  - index(document_id, created_at desc)
  - index(user_id, created_at desc)
  - opsiyonel partial unique (tek aktif job)

### conversations
- Amac: chat/voice oturum basligi ve lifecycle.
- Temel kolonlar:
  - id (conversation_id)
  - user_id
  - title
  - channel (chat|voice|mobile)
  - status
  - last_message_at
  - created_at
  - updated_at
  - meta (jsonb)
- Iliskiler:
  - conversations -> messages
- Onemli indexler:
  - index(user_id, last_message_at desc)
  - index(created_at desc)

### messages
- Amac: konusma icerisindeki tum mesajlar.
- Temel kolonlar:
  - id
  - user_id
  - conversation_id
  - role
  - message_type
  - content
  - transcript
  - audio_url
  - meta (jsonb)
  - created_at
- Iliskiler:
  - messages.conversation_id -> conversations.id
  - messages.user_id -> users.id
- Onemli indexler:
  - index(conversation_id, created_at)
  - index(user_id, created_at desc)
  - opsiyonel GIN(meta)

### memory_nodes
- Amac: kullanici bazli bilgi dugumleri.
- Temel kolonlar:
  - id
  - user_id
  - node_type
  - canonical_text
  - normalized_key
  - source_type
  - source_document_id
  - source_message_id
  - confidence
  - embedding vector(n) (opsiyonel faz-2)
  - created_at
  - updated_at
  - last_seen_at
  - meta (jsonb)
- Iliskiler:
  - memory_nodes.user_id -> users.id
  - opsiyonel source_document_id -> documents.id
  - opsiyonel source_message_id -> messages.id
- Onemli indexler:
  - index(user_id, node_type, last_seen_at desc)
  - unique(user_id, normalized_key)
  - opsiyonel vector index

### memory_edges
- Amac: dugumler arasi graph iliskileri.
- Temel kolonlar:
  - id
  - user_id
  - from_node_id
  - to_node_id
  - edge_type
  - source_type
  - source_document_id
  - source_message_id
  - confidence
  - created_at
  - updated_at
  - last_seen_at
  - meta (jsonb)
- Iliskiler:
  - from_node_id/to_node_id -> memory_nodes.id
  - opsiyonel source FK baglari
- Onemli indexler:
  - index(user_id, from_node_id, edge_type)
  - index(user_id, to_node_id)
  - unique(user_id, from_node_id, to_node_id, edge_type)

### system_logs
- Amac: hata/olay izleme, admin timeline.
- Temel kolonlar:
  - id
  - level
  - message
  - component
  - related_user_id
  - related_document_id
  - related_job_id
  - related_message_id
  - context (jsonb)
  - timestamp
- Iliskiler:
  - nullable FK baglantilari (ilgili kayitlara)
- Onemli indexler:
  - index(timestamp desc)
  - index(level, timestamp desc)
  - index(component, timestamp desc)
  - index(related_job_id)
  - index(related_document_id)

## 4) Akis Haritasi
1. Kullanici login -> users.last_login_at update
2. Belge yukleme -> documents (status=uploaded/queued)
3. Ingest baslangic -> ingest_jobs (queued/running)
4. Chunk + embedding -> document_chunks yazimi, documents.chunk_count/status update
5. Chat retrieval -> document_chunks uzerinde user scope + vector search
6. Konusma kaydi -> conversations + messages
7. Memory update -> memory_nodes + memory_edges upsert
8. Operasyon izleme -> system_logs

## 5) User Scope ve Internal Admin
- Retrieval user scope ile calisir (where user_id = ?).
- Internal admin panel tum user verisini filtre kaldirarak gorebilir.
- SaaS tenant modeli gerekmedigi icin tenant_id zorunlu degil.

## 6) ER Mantigi (Ozet)
- users 1-N documents
- documents 1-N document_chunks
- documents 1-N ingest_jobs
- users 1-N conversations
- conversations 1-N messages
- users 1-N memory_nodes
- memory_nodes 1-N memory_edges (from/to)
- system_logs ilgili varliklara nullable baglanir

## 7) Fazlama

### Faz-1 (zorunlu)
- users
- documents
- document_chunks
- ingest_jobs
- conversations
- messages
- system_logs

### Faz-2 (ertelenebilir)
- memory_nodes
- memory_edges
- gelismis meta/context analitik alanlari
- hybrid search optimizasyonlari

## 8) Admin Panel MVP'nin Okuyacagi Tablolar
- users
- documents
- ingest_jobs
- conversations
- messages
- system_logs
- document_chunks (adet/debug ozeti icin)

## 9) Neden PostgreSQL + pgvector (sade kalma)
- Relational + vector tek yerde; operasyon ve backup daha basit.
- Internal panel icin hizli gelistirme, dusuk bakim yuk.
- Ileride olceklenirse ayrisma:
  - once log pipeline
  - sonra file processing/storage katmani
  - en son gerekirse vector katmanini ayri servise cikarma

## Net Onerilen Ilk Faz Tablo Listesi
- users
- documents
- document_chunks
- ingest_jobs
- conversations
- messages
- system_logs

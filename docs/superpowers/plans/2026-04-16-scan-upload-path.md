# Scan Upload Path Implementation Plan (Task 3 + Task 7)

**Goal:** Accept a CSV upload on `POST /scan/runs/upload`, parse into Transaction rows tagged with the new run's `run_id`, store the raw file in Supabase Storage, and run the detection pipeline scoped to those transactions only. Closes the bank analyst demo gap.

**Architecture:** New multipart endpoint keeps the existing JSON `POST /scan/runs` path untouched (still works for regulator director demos). Upload path: file → storage → CSV parse → Account resolve/create → Transaction insert with run_id → run_scan_pipeline(source_run_id=run_id). Pipeline gains an optional `source_run_id` kwarg that filters transactions by run_id instead of org scope.

**Tech Stack:** FastAPI UploadFile + multipart, httpx for Supabase Storage REST API, existing CSV parser, SQLAlchemy 2 async, existing pipeline.

---

## CSV format (v1)

Expected columns. Required: `posted_at`, `src_account`, `amount`. Optional: `dst_account`, `currency` (default BDT), `channel`, `tx_type`, `description`.

```
posted_at,src_account,dst_account,amount,currency,channel,tx_type,description
2026-04-01T10:30:00,1234567890,9876543210,50000,BDT,RTGS,debit,Transfer to partner
```

Accounts (src + dst) are resolved or created in the uploader's `org_id`. Cross-bank tracking is out of scope for v1 — dst is treated as an account at the uploader's bank.

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `engine/app/services/storage.py` | `upload_file(path, content, content_type)` — httpx to Supabase Storage REST |
| Create | `engine/app/services/csv_ingest.py` | `ingest_csv(session, *, run_id, user, content)` → parses CSV, resolves accounts, inserts transactions |
| Modify | `engine/app/services/scanning.py` | New `queue_run_with_upload` that writes file + ingests + runs pipeline with `source_run_id` |
| Modify | `engine/app/routers/scan.py` | New `POST /scan/runs/upload` multipart endpoint |
| Modify | `engine/app/core/pipeline.py` | `run_scan_pipeline` accepts `source_run_id`; when set, loads only those txns |
| Modify | `web/src/app/api/scan/runs/upload/route.ts` (create) | Proxy multipart pass-through |
| Modify | `web/src/components/scan/upload-drop.tsx` | Real `<input type="file">` + onChange handler |
| Modify | `web/src/components/scan/scan-workbench.tsx` | When file is selected: POST FormData to /api/scan/runs/upload |

---

### Task 1: Storage upload helper

`engine/app/services/storage.py`:
- `upload_to_uploads(*, path, content, content_type)` — PUT to `{SUPABASE_URL}/storage/v1/object/{bucket}/{path}` with service_role bearer.
- Returns the public URL (or signed URL — but for MVP just the storage path, which gets stored in `DetectionRun.file_url`).
- Uses `httpx.AsyncClient`. Fails loudly on non-2xx.

### Task 2: CSV ingest service

`engine/app/services/csv_ingest.py::ingest_csv`:
- Parses CSV content string via existing `parse_csv`
- For each row, resolves src_account and dst_account (by `org_id + account_number`, create if missing)
- Inserts Transaction rows with `run_id` set
- Returns tx_count and accounts_touched count
- Validates required columns; raises HTTPException(400) on malformed CSV

### Task 3: Scan upload orchestration

`engine/app/services/scanning.py`:
- New `queue_run_with_upload(session, *, user, file_name, content_bytes, selected_rules)`:
  1. Create DetectionRun with run_type='upload', status='processing'
  2. Upload raw bytes to Supabase Storage at `{org_id}/{run_id}/{file_name}`
  3. Set DetectionRun.file_url to the storage path
  4. Decode content_bytes → string → call ingest_csv(run_id=run.id)
  5. Call run_scan_pipeline(source_run_id=run.id, org_id=..., scope_org_ids=...)
  6. Returns ScanQueueResponse like the existing path

### Task 4: Pipeline run_id scope

`engine/app/core/pipeline.py::run_scan_pipeline`:
- New kwarg `source_run_id: uuid.UUID | None = None`
- If set, `_load_accounts_and_transactions` is replaced with a run-scoped query: transactions WHERE run_id = source_run_id, accounts JOINed by FK.
- If None, existing behavior unchanged (legacy, regulator demo path).

### Task 5: Scan upload route

`engine/app/routers/scan.py`:
```python
@router.post("/runs/upload", response_model=ScanQueueResponse)
async def upload_and_scan(
    file: Annotated[UploadFile, File(...)],
    selected_rules: Annotated[str, Form()] = "",
    user, session,
) -> ScanQueueResponse:
    content = await file.read()
    rules = [r for r in selected_rules.split(",") if r]
    return await queue_run_with_upload(session, user=user,
        file_name=file.filename, content_bytes=content, selected_rules=rules)
```

Role-gated to `manager+` (matches the existing /scan/runs).

### Task 6: Web UI + proxy

- Create `web/src/app/api/scan/runs/upload/route.ts` — pipes FormData through to engine.
- Update `upload-drop.tsx` to have a real `<input type="file" accept=".csv">` that captures the File.
- Update `scan-workbench.tsx`: if a File is selected, send FormData to /api/scan/runs/upload (not the JSON endpoint).

### Task 7: Deploy + verify

1. Run engine tests.
2. Push feature branch, merge after review.
3. Watch Render deploy.
4. Create a small test CSV, upload via the UI, verify:
   - DetectionRun row has file_url set
   - Transactions table has new rows with run_id = the run's id
   - Pipeline detected alerts only from those new transactions

---

## Scope boundaries

- CSV only. XLSX/PDF later.
- File size limited to what FastAPI/Vercel/Render allow by default (~1MB typical CSV). No chunking.
- No progress polling — sync execution as with the existing scan path.
- No XLSX/PDF parsers, no validation preview, no re-running a past upload.
- Storage writes are fire-and-forget — if storage is down but DB works, the ingestion still succeeds (file_url just stays null). This makes the critical path DB-only.

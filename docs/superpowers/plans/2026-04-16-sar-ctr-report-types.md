# SAR/CTR Report Types Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add report_type column to str_reports (STR/SAR/CTR), create a lightweight cash_transaction_reports table for bulk CTR imports, and update the full stack to filter/group by report type.

**Architecture:** Migration adds report_type to str_reports and creates cash_transaction_reports. Engine model/schema/service/route updates propagate the field. Web types/normalizers/UI gain filter pills and a report type selector on the draft form. CTR gets its own lightweight router for bulk import.

**Tech Stack:** Supabase Postgres migration, SQLAlchemy 2 async, FastAPI, Pydantic v2, Next.js 16 App Router, React 19.

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `supabase/migrations/003_report_types.sql` | Add report_type column, cash_transaction_reports table, update trigger |
| Modify | `engine/app/models/str_report.py` | Add report_type field |
| Create | `engine/app/models/ctr.py` | CashTransactionReport model |
| Modify | `engine/app/schemas/str_report.py` | Add report_type to upsert/summary/detail |
| Create | `engine/app/schemas/ctr.py` | CTR import/list schemas |
| Modify | `engine/app/services/str_reports.py` | Accept report_type in create/list |
| Create | `engine/app/services/ctr.py` | bulk_import_ctrs, list_ctrs |
| Modify | `engine/app/routers/str_reports.py` | Add report_type query param to GET |
| Create | `engine/app/routers/ctr.py` | GET /ctr, POST /ctr/import |
| Modify | `engine/app/main.py` | Mount ctr router |
| Modify | `web/src/types/domain.ts` | Add reportType to STR types, add CTR types |
| Modify | `web/src/types/api.ts` | Add reportType to STR payloads, add CTR types |
| Modify | `web/src/lib/str-reports.ts` | Normalize reportType |
| Modify | `web/src/app/api/str-reports/route.ts` | Pass report_type query param |
| Create | `web/src/app/api/ctr/route.ts` | CTR list + import proxy |
| Modify | `web/src/components/strs/str-report-list.tsx` | Filter pills + type selector on form |

---

### Task 1: Database migration

**Files:**
- Create: `supabase/migrations/003_report_types.sql`

Migration DDL:

```sql
-- Add report_type to str_reports
ALTER TABLE str_reports ADD COLUMN report_type text NOT NULL DEFAULT 'str'
  CHECK (report_type IN ('str','sar','ctr'));

-- Update trigger to use report_type as prefix
CREATE OR REPLACE FUNCTION gen_str_ref() RETURNS trigger AS $$
BEGIN
  IF NEW.report_ref IS NULL OR NEW.report_ref = '' THEN
    NEW.report_ref := upper(coalesce(NEW.report_type, 'str')) || '-'
      || to_char(now(), 'YYMM') || '-'
      || lpad(nextval('str_ref_seq')::text, 6, '0');
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Cash Transaction Reports table (lightweight, bulk-oriented)
CREATE TABLE cash_transaction_reports (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES organizations(id),
  account_number text NOT NULL,
  account_name text,
  transaction_date date NOT NULL,
  amount numeric(18,2) NOT NULL,
  currency text NOT NULL DEFAULT 'BDT',
  transaction_type text CHECK (transaction_type IN ('deposit','withdrawal','transfer')),
  branch_code text,
  reported_at timestamptz NOT NULL DEFAULT now(),
  created_at timestamptz NOT NULL DEFAULT now(),
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX idx_ctr_org ON cash_transaction_reports(org_id);
CREATE INDEX idx_ctr_account ON cash_transaction_reports(account_number);
CREATE INDEX idx_ctr_date ON cash_transaction_reports(transaction_date DESC);

ALTER TABLE cash_transaction_reports ENABLE ROW LEVEL SECURITY;
CREATE POLICY ctr_org ON cash_transaction_reports FOR ALL
  USING (org_id = auth_org_id() OR is_regulator());
```

Apply via Supabase MCP execute_sql against project bmlyqlkzeuoglyvfythg.

---

### Task 2: Engine model updates

**Files:**
- Modify: `engine/app/models/str_report.py` — add report_type field
- Create: `engine/app/models/ctr.py` — CashTransactionReport model

Add to STRReport model after `report_ref`:
```python
report_type: Mapped[str] = mapped_column(String(16), default="str")
```

New CashTransactionReport model:
```python
class CashTransactionReport(TimestampMixin, Base):
    __tablename__ = "cash_transaction_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"))
    account_number: Mapped[str] = mapped_column(String(128))
    account_name: Mapped[str | None] = mapped_column(String(255))
    transaction_date: Mapped[date] = mapped_column(Date())
    amount: Mapped[float] = mapped_column(Numeric(18, 2))
    currency: Mapped[str] = mapped_column(String(16), default="BDT")
    transaction_type: Mapped[str | None] = mapped_column(String(32))
    branch_code: Mapped[str | None] = mapped_column(String(32))
    reported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
```

---

### Task 3: Engine schema updates

**Files:**
- Modify: `engine/app/schemas/str_report.py` — add report_type everywhere
- Create: `engine/app/schemas/ctr.py` — CTR schemas

Add `report_type: str = "str"` to:
- `STRDraftUpsert`
- `STRReportSummary`
- `STRReportDetail`

New CTR schemas:
```python
class CTRImportItem(BaseModel):
    account_number: str
    account_name: str | None = None
    transaction_date: str  # ISO date
    amount: float
    currency: str = "BDT"
    transaction_type: str | None = None  # deposit | withdrawal | transfer
    branch_code: str | None = None

class CTRBulkImportRequest(BaseModel):
    records: list[CTRImportItem]

class CTRSummary(BaseModel):
    id: str
    org_id: str
    account_number: str
    account_name: str | None
    transaction_date: str
    amount: float
    currency: str
    transaction_type: str | None
    branch_code: str | None
    reported_at: str | None
    created_at: str

class CTRListResponse(BaseModel):
    records: list[CTRSummary]
    total: int

class CTRBulkImportResponse(BaseModel):
    imported: int
    message: str
```

---

### Task 4: Engine STR service updates

**Files:**
- Modify: `engine/app/services/str_reports.py`

Changes:
1. `list_str_reports`: add optional `report_type: str | None` param, filter query when set
2. `create_str_report`: read `report_type` from payload (default "str"), assign to model
3. `_serialize_report` and `serialize_report_detail`: include `report_type` in output dict

---

### Task 5: Engine CTR service + router

**Files:**
- Create: `engine/app/services/ctr.py`
- Create: `engine/app/routers/ctr.py`
- Modify: `engine/app/main.py` — mount ctr router

Service functions:
- `list_ctrs(session, *, user, limit=100, offset=0)` — query cash_transaction_reports for user's org (or all if regulator)
- `bulk_import_ctrs(session, *, user, records, ip)` — insert batch of CTR rows, return count

Router:
- `GET /ctr` — list CTRs with pagination
- `POST /ctr/import` — bulk import, requires analyst+ role

---

### Task 6: Engine route update for str_reports

**Files:**
- Modify: `engine/app/routers/str_reports.py`

Add `report_type: str | None = None` query param to the GET endpoint, pass to `list_str_reports`.

---

### Task 7: Web types + normalizers

**Files:**
- Modify: `web/src/types/domain.ts` — add reportType to STRReportSummary, add CTR types
- Modify: `web/src/types/api.ts` — add reportType to payloads, add CTR API types
- Modify: `web/src/lib/str-reports.ts` — normalize reportType field

---

### Task 8: Web proxy routes

**Files:**
- Modify: `web/src/app/api/str-reports/route.ts` — forward report_type query param
- Create: `web/src/app/api/ctr/route.ts` — GET list + POST import proxy

---

### Task 9: Web UI — STR list filter + type selector

**Files:**
- Modify: `web/src/components/strs/str-report-list.tsx`

Changes:
1. Add report type filter pills (All / STR / SAR / CTR) above the list
2. Add report type selector dropdown in the draft creation form
3. Show report type badge on list items
4. Pass ?reportType= to the fetch call when a filter is active

---

### Task 10: Build + test verification

Run:
- `cd engine && pytest -q`
- `cd web && npm run build && npm run lint`

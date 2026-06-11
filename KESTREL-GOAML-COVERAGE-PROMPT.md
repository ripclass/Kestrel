# Kestrel — goAML Coverage Patch

You are working on the Kestrel codebase. Kestrel is positioned to replace goAML for BFIU. BFIU analysts have worked with goAML for years — every goAML workflow has a mental slot in their head. Kestrel must answer every one of those workflows, but it does NOT replicate goAML screen-for-screen. Where Kestrel's modern approach is better, we keep ours and document why. Where goAML has workflow coverage Kestrel lacks, we add it.

This is not a UI overhaul. Kestrel's architecture, sidebar, and AI-native flows stay. This patch closes coverage gaps and adds familiar vocabulary so BFIU procurement cannot point at goAML and say "you're missing X."

Read the current state before writing code:
- `supabase/migrations/` — you'll add migration 005
- `engine/app/models/str_report.py` — extend for new report types
- `engine/app/routers/` — existing routers to extend or add alongside
- `engine/app/services/str_reports.py`, `case_mgmt.py`, `investigation.py`
- `web/src/app/(platform)/` — pages to extend, not replace
- `web/src/components/shell/nav-config.ts` — where familiar vocabulary lives
- `docs/` — where the "deliberately excluded" explainer will live

Work on `main`. No live users yet.

---

## Task 1: Complete report type coverage

goAML's Reports menu has: STR, SAR, CTR, Suspected TBML, Complaint Report, FIU Escalated Report, Information Exchange Request (IER), Internal Report, Adverse Media-SAR, Adverse Media-STR, Additional Information File.

Kestrel currently has STR, SAR, CTR. Add the rest as first-class variants, not separate pipelines — one report model handles all types with type-specific fields.

### Schema: `supabase/migrations/005_report_types_expanded.sql`

```sql
-- Expand the report_type enum
ALTER TABLE str_reports DROP CONSTRAINT IF EXISTS str_reports_report_type_check;
ALTER TABLE str_reports ADD CONSTRAINT str_reports_report_type_check
  CHECK (report_type IN (
    'str', 'sar', 'ctr',
    'tbml',              -- Suspected Trade-Based Money Laundering
    'complaint',         -- Complaint Report (individuals/entities reporting to BFIU)
    'ier',               -- Information Exchange Request (Egmont Group cooperation)
    'internal',          -- Internal Report (BFIU-originated intelligence)
    'adverse_media_str', -- Adverse Media prompting STR workflow
    'adverse_media_sar', -- Adverse Media prompting SAR workflow
    'escalated',         -- FIU Escalated Report
    'additional_info'    -- Additional Information File (supplements existing report)
  ));

-- additional_info tracks which report it supplements
ALTER TABLE str_reports ADD COLUMN supplements_report_id uuid REFERENCES str_reports(id);

-- Adverse media provenance
ALTER TABLE str_reports ADD COLUMN media_source text;
ALTER TABLE str_reports ADD COLUMN media_url text;
ALTER TABLE str_reports ADD COLUMN media_published_at date;

-- IER fields
ALTER TABLE str_reports ADD COLUMN ier_direction text
  CHECK (ier_direction IS NULL OR ier_direction IN ('inbound','outbound'));
ALTER TABLE str_reports ADD COLUMN ier_counterparty_fiu text;   -- e.g. "FINTRAC (Canada)"
ALTER TABLE str_reports ADD COLUMN ier_counterparty_country text;
ALTER TABLE str_reports ADD COLUMN ier_egmont_ref text;
ALTER TABLE str_reports ADD COLUMN ier_request_narrative text;
ALTER TABLE str_reports ADD COLUMN ier_response_narrative text;
ALTER TABLE str_reports ADD COLUMN ier_deadline date;

-- TBML-specific fields
ALTER TABLE str_reports ADD COLUMN tbml_invoice_value numeric(18,2);
ALTER TABLE str_reports ADD COLUMN tbml_declared_value numeric(18,2);
ALTER TABLE str_reports ADD COLUMN tbml_lc_reference text;
ALTER TABLE str_reports ADD COLUMN tbml_hs_code text;
ALTER TABLE str_reports ADD COLUMN tbml_commodity text;
ALTER TABLE str_reports ADD COLUMN tbml_counterparty_country text;

-- Reference sequence per report type (so STR-2604-000001, SAR-2604-000001, IER-2604-000001)
-- The existing trigger already uses upper(report_type) as prefix — verify it handles new types.

CREATE INDEX idx_str_report_type ON str_reports(report_type);
CREATE INDEX idx_str_supplements ON str_reports(supplements_report_id) WHERE supplements_report_id IS NOT NULL;
```

### Model: `engine/app/models/str_report.py`

Add the new columns matching migration 005. Keep one model — type-specific fields are nullable.

### Schemas: `engine/app/schemas/str_report.py`

- Extend `STRDraftUpsert` with all new optional fields (media_source, ier_direction, tbml_*, etc.).
- `STRReportSummary` and `STRReportDetail` add `report_type`, `supplements_report_id`, IER/media/TBML fields.
- Validation: if `report_type == 'ier'`, require `ier_direction` and `ier_counterparty_fiu`. If `report_type == 'additional_info'`, require `supplements_report_id`. If `report_type == 'tbml'`, `tbml_counterparty_country` required. If `report_type` starts with `'adverse_media_'`, require `media_source`.

### Service: `engine/app/services/str_reports.py`

- `create_str_report` and `update_str_report` accept the new fields.
- `list_str_reports` already supports `status_filter`; add `report_type_filter` parameter.
- For `report_type == 'additional_info'`, link the supplemented report's entities into the new report so intelligence carries over.
- For `report_type == 'ier'`, skip subject account/phone/wallet requirements — IER is about counterparty FIU exchange, not an account.

### Router: `engine/app/routers/str_reports.py`

Add `report_type` query parameter to `GET /` for filtering.

### UI: `web/src/app/(platform)/strs/page.tsx`

- Add report type filter pills (already partially present per commit history) covering all 11 types.
- Add "New Report" flow with type picker step — after selecting type, render type-specific form fields.

### UI: `web/src/components/str-reports/str-report-workspace.tsx`

- Type-aware sections: IER shows counterparty FIU + direction + Egmont ref; TBML shows LC reference, HS code, invoice vs declared values; Adverse Media shows source URL and published date; Additional Info shows a "Supplements" link to the parent report.

---

## Task 2: XML report upload (goAML format intake)

Banks currently submit STR/SAR/CTR to BFIU via goAML's XML upload. Their internal systems already produce this XML. Kestrel must accept the same format so banks don't rewrite pipelines. This is the #1 procurement unlock.

### Parser: `engine/app/parsers/goaml_xml.py`

Parse the goAML XML schema. The core element is `<report>` with child `<rentity_id>`, `<submission_code>` (STR/SAR/CTR), `<report_code>` (type variant), `<reporting_person>`, `<location>`, then `<transaction>` or `<activity>` elements with nested subjects (`<t_from>`, `<t_to>`, `<from_account>`, `<to_account>`, `<from_person>`, `<to_person>`, `<from_entity>`, `<to_entity>`).

Map to Kestrel's model:
- `submission_code` → `report_type`
- Primary subject (first `<t_from>` party or first `<activity>` party) → `subject_name`, `subject_account`, `subject_phone`, `subject_wallet`, `subject_nid`
- Transactions → insert into `transactions` table with `run_id` set to the import batch ID
- All accounts/persons/entities → run through entity resolver

Use `lxml` for parsing (add to `pyproject.toml`). Validate against goAML XSD if schema file is available; otherwise parse permissively with logged warnings.

### Schema: `engine/app/schemas/xml_import.py`

```python
class XMLImportRequest(BaseModel):
    # File uploaded via multipart/form-data
    pass

class XMLImportResponse(BaseModel):
    report_id: str
    report_type: str
    report_ref: str
    transactions_ingested: int
    subjects_resolved: int
    warnings: list[str]
```

### Router: `engine/app/routers/str_reports.py`

Add:
```
POST /api/v1/str-reports/import-xml
```

Accepts multipart file upload. Parses via `goaml_xml.py`, creates STR record, ingests transactions, runs entity resolver + cross-bank matcher.

### UI: Add "Import XML" button on the STRs list page. File picker → upload → success state showing the created report with a link.

---

## Task 3: Information Exchange Request (IER) workflow

goAML's IER is how FIUs cooperate with foreign FIUs via the Egmont Group. This is a real regulatory obligation — BFIU cannot fully abandon goAML without it. Once report_type='ier' is supported (Task 1), add the workflow.

### Service: `engine/app/services/ier.py`

New service module:
- `create_outbound_ier(counterparty_fiu, counterparty_country, request_narrative, deadline, linked_entity_ids)` — BFIU requesting info from foreign FIU
- `create_inbound_ier(counterparty_fiu, counterparty_country, request_narrative, deadline, egmont_ref)` — foreign FIU requesting info from BFIU
- `respond_to_ier(ier_id, response_narrative, linked_str_ids)` — capture response
- `list_iers(direction, status, counterparty)` — filterable list

### Router: `engine/app/routers/ier.py`

```
GET    /api/v1/iers                            # list
POST   /api/v1/iers                            # create (outbound or inbound)
GET    /api/v1/iers/{id}                       # detail
PATCH  /api/v1/iers/{id}                       # update narrative, linked entities
POST   /api/v1/iers/{id}/respond               # capture response
POST   /api/v1/iers/{id}/close                 # mark complete
```

Mount in `main.py` under `/api/v1/iers`.

### UI: `web/src/app/(platform)/iers/`

- `page.tsx` — list view with Inbound / Outbound tabs
- `[id]/page.tsx` — detail showing request, counterparty, linked entities, response status, deadline, Egmont reference
- `new/page.tsx` — create form

Sidebar: add "Exchange" nav item (under Operations group) — the label is clearer than "IER" for non-experts but we include "Information Exchange Request" as a subtitle/tooltip so goAML users recognize it.

---

## Task 4: Additional Information File mechanism

goAML allows banks to supplement an existing report with additional information. Task 1 adds `supplements_report_id`. This task wires the workflow.

### Service: `engine/app/services/str_reports.py`

- `create_supplementary_report(parent_report_id, payload)` — creates STR with `report_type='additional_info'`, `supplements_report_id=parent_report_id`. Auto-inherits subject fields from parent if not provided.
- `list_supplements(parent_report_id)` — return all supplements for a parent.

### UI: On any STR detail page, add "Supplement this report" button. On the supplement, show a breadcrumb to the parent report. On the parent, show a "Supplements" section listing all supplementary reports with their refs and dates.

---

## Task 5: New Subjects explicit entry points

goAML's "New Subjects" menu has New Account / New Person / New Entity as distinct forms. Kestrel has unified entity creation. Add explicit entry points that pre-fill the entity type and land on focused forms. Same underlying endpoint; clearer UX and familiar vocabulary.

### UI: `web/src/app/(platform)/intelligence/entities/new/page.tsx`

Single page with three tabs: Account / Person / Entity. Each tab:
- Account tab: account number (required), account name, bank, account type, NID, phone
- Person tab: full name (required), NID, phone, DOB, address, known aliases
- Entity tab: business name (required), registration number, address, UBO info, industry

On submit, route through existing entity creation endpoint with `entity_type` set. Resolver handles linking (person ↔ account = same_owner, etc.).

### Sidebar: Add "New Subject" shortcut in the topbar (already present in design — verify it uses these three tabs).

---

## Task 6: Catalogue Search — labeled entry points

goAML has 12 separate lookup forms. Kestrel has omnisearch — more powerful, less familiar. Keep omnisearch. Add a "Catalogue" sub-nav under Investigate with labeled entry points that land on omnisearch pre-filtered.

### UI: `web/src/app/(platform)/investigate/catalogue/page.tsx`

Tile grid with 12 tiles — clicking each opens the existing omnisearch with a preset filter:

| Tile label (goAML vocabulary) | Preset filter |
|---|---|
| Account Lookup | entity_type=account |
| Person Lookup | entity_type=person |
| Entity Lookup | entity_type=business |
| Address Lookup | searches `metadata->>'address'` |
| Text Lookup | full-text across narrative, notes, descriptions |
| Quick Finder | no filter (same as default omnisearch) |
| Transaction Lookup | searches transactions table |
| Report Lookup | searches str_reports by ref |
| Intelligence Report Lookup | searches internal/escalated reports |
| Templates Lookup | searches saved templates |
| Journal Lookup | searches audit_log |
| Dissemination Lookup | searches disseminations (see Task 7) |

Each tile has a tooltip explaining it's powered by Kestrel's unified search.

### Sidebar nav-config: Add "Catalogue" as a sub-item under Investigate.

---

## Task 7: Dissemination tracking (replaces goAML "Disseminated Transaction Lookup")

BFIU disseminates intelligence to law enforcement (Police, ACC, NBR, etc.). This is an audit-critical workflow. goAML tracks which transactions/reports were disseminated where.

### Schema: `supabase/migrations/005_report_types_expanded.sql` (append):

```sql
CREATE TABLE disseminations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES organizations(id),
  dissemination_ref text NOT NULL,
  recipient_agency text NOT NULL,        -- "Bangladesh Police", "ACC", "NBR", "DGFI", foreign FIU name
  recipient_type text NOT NULL CHECK (recipient_type IN ('law_enforcement','regulator','foreign_fiu','prosecutor','other')),
  subject_summary text NOT NULL,
  linked_report_ids uuid[] NOT NULL DEFAULT '{}',
  linked_entity_ids uuid[] NOT NULL DEFAULT '{}',
  linked_case_ids uuid[] NOT NULL DEFAULT '{}',
  disseminated_by uuid REFERENCES auth.users(id),
  disseminated_at timestamptz NOT NULL DEFAULT now(),
  classification text DEFAULT 'confidential',
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_dissem_org ON disseminations(org_id);
CREATE INDEX idx_dissem_recipient ON disseminations(recipient_agency);
CREATE INDEX idx_dissem_date ON disseminations(disseminated_at DESC);
ALTER TABLE disseminations ENABLE ROW LEVEL SECURITY;
CREATE POLICY dissem_org ON disseminations FOR ALL USING (org_id = auth_org_id() OR is_regulator());

CREATE SEQUENCE IF NOT EXISTS dissem_ref_seq START 1;
CREATE OR REPLACE FUNCTION gen_dissem_ref() RETURNS TRIGGER AS $$
BEGIN
  IF NEW.dissemination_ref IS NULL OR NEW.dissemination_ref = '' THEN
    NEW.dissemination_ref := 'DISS-' || to_char(now(),'YYMM') || '-' || lpad(nextval('dissem_ref_seq')::text, 5, '0');
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER dissem_ref_trigger BEFORE INSERT ON disseminations FOR EACH ROW EXECUTE FUNCTION gen_dissem_ref();
```

### Model, schema, router, service, UI: Full CRUD for disseminations. Router at `/api/v1/disseminations`. UI page at `/platform/intelligence/disseminations`.

Key UI detail: on any Case, Alert, Entity, or STR detail page, add a "Disseminate" action button → opens modal → pick recipient agency, classification, subject summary → creates dissemination record and logs audit trail.

---

## Task 8: Business Processes — Case variants and proposals

goAML distinguishes: Cases, Case Proposals (pre-opened cases awaiting decision), Requests For Info (internal requests between analysts), Operations, Projects, FIU Escalated Case, Case (Complaints), Case (Adverse Media).

Kestrel has Cases. Close the gap via category field + proposal state.

### Schema: `supabase/migrations/005_report_types_expanded.sql` (append):

```sql
-- Case categories (goAML's case variants become a category field)
ALTER TABLE cases ADD COLUMN category text DEFAULT 'standard'
  CHECK (category IN (
    'standard',         -- general case
    'proposal',         -- pre-opened case awaiting manager decision
    'rfi',              -- Request For Information (between analysts)
    'operation',        -- larger multi-case operation
    'project',          -- long-running thematic project
    'escalated',        -- FIU Escalated Case
    'complaint',        -- Complaint Case
    'adverse_media'     -- Adverse Media Case
  ));

ALTER TABLE cases ADD COLUMN parent_case_id uuid REFERENCES cases(id);
ALTER TABLE cases ADD COLUMN requested_by uuid REFERENCES auth.users(id);  -- for RFI
ALTER TABLE cases ADD COLUMN requested_from uuid REFERENCES auth.users(id); -- for RFI
ALTER TABLE cases ADD COLUMN proposal_decision text CHECK (proposal_decision IN ('approved','rejected','pending'));
ALTER TABLE cases ADD COLUMN proposal_decided_by uuid REFERENCES auth.users(id);
ALTER TABLE cases ADD COLUMN proposal_decided_at timestamptz;

CREATE INDEX idx_cases_category ON cases(category);
CREATE INDEX idx_cases_parent ON cases(parent_case_id) WHERE parent_case_id IS NOT NULL;
```

### Service: `engine/app/services/case_mgmt.py`

Add:
- `propose_case(payload)` — creates case with `category='proposal'`, `status='open'`, `proposal_decision='pending'`
- `decide_proposal(case_id, decision, note)` — manager approves/rejects; on approval sets `category='standard'`
- `create_rfi(requested_from_user_id, subject, linked_entities, linked_reports)` — creates case with `category='rfi'`
- `list_cases(category, status, assigned_to)` — extended filtering

### Router: add endpoints for `/cases/propose`, `/cases/{id}/decide`, `/cases/rfi`.

### UI: `web/src/app/(platform)/cases/page.tsx`

Add category filter pills: All / Standard / Proposals / RFI / Operations / Projects / Escalated / Complaints / Adverse Media.

Proposals view: kanban columns pending / approved / rejected.
RFI view: inbox style with "requested from me" vs "requested by me" tabs.

---

## Task 9: Intel — Profiles (Saved Queries), Manual Graph, Match Definitions

goAML Intel menu: Profiles (Queries), Create Diagram, Matching (Match Definitions/Executions), Message Board.

### 9a. Saved Queries ("Profiles")

Analysts save common search patterns for reuse.

Schema (append to migration 005):
```sql
CREATE TABLE saved_queries (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES organizations(id),
  user_id uuid NOT NULL REFERENCES auth.users(id),
  name text NOT NULL,
  description text,
  query_type text NOT NULL,          -- 'entity_search' | 'transaction_search' | 'str_filter' | 'alert_filter'
  query_definition jsonb NOT NULL,   -- filters, search terms, sort order
  is_shared boolean DEFAULT false,   -- visible to whole org
  last_run_at timestamptz,
  run_count integer DEFAULT 0,
  created_at timestamptz DEFAULT now()
);
ALTER TABLE saved_queries ENABLE ROW LEVEL SECURITY;
CREATE POLICY sq_own ON saved_queries FOR ALL
  USING (user_id = auth.uid() OR (is_shared = true AND org_id = auth_org_id()) OR is_regulator());
```

UI: "Save this search" button on investigate/catalogue/alerts/cases filter bars. "My Saved Searches" panel in topbar.

### 9b. Create Diagram (manual network graph)

Kestrel already auto-renders graphs on entities. Add a manual diagram builder where an analyst picks entities + adds annotations for case narrative.

UI: `web/src/app/(platform)/investigate/diagram/page.tsx`
- Canvas: React Flow, draggable nodes from an entity picker panel
- Annotations: text labels on nodes/edges, colored highlights, exported as PNG/PDF
- Save diagram → attaches to a case or report as evidence

Schema:
```sql
CREATE TABLE diagrams (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES organizations(id),
  created_by uuid REFERENCES auth.users(id),
  title text NOT NULL,
  description text,
  graph_definition jsonb NOT NULL,  -- nodes, edges, annotations, positions
  linked_case_id uuid REFERENCES cases(id),
  linked_str_id uuid REFERENCES str_reports(id),
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
ALTER TABLE diagrams ENABLE ROW LEVEL SECURITY;
CREATE POLICY diagrams_org ON diagrams FOR ALL USING (org_id = auth_org_id() OR is_regulator());
```

### 9c. Match Definitions

Admin-configurable matching rules beyond the 8 system rules. Allows BFIU to define bespoke matches (e.g., "flag any transaction >৳50L to a newly-opened account in a border district").

Schema:
```sql
CREATE TABLE match_definitions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id uuid NOT NULL REFERENCES organizations(id),
  name text NOT NULL,
  description text,
  definition jsonb NOT NULL,  -- {conditions, scoring, severity_thresholds}
  is_active boolean DEFAULT true,
  created_by uuid REFERENCES auth.users(id),
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  last_execution_at timestamptz,
  total_hits integer DEFAULT 0
);

CREATE TABLE match_executions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  definition_id uuid NOT NULL REFERENCES match_definitions(id) ON DELETE CASCADE,
  executed_at timestamptz DEFAULT now(),
  executed_by uuid REFERENCES auth.users(id),
  hit_count integer DEFAULT 0,
  execution_status text DEFAULT 'completed',
  results_summary jsonb DEFAULT '{}'::jsonb
);
ALTER TABLE match_definitions ENABLE ROW LEVEL SECURITY;
ALTER TABLE match_executions ENABLE ROW LEVEL SECURITY;
CREATE POLICY match_def_org ON match_definitions FOR ALL USING (org_id = auth_org_id() OR is_regulator());
CREATE POLICY match_exec_org ON match_executions FOR ALL USING (
  EXISTS (SELECT 1 FROM match_definitions md WHERE md.id = definition_id AND (md.org_id = auth_org_id() OR is_regulator()))
);
```

UI: `web/src/app/(platform)/admin/match-definitions/page.tsx` — list, create (JSON editor with schema validation), run now, view execution history.

### 9d. Message Board — EXCLUDED

See Task 12 for the justification document.

---

## Task 10: Admin — Reference Tables, Statistics, Scheduled Processes

goAML's Management menu is vast. Most items are configuration of goAML itself as a customizable product. Kestrel is purpose-built for BFIU, so most are unnecessary. Keep the ones with real operational value.

### 10a. Reference Tables (Lookup Master)

Centralized reference data: bank codes, branch codes, country codes, currency codes, channel codes, category codes.

Schema:
```sql
CREATE TABLE reference_tables (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  table_name text NOT NULL,         -- 'banks' | 'branches' | 'countries' | 'channels' | 'categories'
  code text NOT NULL,
  value text NOT NULL,
  description text,
  parent_code text,                 -- branches reference banks
  metadata jsonb DEFAULT '{}'::jsonb,
  is_active boolean DEFAULT true,
  created_at timestamptz DEFAULT now(),
  UNIQUE(table_name, code)
);
ALTER TABLE reference_tables ENABLE ROW LEVEL SECURITY;
CREATE POLICY ref_read ON reference_tables FOR SELECT USING (auth.uid() IS NOT NULL);
CREATE POLICY ref_write ON reference_tables FOR INSERT WITH CHECK (is_regulator());
CREATE POLICY ref_update ON reference_tables FOR UPDATE USING (is_regulator()) WITH CHECK (is_regulator());
```

Seed with Bangladesh bank list (61 scheduled banks), major branch codes, channel codes (NPSB/RTGS/BEFTN/MFS/Cash/Cards/LC), ISO country codes, ISO currency codes.

UI: `web/src/app/(platform)/admin/reference-tables/page.tsx` — CRUD per table_name tab.

### 10b. Statistics menu

goAML's Statistics menu generates operational stats. Kestrel already has national dashboard + compliance scorecard. Add a consolidated "Operational Statistics" page that matches goAML's naming.

UI: `web/src/app/(platform)/reports/statistics/page.tsx`

Dashboards for:
- Reports received per type per month
- Reports by reporting organization
- CTR volume and aggregate value
- Disseminations by recipient agency
- Case outcomes (confirmed vs false positive rates)
- IER inbound/outbound by counterparty FIU
- Average time-to-review per report type

All stats already queryable via existing services — this page aggregates and renders them with Recharts.

### 10c. Scheduled Processes UI

Celery is already running. Add a read-only admin page listing scheduled jobs (nightly scan run, daily digest, weekly report) with last run time, next run, last status.

UI: `web/src/app/(platform)/admin/schedules/page.tsx`

### 10d. Things to NOT build

Skip: ESW Configurations, PAE Tab Configuration, Report Topic Measure Mapping, Group User Mapping, Agency Group Mapping, Group Based Data Filtering, XML Rejection Rules, Custom Numbering, Transaction Role Orientation, Report Indicator/Category Mapping, Data Correction tool. These are goAML-internal config mechanisms that exist because goAML is a customizable off-the-shelf product for many FIUs. Kestrel is purpose-built for BFIU; these config surfaces are replaced by code-level defaults + the Reference Tables above.

---

## Task 11: File menu operations

goAML's File menu: Clear Criteria, Retrieve, Print, PDF Export, Excel Export, Pivot Table, Graph, XML Export, XML Import, Change Password, Save/Load/Reset Grid Layout, Translate MDI, Exit.

Kestrel coverage:

| goAML item | Kestrel equivalent |
|---|---|
| Retrieve / Clear Criteria | Filter bars reset button + real-time results (no "retrieve" button needed — queries run on filter change) |
| Print | Browser print CSS (add `@media print` stylesheet across major pages) |
| PDF Export | Already implemented (case pack). Add "Export to PDF" to STR detail, Entity dossier, Alert detail |
| Excel Export | Add `/export/xlsx` endpoints for reports, alerts, entities, transactions, disseminations. Use `openpyxl` |
| XML Export | Add `/str-reports/{id}/export-xml` returning goAML-format XML (pairs with Task 2 import) |
| XML Import | Task 2 |
| Pivot Table | EXCLUDED — see Task 12 |
| Graph | Already exists per-entity. Add "View as Graph" toggle on search results |
| Change Password | Supabase Auth flow already handles this |
| Grid Layout save/load | EXCLUDED — see Task 12 |
| Translate MDI | EXCLUDED — see Task 12 (i18n is handled differently) |

### Implementation

- `engine/app/services/xlsx_export.py` — new, renders filtered tables to XLSX bytes
- `engine/app/services/goaml_xml_export.py` — renders an STR to goAML XML format (inverse of Task 2 parser)
- `engine/app/routers/` — add `GET /str-reports/{id}/export.xlsx`, `.xml`, and matching for alerts, entities, disseminations
- Web: add "Export" dropdown button component on list/detail pages → PDF / Excel / XML

---

## Task 12: "What we deliberately excluded" document

Create `docs/goaml-coverage.md`. This is the document BFIU procurement will read to understand Kestrel's coverage decisions.

Structure:

```markdown
# Kestrel vs goAML — Coverage and Design Decisions

## Summary

Kestrel provides complete functional coverage of goAML for BFIU's regulatory and operational workflows while modernizing the interface and adding AI-native intelligence capabilities goAML cannot provide. This document lists every goAML feature area, Kestrel's approach, and the rationale for any deviation.

## Coverage matrix

| goAML capability | Kestrel approach | Rationale |
|---|---|---|
| STR / SAR / CTR intake | First-class with AI enrichment | Same data model, extra AI enrichment on submit |
| TBML / Complaint / Internal / Adverse Media / Escalated / IER / Additional Information reports | First-class report types | Full parity |
| XML report upload (goAML format) | Supported via `/str-reports/import-xml` | Banks continue using existing pipelines unchanged |
| XML report export | Supported — Kestrel emits goAML-format XML | Interoperability with other FIUs and audit systems |
| 12 Catalogue Search forms | Unified omnisearch with 12 labeled entry points | One search handles every type; labels preserve familiarity. Powered by pg_trgm fuzzy matching which no individual goAML lookup form supports |
| New Account / Person / Entity manual entry | Unified "New Subject" flow with three tabs | Same endpoints underneath; focused forms per type |
| Case management | Full parity plus AI summaries | Cases, Proposals, RFI, Operations, Projects, Escalated, Complaints, Adverse Media |
| Matching (Match Definitions/Executions) | Full parity plus 8 system detection rules | BFIU can define custom rules; 8 are pre-built |
| Saved Queries (Profiles) | Supported | Per-user and org-shared |
| Create Diagram | Manual diagram builder + automatic graph on every entity | Kestrel auto-generates what goAML requires manual drawing of |
| Dissemination tracking | First-class `disseminations` table | Equal or better audit trail |
| Reference Tables / Lookup Master | `reference_tables` with bank, branch, country, currency, channel, category codes | Equal coverage |
| Statistics | Purpose-built dashboards + operational statistics page | Better than goAML's generic reports |
| User / Role / Workflow Maintenance | Supabase Auth + persona system + Celery | Modern auth stack |
| Localization | English + Bangla (selective, growing) | Phase-rolled |
| Audit log | `audit_log` table, X-Request-ID tracing | Better than goAML's Journal Lookup |

## Deliberate exclusions

The following goAML features are NOT implemented in Kestrel. Each has a specific rationale.

### Message Board (Intel menu)
**Excluded.** Built-in internal messaging is a 2006 enterprise pattern that underperforms dedicated communication tools. Kestrel provides contextual @-mentions and comments directly on cases, alerts, entities, and STRs — where the conversation needs to happen. Email notifications and webhook integrations connect to BFIU's existing channels. The stale Message Board pattern is replaced by conversations anchored to the work they're about, which is safer and auditable.

### Pivot Table (File menu)
**Excluded.** Kestrel's reporting views (national dashboard, compliance scorecard, trend analysis, operational statistics) are purpose-built for financial intelligence workflows. For ad-hoc pivoting, analysts export filtered datasets to Excel at any point and use Excel's own pivoting — which is more powerful than goAML's embedded pivot table. The goAML Pivot Table was a generic BI tool bundled into AML software; we replace it with AML-tuned analytics plus the export path to best-in-class tools.

### Schema XML View (System Admin)
**Excluded.** Kestrel is introspectable via an OpenAPI specification available at `/docs`. This is a standards-based API explorer that also enables automation, integration, and testing — capabilities the static XML schema view cannot provide.

### Grid Layout Save / Load / Reset (File menu)
**Excluded.** Kestrel uses modern web UI patterns (responsive layouts, persistent user preferences via Supabase). Per-page grid layout serialization is an artifact of desktop software that doesn't apply to the web.

### ESW Configurations, PAE Tab Configuration, Report Topic Measure Mapping, XML Rejection Rules, Custom Numbering, Transaction Role Orientation, Group User Mapping, Agency Group Mapping, Group Based Data Filtering (Management menu)
**Excluded.** These are goAML-internal configuration mechanisms that exist because goAML is a customizable off-the-shelf product serving many FIUs with different regulatory frameworks. Kestrel is purpose-built for Bangladesh's regulatory framework (Money Laundering Prevention Act 2012, ATA 2009, related BFIU circulars) with BFIU-specific rules and workflows baked in. What goAML exposes as 20+ configuration surfaces, Kestrel delivers as code-level correctness plus the focused admin surfaces listed above (Reference Tables, Match Definitions, Scheduled Processes, User/Role management).

### Translate MDI (File menu)
**Excluded.** Localization is handled through per-user language preferences (English / Bangla) at the application level rather than per-window translation. This is the modern i18n pattern.

## Capabilities unique to Kestrel (not in goAML)

1. **AI-powered entity extraction** from STR narratives — automatic subject resolution
2. **AI-drafted STR narratives** — analysts describe facts, Kestrel drafts the narrative
3. **AI alert explanations** — every alert explains why it fired in natural language
4. **Automatic cross-bank entity resolution** — no manual match definition required
5. **Network graphs on every entity** — automatic, not manually drawn
6. **8 pre-built detection rules** with continuous scoring — rapid cashout, fan-in/fan-out burst, dormant spike, layering, proximity to flagged, structuring, first-time high value
7. **Compliance scorecard** — ranks banks against each other on submission behaviors
8. **Modern web interface** — accessible from any browser, no desktop install, no VPN-only access
9. **Production observability** — structured logs, request tracing, incident runbook, uptime monitoring
10. **BDT-native, Bangla-ready** — built for Bangladesh specifically
```

Commit this as `docs/goaml-coverage.md`. Update `README.md` with a link.

---

## Task 13: Vocabulary alignment in the UI

Small but high-leverage. In the existing Kestrel sidebar and top-level page headers, add goAML-familiar terminology as secondary labels, tooltips, or aliases. This is a 1-day pass, not a redesign.

Edit `web/src/components/shell/nav-config.ts` to attach optional `aka` field (goAML equivalent terminology), then render as tooltip on hover.

Examples:
- Sidebar "Investigate" — tooltip "Analysis / Catalogue Search (goAML)"
- Sidebar "Intelligence" — tooltip "Intel (goAML)"
- Sidebar "Scan" — tooltip "Detection / Matching Executions (goAML)"
- Sidebar "Reports" — tooltip "Reports / Statistics (goAML)"
- Sidebar "Cases" — tooltip "Business Processes (goAML)"

Also on the Overview page for bfiu_analyst persona, add a one-line welcome: "Looking for goAML workflows? Everything is here — see the Coverage guide."

---

## Build order

The dependency chain:
1. Task 1 (report types) — foundational, others reference
2. Task 7 (disseminations schema) — referenced by Task 8
3. Task 8 (case variants)
4. Task 9 (Intel features)
5. Task 10 (Reference Tables + Stats)
6. Task 2 (XML import) — can run in parallel after Task 1
7. Task 3 (IER workflow) — depends on Task 1
8. Task 4 (Additional Info) — depends on Task 1
9. Task 5 (New Subjects forms) — UI-only, runs anytime
10. Task 6 (Catalogue tiles) — UI-only, runs anytime
11. Task 11 (File menu exports) — runs anytime
12. Task 12 (coverage doc) — write at end, reflects what shipped
13. Task 13 (vocabulary labels) — UI polish, runs last

Merge to main after each task. Live verify each task on production before moving to the next.

---

## Rules

- No Docker. Deploys via Vercel + Render as already wired.
- All new endpoints go through existing auth + RLS patterns.
- Every new table gets RLS policies (org-scoped + regulator-sees-all where appropriate).
- Every new user-facing action logs to `audit_log`.
- Keep the AI provider abstraction. Any new AI use goes through `engine/app/ai/service.py`.
- Commit style matches existing repo: `feat(engine): ...`, `feat(web): ...`, `feat(schema): ...`, `fix(...): ...`.
- Update `CLAUDE.md` "What to work on next" section after each task.
- Update `docs/RUNBOOK.md` if new failure modes are introduced.

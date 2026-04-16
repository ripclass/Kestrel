# PDF Case Pack Export Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the placeholder `engine/app/services/pdf_export.py` with a real WeasyPrint-rendered PDF case pack. Add `POST /cases/{case_id}/export` that streams the PDF back. Wire the existing "Generate PDF" button in the case workspace to the new flow.

**Architecture:** Engine renders an HTML template via Jinja2 → WeasyPrint converts to PDF → FastAPI streams as `application/pdf`. Web-side adds a proxy route and click handler; browser triggers the download via an `<a>` with a blob URL. Graceful fallback if WeasyPrint can't import (Render native deps) — return a 503 with a clear error so we know to add system packages.

**Tech Stack:** WeasyPrint 66+, Jinja2 (already a transitive dep via FastAPI), FastAPI StreamingResponse, existing engine auth.

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `engine/app/templates/case_pack.html` | Jinja2 template — case header, entities, alerts, STRs, timeline, watermark |
| Create | `engine/app/templates/case_pack.css` | Print CSS — A4 layout, BFIU branding, watermark |
| Modify | `engine/app/services/pdf_export.py` | Replace placeholder: `render_case_pdf(session, case_id, user)` returns PDF bytes |
| Create | `engine/app/services/case_export.py` | `assemble_case_pack(session, case_id, user)` — gathers case + alerts + STRs into a dict for the template |
| Modify | `engine/app/routers/cases.py` | Add `GET /cases/{case_id}/export.pdf` — streams the PDF |
| Create | `web/src/app/api/cases/[id]/export/route.ts` | Proxy that streams bytes through |
| Modify | `web/src/components/cases/case-export.tsx` | Wire onClick → fetch → download the PDF blob |
| Modify | `engine/render.yaml` | Add Cairo/Pango system packages if WeasyPrint import fails on Render |

---

### Task 1: Create HTML template + CSS

Template renders: header (case ref, title, status, severity, exposure), summary, entities table, alerts table, STRs table, timeline bullets, footer + watermark.

### Task 2: Case pack assembly service

`assemble_case_pack(session, *, case_id, user)` pulls:
- The CaseWorkspace (already exists via `get_case_workspace`)
- The linked alerts (query by `case_id == case.id` + `id IN linked_alert_ids`)
- The linked STRs (query by `matched_entity_ids` overlap with case.linked_entity_ids, OR by case linkage if metadata tracks it)

Returns a dict matching the template variables.

### Task 3: PDF rendering service

Replace `pdf_export.py` with:
- `render_case_pdf(session, *, case_id, user) -> bytes`
- Try/except the WeasyPrint import at module load — if it fails, `render_case_pdf` raises `HTTPException(503, "PDF generation unavailable — system deps missing")`. This lets the rest of the app start.
- Uses Jinja2 `Environment` with `FileSystemLoader` pointing at `engine/app/templates/`.
- Calls `WeasyPrint HTML(string=rendered).write_pdf(stylesheets=[CSS(filename=...)])`.

### Task 4: Case export route

Add to `engine/app/routers/cases.py`:
```python
@router.get("/{case_id}/export.pdf")
async def export_case_pdf(case_id: str, user, session) -> StreamingResponse:
    pdf_bytes = await render_case_pdf(session, case_id=case_id, user=user)
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="case-{case_id}.pdf"'},
    )
```

Role-gated to `analyst+`. GET not POST because browsers can download GET responses as files; POST requires JS handling.

### Task 5: Web proxy route

`web/src/app/api/cases/[id]/export/route.ts`:
- GET handler proxies to engine `/cases/{id}/export.pdf`
- Streams the binary body through unchanged
- Sets `Content-Disposition` and `Content-Type` from engine response

### Task 6: Wire the button

`case-export.tsx`: add `onClick` that fetches `/api/cases/{id}/export`, reads as blob, creates object URL, triggers browser download via `<a>` click with `download` attribute. Shows loading state while waiting.

### Task 7: Build + deploy verification

1. Test locally — may fail on Windows due to GTK. If so, skip local and rely on Render.
2. Push to feature branch.
3. Watch Render deploy. If the engine fails to start with a WeasyPrint ImportError, add Cairo/Pango/GDK to `render.yaml` via `packages:` or add a build-time `apt-get install`.
4. Drive the UI via Playwright on prod — open a case, click "Generate PDF", verify the download contains a real PDF.

---

## Scope boundaries

- **No network graph image.** Rendering a graph to PNG requires graphviz or similar. Skip for v1 — the graph is visible in the web UI.
- **No charts.** Tables only.
- **One template.** `case_pack.html`. Other report types (national/compliance) can reuse later.
- **No pagination optimization.** WeasyPrint handles basic page breaks; I won't hand-tune.
- **Only the button on case-export.tsx.** The existing `/reports/export` stays a placeholder for now (it's a different flow — national/compliance reports, not case packs).

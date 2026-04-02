from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import admin, ai, alerts, cases, intelligence, investigate, network, overview, reports, scan, str_reports, system

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Kestrel intelligence engine",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system.router, tags=["system"])
app.include_router(ai.router, prefix="/ai", tags=["ai"])
app.include_router(overview.router, prefix="/overview", tags=["overview"])
app.include_router(investigate.router, prefix="/investigate", tags=["investigate"])
app.include_router(network.router, prefix="/network", tags=["network"])
app.include_router(scan.router, prefix="/scan", tags=["scan"])
app.include_router(str_reports.router, prefix="/str-reports", tags=["str-reports"])
app.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
app.include_router(cases.router, prefix="/cases", tags=["cases"])
app.include_router(intelligence.router, prefix="/intelligence", tags=["intelligence"])
app.include_router(reports.router, prefix="/reports", tags=["reports"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])

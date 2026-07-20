from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from config import ALLOWED_ORIGINS, DEBUG
from db import init_db
from modules.auth.routes import router as auth_router
from modules.journal.routes import router as journal_router
from modules.market_data.routes import router as market_router
from modules.subscriptions.routes import expire_subscriptions_job, router as subs_router

scheduler = BackgroundScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    scheduler.add_job(expire_subscriptions_job, "cron", hour=0, minute=5)
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(
    title="FasTradeX API",
    description="Expiry Scalping Command Centre — educational trading assistant",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(market_router)
app.include_router(journal_router)
app.include_router(subs_router)

frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
frontend_dist_dir = frontend_dir / "dist"
serve_dir = frontend_dist_dir if frontend_dist_dir.exists() else frontend_dir

if serve_dir.exists():
    assets_dir = serve_dir / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="frontend-assets")

    @app.get("/", include_in_schema=False)
    async def serve_frontend_root():
        return FileResponse(str(serve_dir / "index.html"))

    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "service": "FasTradeX",
            "mode": "debug" if DEBUG else "production",
        }

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend_spa(full_path: str):
        if full_path.startswith(("api/", "auth/", "journal/", "docs", "openapi.json")):
            raise HTTPException(status_code=404, detail="Not Found")

        target_path = serve_dir / full_path
        if target_path.exists() and target_path.is_file():
            return FileResponse(str(target_path))
        return FileResponse(str(serve_dir / "index.html"))


def main() -> None:
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()

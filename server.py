from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from core.database import init_db
from .api import router

BASE = Path(__file__).resolve().parent
app = FastAPI(title="MEETTOGETHER Mini App")
app.include_router(router)
app.mount("/assets", StaticFiles(directory=BASE / "assets"), name="assets")

@app.on_event("startup")
def startup():
    init_db()

@app.get("/")
def index():
    return FileResponse(BASE / "index.html")

"""ViruContext local web app."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from virucontext.europepmc import PaperNotOpenAccess, PaperNotFound, resolve_paper
from virucontext.summarize import SummarizerNotConfigured, make_packet

load_dotenv()

ROOT = Path(__file__).parent
STATIC = ROOT / "static"

app = FastAPI(
    title="ViruContext",
    description="Open-access virology papers → locked field packet for writing, teaching, and tools.",
    version="0.1.0",
)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


class SummarizeIn(BaseModel):
    query: str = Field(..., min_length=3, max_length=500)
    virus_of_interest: str | None = Field(default=None, max_length=200)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/api/health")
def health() -> dict:
    return {
        "ok": True,
        "model": os.getenv("VIRUCONTEXT_MODEL", "gpt-4o"),
        "openai_key_present": bool(os.getenv("OPENAI_API_KEY")),
    }


@app.post("/api/summarize")
def summarize(body: SummarizeIn) -> dict:
    query = body.query.strip()
    virus = (body.virus_of_interest or "").strip() or None
    try:
        paper = resolve_paper(query)
        packet = make_packet(paper, virus_of_interest=virus)
    except PaperNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PaperNotOpenAccess as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except SummarizerNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 — surface lookup/LLM failures to the UI
        raise HTTPException(status_code=502, detail=f"Lookup or summarization failed: {exc}") from exc

    return {
        "paper": paper.to_public_dict(),
        "packet": packet,
        "virus_of_interest": virus,
    }

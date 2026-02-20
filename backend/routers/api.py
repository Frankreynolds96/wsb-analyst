from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

from fastapi import APIRouter, HTTPException

from backend.agent.orchestrator import run_analysis
from backend.analysis.fundamental import analyze_fundamentals
from backend.analysis.risk import analyze_risk
from backend.analysis.technical import analyze_technicals
from backend.data.market import get_financial_statements, get_stock_data
from backend.models.schemas import AnalysisResult
from backend.scrapers.reddit import get_trending_tickers

router = APIRouter(prefix="/api")

# In-memory job store (swap for Redis/DB in production)
_jobs: dict[str, AnalysisResult] = {}
_jobs_lock = Lock()
_executor = ThreadPoolExecutor(max_workers=2)


def _run_job(job_id: str) -> None:
    """Run analysis in background thread."""
    try:
        result = run_analysis(job_id)
        with _jobs_lock:
            _jobs[job_id] = result
    except Exception as e:
        with _jobs_lock:
            _jobs[job_id] = AnalysisResult(
                job_id=job_id, status="error", error=str(e)
            )


@router.get("/trending")
def api_trending(time_filter: str = "day", limit: int = 100):
    """Get currently trending WSB tickers."""
    tickers = get_trending_tickers(time_filter=time_filter, limit=limit)
    return {"tickers": [t.model_dump() for t in tickers]}


@router.post("/analyze")
def api_analyze():
    """Trigger a full agent analysis. Returns a job ID to poll."""
    job_id = str(uuid.uuid4())[:8]
    with _jobs_lock:
        _jobs[job_id] = AnalysisResult(job_id=job_id, status="running")
    _executor.submit(_run_job, job_id)
    return {"job_id": job_id, "status": "running"}


@router.get("/analyze/{job_id}")
def api_analyze_status(job_id: str):
    """Poll for analysis job status and results."""
    with _jobs_lock:
        job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.model_dump(mode="json")


@router.get("/recommendations")
def api_recommendations():
    """Get the latest completed analysis recommendations."""
    with _jobs_lock:
        completed = [
            j for j in _jobs.values() if j.status == "completed"
        ]
    if not completed:
        return {"recommendations": [], "message": "No completed analyses yet"}
    latest = max(completed, key=lambda j: j.completed_at or j.created_at)
    return latest.model_dump(mode="json")


@router.get("/stock/{ticker}")
def api_stock_detail(ticker: str):
    """Get detailed analysis for a single stock."""
    ticker = ticker.upper()
    try:
        stock_data = get_stock_data(ticker)
        financials = get_financial_statements(ticker)
        fundamental = analyze_fundamentals(ticker, stock_data, financials)
        technical = analyze_technicals(ticker, stock_data)
        risk = analyze_risk(ticker, stock_data)

        return {
            "ticker": ticker,
            "info": stock_data.info.model_dump(),
            "fundamental": fundamental.model_dump(),
            "technical": technical.model_dump(),
            "risk": risk.model_dump(),
            "price_history": [bar.model_dump() for bar in stock_data.history[-60:]],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed for {ticker}: {str(e)}")

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from .tracker import log_event, resolve_org
from .models import init_db
import os

app = FastAPI(title="Document Tracker")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
)

# Destination map — all your links
DESTINATIONS = {
    "gh":         "https://github.com/IpsitMohanty",
    "li":         "https://www.linkedin.com/in/ipsit-mohanty/",
    "demo/cnn":   "https://cnn-vit-land-classification.streamlit.app/",
    "demo/rag":   "https://rag-ingestion-evaluation.streamlit.app",
    "demo/rec":   "https://course-recommender-system-dlrwwyqrh9vvstfxaf79wn.streamlit.app/",
    "demo/awc":   "https://awc-operations-dashboard.streamlit.app",
    "repo/awc":   "https://github.com/IpsitMohanty/awc-operations-dashboard",
    "repo/cnn":   "https://github.com/IpsitMohanty/cnn-vit-land-classification",
    "repo/rag":   "https://github.com/IpsitMohanty/rag-ingestion-evaluation",
    "repo/rec":   "https://github.com/IpsitMohanty/course-recommender-system",
    "repo/poshan":"https://github.com/IpsitMohanty/poshan-intelligence-pipeline",
}

DOCUMENT_PATH = os.environ.get("DOCUMENT_PATH", "data/document.pdf")


@app.on_event("startup")
async def startup():
    init_db()


@app.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    ip = request.client.host
    org_info = await resolve_org(ip)
    log_event(
        token="landing",
        slug="landing_page",
        ip=ip,
        org=org_info.get("org", ""),
        city=org_info.get("city", ""),
        country=org_info.get("country", ""),
        user_agent=request.headers.get("user-agent", ""),
    )
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>Ipsit Mohanty — Data & ML Engineer</title>
      <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
          font-family: 'Courier New', monospace;
          background: #0f0f0f;
          color: #e0e0e0;
          min-height: 100vh;
          display: flex;
          align-items: center;
          justify-content: center;
        }
        .card {
          max-width: 560px;
          width: 90%;
          padding: 48px 40px;
          border: 1px solid #2a2a2a;
          border-radius: 4px;
        }
        h1 { font-size: 1.8rem; color: #fff; margin-bottom: 6px; }
        .role { color: #888; font-size: 0.9rem; margin-bottom: 24px; }
        .stack { color: #555; font-size: 0.78rem; margin-bottom: 32px; letter-spacing: 0.03em; }
        .links { display: flex; gap: 16px; margin-bottom: 36px; flex-wrap: wrap; }
        .links a {
          color: #4a9eff;
          text-decoration: none;
          font-size: 0.85rem;
          border-bottom: 1px solid transparent;
          transition: border-color 0.2s;
        }
        .links a:hover { border-color: #4a9eff; }
        .download-btn {
          display: inline-block;
          padding: 12px 28px;
          background: #4a9eff;
          color: #000;
          text-decoration: none;
          font-weight: bold;
          font-size: 0.85rem;
          border-radius: 2px;
          letter-spacing: 0.05em;
          transition: background 0.2s;
        }
        .download-btn:hover { background: #6ab4ff; }
        .footer { margin-top: 32px; color: #444; font-size: 0.72rem; }
      </style>
    </head>
    <body>
      <div class="card">
        <h1>Ipsit Mohanty</h1>
        <div class="role">Data &amp; ML Engineer</div>
        <div class="stack">Python · ETL Pipelines · Analytical Warehousing · Machine Learning · FastAPI · GenAI (RAG)</div>
        <div class="links">
          <a href="/r/gh?t=landing">GitHub</a>
          <a href="/r/li?t=landing">LinkedIn</a>
          <a href="/r/demo/awc?t=landing">AWC Dashboard</a>
          <a href="/r/demo/rag?t=landing">RAG System</a>
          <a href="/r/demo/rec?t=landing">Recommender</a>
          <a href="/r/demo/cnn?t=landing">CNN-ViT</a>
        </div>
        <a class="download-btn" href="/document?t=landing">↓ Download</a>
        <div class="footer">ipsit13@gmail.com · 8433904389</div>
      </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.get("/r/{slug:path}")
async def redirect(slug: str, request: Request, t: str = "unknown"):
    destination = DESTINATIONS.get(slug)
    if not destination:
        return HTMLResponse("Link not found", status_code=404)

    ip = request.client.host
    org_info = await resolve_org(ip)
    log_event(
        token=t,
        slug=slug,
        ip=ip,
        org=org_info.get("org", ""),
        city=org_info.get("city", ""),
        country=org_info.get("country", ""),
        user_agent=request.headers.get("user-agent", ""),
    )
    return RedirectResponse(url=destination, status_code=302)


@app.get("/document")
async def serve_document(request: Request, t: str = "unknown"):
    ip = request.client.host
    org_info = await resolve_org(ip)
    log_event(
        token=t,
        slug="document_download",
        ip=ip,
        org=org_info.get("org", ""),
        city=org_info.get("city", ""),
        country=org_info.get("country", ""),
        user_agent=request.headers.get("user-agent", ""),
    )
    if not os.path.exists(DOCUMENT_PATH):
        return HTMLResponse("Document not found. Place your PDF at data/document.pdf", status_code=404)
    return FileResponse(
        DOCUMENT_PATH,
        media_type="application/pdf",
        filename="document.pdf",
    )


if __name__ == "__main__":
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)

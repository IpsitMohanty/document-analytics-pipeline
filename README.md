# Document Analytics Pipeline

A per-recipient document distribution and analytics system: every link inside a distributed
PDF routes through a tracking layer that attributes each open and click to the specific
recipient it was sent to, and to the organisation behind the visiting IP — turning a static
document into an instrumented one.

## What it does

- **Per-recipient token system.** Every recipient gets a unique 8-character token baked into
  every link inside their copy of the document at generation time. No two recipients' copies
  are byte-identical.
- **Redirect router with IP-to-org attribution.** Every tracked link (document download,
  outbound links, landing page) resolves through a redirect router that logs the hit —
  token, destination, IP, user agent, timestamp — and resolves the visiting IP to an
  organisation, city, and country via `ipinfo.io`'s free tier (no API key required).
- **Forwarding detection.** Because every hit is logged per-token with org/IP attribution,
  a single token showing multiple distinct organisations or IP ranges is a direct signal
  that the document was forwarded beyond its original recipient — something a plain
  "email open" pixel can't tell you.
- **Private audit dashboard.** A password-gated Streamlit app for reviewing the full event
  log: per-recipient summaries, org/IP filters, a hit timeline, and a token generator. Not
  public-facing by design — it exposes who looked at what, from where.
- **LaTeX document pipeline with placeholder substitution.** The source document is a LaTeX
  template with `%%TRACKER_*%%` placeholders in place of every link. A generator script
  substitutes each placeholder with that recipient's tracked URL and compiles a versioned
  PDF, so the tracking layer never has to touch the document's actual content or design.

## Key empirical finding

Running this against a set of real applications surfaced a consistent, detectable pattern:
**LinkedIn's crawler (`AS8075`, Microsoft Corporation — geolocated to Dulles Town Center)
systematically follows every embedded link in an uploaded PDF within seconds of upload.**
It shows up in the event log as a single token generating hits across nearly every tracked
slug in immediate succession, from an org attribution that's obviously automated rather
than human — a fingerprint that's straightforward to distinguish from a real recruiter or
hiring manager opening the same document once IP-to-org attribution is in place.

## Stack

- **FastAPI** — redirect router, document serving, landing page
- **PostgreSQL** — event log and recipient store
- **Streamlit** — private audit dashboard
- **LaTeX** (XeLaTeX) — templated document generation with per-recipient token injection.
  LaTeX is what this instance uses for template generation; any document format that
  supports embedded hyperlinks (e.g. a templated Word or HTML-to-PDF pipeline) is
  compatible with the same tracking layer — the redirect router and token system don't
  care how the PDF was produced.

## How it works

```
generate_document.py --recipient "Acme Corp" --auto-token
        │
        ▼
  LaTeX template (%%TRACKER_*%% placeholders)
        │  substitute every placeholder with /r/{slug}?t={token}
        ▼
  compiled, recipient-specific PDF
        │  distributed to "Acme Corp"
        ▼
  every link click / document open  ──▶  redirect router  ──▶  event log (Postgres)
                                              │                      │
                                     IP → org/city/country      audit dashboard
                                        (ipinfo.io)              (private, Streamlit)
```

## Repository layout

```
api/            FastAPI app — redirect router, document serving, landing page, IP attribution
dashboard/      Streamlit audit dashboard (password-gated)
latex/          LaTeX templates and the recipient/token document generator
```

## Local development

```bash
pip install -r requirements.txt

# API
uvicorn api.main:app --reload

# Dashboard (separate terminal)
DATABASE_URL=postgresql://user:pass@host/dbname \
DASHBOARD_PASSWORD=yourpassword \
streamlit run dashboard/app.py
# or: bash run_dashboard.sh "postgresql://..." "yourpassword"

# Generate a tracked document for a recipient
export TRACKER_BASE_URL=https://your-tracker-host.example.com
python latex/generate_document.py --recipient "Acme Corp" --auto-token
```

Requires XeLaTeX on the machine that compiles the PDF (for the document's font handling);
if it isn't available, the generator still writes the substituted `.tex` for a manual compile.

## Environment variables

| Variable | Description |
|---|---|
| `TRACKER_BASE_URL` | Base URL the redirect router is reachable at |
| `DATABASE_URL` | PostgreSQL connection string |
| `DOCUMENT_PATH` | Path to the source document served for download |
| `DASHBOARD_PASSWORD` | Password for the audit dashboard's auth gate |

## Design notes

- Every distributed link routes through the redirect layer — never a direct URL — so every
  open and click is attributable back to a specific recipient and token.
- The audit dashboard is intentionally private: it surfaces exactly who opened a document
  and from where, which is not information to expose publicly.
- IP attribution runs on `ipinfo.io`'s free, keyless tier — sufficient volume for
  per-recipient document tracking without any API key management.

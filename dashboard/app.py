import streamlit as st
import pandas as pd
import os
import sys

# Allow running from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api import models  # noqa: E402  (needs sys.path fix above first)

st.set_page_config(
    page_title="Document Tracker — Ipsit Mohanty",
    page_icon="📊",
    layout="wide",
)

# --- Auth gate ---
PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "changeme")
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("Document Tracker")
    pwd = st.text_input("Password", type="password")
    if st.button("Login"):
        if pwd == PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Wrong password")
    st.stop()


# --- Data loading ---
@st.cache_data(ttl=30)
def load_data():
    if not models.USE_POSTGRES and not os.path.exists(models.DB_PATH):
        return pd.DataFrame(), pd.DataFrame()
    events = pd.DataFrame(models.get_all_events())
    summary = pd.DataFrame(models.get_summary())
    return events, summary


# --- UI ---
st.title("📊 Document Tracker")
db_label = "Postgres" if models.USE_POSTGRES else f"SQLite `{models.DB_PATH}`"
st.caption(f"DB: {db_label} · Auto-refreshes every 30s")

col1, col2, col3 = st.columns(3)

events, summary = load_data()

if events.empty:
    st.info("No events yet. Generate a token and share a document to start tracking.")
    st.stop()

total_hits = len(events)
unique_tokens = events["token"].nunique()
unique_orgs = events["org"].dropna().replace("", pd.NA).dropna().nunique()

col1.metric("Total hits", total_hits)
col2.metric("Tokens active", unique_tokens)
col3.metric("Orgs seen", unique_orgs)

st.divider()

# --- Summary table ---
st.subheader("Recipients")
if not summary.empty:
    display_summary = summary.copy()
    display_summary["recipient"] = display_summary.apply(
        lambda r: r["recipient"] if pd.notna(r["recipient"]) else r["token"], axis=1
    )
    st.dataframe(
        display_summary[["recipient", "token", "total_hits", "links_clicked", "unique_ips", "last_seen", "orgs_seen"]],
        use_container_width=True,
        hide_index=True,
    )

st.divider()

# --- Filters ---
st.subheader("Event Log")

col_a, col_b, col_c = st.columns(3)
token_filter = col_a.selectbox("Token", ["All"] + sorted(events["token"].unique().tolist()))
slug_filter = col_b.selectbox("Link", ["All"] + sorted(events["slug"].unique().tolist()))
org_filter = col_c.text_input("Org contains", "")

filtered = events.copy()
if token_filter != "All":
    filtered = filtered[filtered["token"] == token_filter]
if slug_filter != "All":
    filtered = filtered[filtered["slug"] == slug_filter]
if org_filter:
    filtered = filtered[filtered["org"].str.contains(org_filter, case=False, na=False)]

display_cols = ["ts", "recipient_label", "token", "slug", "org", "city", "country", "ip", "user_agent"]
st.dataframe(
    filtered[display_cols].rename(columns={
        "ts": "Timestamp",
        "recipient_label": "Recipient",
        "token": "Token",
        "slug": "Link",
        "org": "Org",
        "city": "City",
        "country": "Country",
        "ip": "IP",
        "user_agent": "User Agent",
    }),
    use_container_width=True,
    hide_index=True,
)

st.divider()

# --- Timeline chart ---
st.subheader("Hit Timeline")
if not filtered.empty:
    filtered["date"] = pd.to_datetime(filtered["ts"]).dt.date
    timeline = filtered.groupby("date").size().reset_index(name="hits")
    st.bar_chart(timeline.set_index("date")["hits"])

st.divider()

# --- Token generator ---
st.subheader("Generate Token")
with st.form("token_form"):
    label = st.text_input("Recipient label", placeholder="e.g. Hays, TCS via Avance, Accenture-Goldy")
    submitted = st.form_submit_button("Generate")
    if submitted and label:
        import hashlib, time
        raw = f"{label}-{time.time()}"
        token = hashlib.md5(raw.encode()).hexdigest()[:8]
        models.insert_recipient(token, label)
        st.success(f"Token: `{token}`")
        st.code(f"python latex/generate_document.py --recipient \"{label}\" --token {token}", language="bash")
        st.cache_data.clear()

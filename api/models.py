import os

DATABASE_URL = os.environ.get("DATABASE_URL")
USE_POSTGRES = bool(DATABASE_URL)

if USE_POSTGRES:
    import psycopg2
    import psycopg2.extras
else:
    import sqlite3

DB_PATH = os.environ.get("DB_PATH", "data/tracker.db")


def get_conn():
    """Return a DB-API connection: Postgres if DATABASE_URL is set, else local SQLite."""
    if USE_POSTGRES:
        return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _q(sql: str) -> str:
    """Translate sqlite-style '?' placeholders to psycopg2 '%s' style."""
    return sql.replace("?", "%s") if USE_POSTGRES else sql


def init_db():
    if not USE_POSTGRES:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    id_col = "id SERIAL PRIMARY KEY" if USE_POSTGRES else "id INTEGER PRIMARY KEY AUTOINCREMENT"
    ts_type = "TIMESTAMP" if USE_POSTGRES else "DATETIME"

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS events (
            {id_col},
            token       TEXT NOT NULL,
            slug        TEXT NOT NULL,
            ip          TEXT,
            org         TEXT,
            city        TEXT,
            country     TEXT,
            user_agent  TEXT,
            ts          {ts_type} DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS recipients (
            token       TEXT PRIMARY KEY,
            label       TEXT NOT NULL,
            created_at  {ts_type} DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def insert_event(token: str, slug: str, ip: str, org: str, city: str, country: str, user_agent: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        _q("""INSERT INTO events (token, slug, ip, org, city, country, user_agent)
              VALUES (?, ?, ?, ?, ?, ?, ?)"""),
        (token, slug, ip, org, city, country, user_agent)
    )
    conn.commit()
    conn.close()


def insert_recipient(token: str, label: str):
    conn = get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute(
            """INSERT INTO recipients (token, label) VALUES (%s, %s)
               ON CONFLICT (token) DO UPDATE SET label = EXCLUDED.label""",
            (token, label)
        )
    else:
        cur.execute(
            "INSERT OR REPLACE INTO recipients (token, label) VALUES (?, ?)",
            (token, label)
        )
    conn.commit()
    conn.close()


def get_all_events():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT e.*, r.label as recipient_label
        FROM events e
        LEFT JOIN recipients r ON e.token = r.token
        ORDER BY e.ts DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_events_by_token(token: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(_q("SELECT * FROM events WHERE token = ? ORDER BY ts DESC"), (token,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_summary():
    org_agg = (
        "STRING_AGG(DISTINCT NULLIF(e.org, ''), ', ')"
        if USE_POSTGRES
        else "GROUP_CONCAT(DISTINCT e.org)"
    )
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"""
        SELECT
            e.token,
            r.label as recipient,
            COUNT(*) as total_hits,
            COUNT(DISTINCT e.slug) as links_clicked,
            COUNT(DISTINCT e.ip) as unique_ips,
            MAX(e.ts) as last_seen,
            MIN(e.ts) as first_seen,
            {org_agg} as orgs_seen
        FROM events e
        LEFT JOIN recipients r ON e.token = r.token
        GROUP BY e.token, r.label
        ORDER BY last_seen DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

import httpx
from .models import insert_event

IPINFO_URL = "https://ipinfo.io/{ip}/json"

# IPs that are not useful to look up
LOCAL_IPS = {"127.0.0.1", "::1", "localhost"}


async def resolve_org(ip: str) -> dict:
    """Look up org, city, country from IP using ipinfo.io (free tier, no key needed for low volume)."""
    if ip in LOCAL_IPS or ip.startswith("192.168.") or ip.startswith("10."):
        return {"org": "local", "city": "local", "country": "local"}
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(IPINFO_URL.format(ip=ip))
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "org":     data.get("org", ""),
                    "city":    data.get("city", ""),
                    "country": data.get("country", ""),
                }
    except Exception:
        pass
    return {"org": "", "city": "", "country": ""}


def log_event(token: str, slug: str, ip: str, org: str, city: str, country: str, user_agent: str):
    insert_event(token, slug, ip, org, city, country, user_agent)

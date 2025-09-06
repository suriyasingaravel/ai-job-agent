import requests
from typing import List, Dict, Any
from ai_job_agent.apps.api.settings import settings

BASE = "https://serpapi.com/search.json"

def serp_search_site(site: str, q: str, max_results: int=10) -> List[Dict[str, Any]]:
    if not settings.serpapi_key:
        return []
    params = {
        "engine": "google",
        "q": f"site:{site} {q}",
        "num": max_results,
        "api_key": settings.serpapi_key
    }
    r = requests.get(BASE, params=params, timeout=25)
    r.raise_for_status()
    js = r.json()
    results = []
    for item in (js.get("organic_results") or []):
        results.append({
            "title": item.get("title"),
            "url": item.get("link"),
            "snippet": item.get("snippet"),
        })
    return results

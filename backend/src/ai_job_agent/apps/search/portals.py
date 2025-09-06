from typing import List, Dict, Any
from .base import Searcher
from .serpapi_client import serp_search_site

# Simple adapters using public site: searches via SerpAPI
DOMAIN_MAP = {
    "linkedin": "linkedin.com/jobs",
    "naukri": "naukri.com",
    "indeed": "indeed.com",
    "hirist": "hirist.com",
    "timesjobs": "timesjobs.com",
    "talentoindia": "talentoindia.com",  # adjust if needed
}

class PortalSearcher(Searcher):
    def __init__(self, portal: str):
        self.portal = portal
        self.domain = DOMAIN_MAP.get(portal, portal)

    def search(self, query: str, max_results: int = 20) -> List[Dict[str, Any]]:
        rows = serp_search_site(self.domain, query, max_results)
        out=[]
        for r in rows:
            out.append({
                "title": r.get("title",""),
                "company": "",
                "location": None,
                "url": r.get("url"),
                "portal": self.portal,
                "snippet": r.get("snippet",""),
            })
        return out

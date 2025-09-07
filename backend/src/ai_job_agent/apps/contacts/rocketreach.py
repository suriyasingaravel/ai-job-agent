# ai_job_agent/apps/contacts/rocketreach.py
from __future__ import annotations
from typing import Optional, Dict, Any
import requests
from requests.auth import HTTPBasicAuth
from ai_job_agent.apps.api.settings import settings

RR_BASE = "https://api.rocketreach.co/v2/api"

def _auth() -> HTTPBasicAuth | None:
    if not settings.rocketreach_api_key:
        return None
    # Basic auth: username = API key, password = empty
    return HTTPBasicAuth(settings.rocketreach_api_key, "")

def _clean_person(p: dict, fallback_company: Optional[str] = None) -> Dict[str, Any]:
    # RocketReach field names vary; normalize the most useful bits
    return {
        "found": True,
        "name": p.get("name") or p.get("full_name") or None,
        "email": p.get("email") or p.get("current_work_email") or None,
        "linkedin": p.get("linkedin_url") or p.get("profile_url") or None,
        "company": p.get("current_employer") or p.get("company") or fallback_company,
        "title": p.get("current_title") or p.get("title") or None,
    }

def lookup_hr(
    company: str | None = None,
    role_hint: str = "recruiter",
    job_url: str | None = None,
    linkedin_url: str | None = None,
) -> Optional[Dict[str, Any]]:
    """
    - If linkedin_url is provided, try profile lookup (best).
    - Else, try people search by company + role.
    Returns a dict compatible with ContactInfo or None.
    """
    auth = _auth()
    if not auth:
        return None

    # 1) Direct profile lookup by LinkedIn URL
    if linkedin_url:
        try:
            resp = requests.post(
                f"{RR_BASE}/lookupProfile",
                json={"profile_url": linkedin_url},
                auth=auth,
                timeout=20,
            )
            if resp.status_code == 200:
                data = resp.json() or {}
                # Some plans return {"profiles":[...]} others single object — handle both
                if isinstance(data, dict) and "profiles" in data and data["profiles"]:
                    return _clean_person(data["profiles"][0], fallback_company=company)
                elif isinstance(data, dict) and (data.get("name") or data.get("full_name")):
                    return _clean_person(data, fallback_company=company)
                # Not found
            # 404/402/401 -> not found/plan/auth issues
        except Exception:
            pass  # fall through to people search

    # 2) People search by company + role/title (broader but useful)
    if company:
        query: Dict[str, Any] = {
            "current_employer": company,
        }
        # help the search with a few common HR/recruiter titles if user gave only 'recruiter'
        if role_hint and role_hint.strip():
            query["current_title"] = role_hint
        elif job_url:
            query["keywords"] = "recruiter OR talent acquisition OR HR"

        try:
            resp = requests.post(
                f"{RR_BASE}/search/people",
                json={"query": query, "page": 1, "per_page": 1},
                auth=auth,
                timeout=20,
            )
            if resp.status_code == 200:
                data = resp.json() or {}
                people = data.get("results") or data.get("people") or []
                if people:
                    return _clean_person(people[0], fallback_company=company)
        except Exception:
            pass

    return None

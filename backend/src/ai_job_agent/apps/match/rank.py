from typing import List, Dict, Any
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from rapidfuzz import fuzz
from ai_job_agent.apps.llm.gemini import embed

def _text_of_hit(h: Dict[str, Any]) -> str:
    return " ".join([
        h.get("title",""), h.get("company","") or "",
        h.get("location","") or "", h.get("snippet","") or ""
    ]).strip()

def rank_jobs(profile: Dict[str, Any], hits: List[Dict[str, Any]], top_k: int = 20) -> List[Dict[str, Any]]:
    if not hits: return []
    skills = ", ".join(profile.get("skills") or [])
    roles = ", ".join(profile.get("roles") or [])
    locs  = ", ".join(profile.get("locations") or [])
    query = f"roles: {roles}; skills: {skills}; locations: {locs}; exp: {profile.get('years_experience',0)} years"

    job_texts = [_text_of_hit(h) for h in hits]
    em_q = np.array(embed([query])[0]).reshape(1,-1)
    em_jobs = embed(job_texts)
    if len(em_jobs)==0:
        return []
    em_jobs = np.array([e if e else np.zeros_like(em_q[0]) for e in em_jobs])

    cos = cosine_similarity(em_q, em_jobs)[0]
    role_pref = (profile.get("roles") or [""])[0]
    fuzzy = np.array([fuzz.token_set_ratio(role_pref, h.get("title",""))/100.0 for h in hits])

    scores = 0.7*cos + 0.3*fuzzy

    ranked = []
    for h, s in zip(hits, scores):
        h2 = h.copy()
        h2["score"] = float(round(float(s), 3))
        ranked.append(h2)

    ranked.sort(key=lambda x: x["score"], reverse=True)
    return ranked[:top_k]

# src/ai_job_agent/apps/api/main.py
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os, tempfile, shutil

from ai_job_agent.apps.api.settings import settings
from ai_job_agent.apps.api.schemas import (
    HealthResponse, UploadResponse, ProfileIn, ProfileOut,
    SearchRequest, SearchResponse, PipelineRequest,
    ComposeRequest, ComposeResponse, JobHit, ContactInfo, EnrichRequest
)
from ai_job_agent.apps.profile.resume import extract_text_from_pdf, guess_skills, token_count
from ai_job_agent.apps.profile.profile_store import upsert_profile, get_profile
from ai_job_agent.apps.search.portals import PortalSearcher, DOMAIN_MAP
from ai_job_agent.apps.match.rank import rank_jobs
from ai_job_agent.apps.contacts.rocketreach import lookup_hr
from ai_job_agent.apps.graph.pipeline import run_email_pipeline  # LangGraph-powered compose

# Construct all portal searchers once
PORTAL_SEARCHERS = {name: PortalSearcher(name) for name in DOMAIN_MAP.keys()}

app = FastAPI(title="AI Job Agent API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501", "http://127.0.0.1:8501",
        "http://localhost:3000",  # local dev
        "*"  # if you deploy a separate frontend domain, you can tighten this later
    ],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

# ---------------------- Misc ----------------------

@app.get("/")
def root():
    return {"message": "Welcome to AI Job agent application"}

@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok", data_dir=settings.data_dir)

# ---------------------- Profile ----------------------

@app.post("/profile/set", response_model=ProfileOut)
def set_profile(p: ProfileIn):
    d = p.model_dump()
    pid = upsert_profile(d)
    d["id"] = pid
    return ProfileOut(**d)

@app.post("/upload_resume", response_model=UploadResponse)
async def upload_resume(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Upload a PDF resume")
    tmpdir = tempfile.mkdtemp(prefix="resume_")
    try:
        pth = os.path.join(tmpdir, file.filename)
        with open(pth, "wb") as f:
            f.write(await file.read())

        text = extract_text_from_pdf(pth)
        skills = guess_skills(text)
        pid = upsert_profile({"resume_text": text, "skills": skills})

        return UploadResponse(
            ok=True,
            tokens=token_count(text),
            extracted_skills=skills,
            profile_id=pid
        )
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

# ---------------------- Job Search ----------------------

@app.post("/search_jobs", response_model=SearchResponse)
def search_jobs(req: SearchRequest, profile_id: str):
    profile = get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    roles   = profile.get("roles") or []
    locs    = profile.get("locations") or []
    portals = profile.get("portals") or list(PORTAL_SEARCHERS.keys())
    skills  = " ".join(profile.get("skills") or [])
    base_q  = f"{' OR '.join(roles)} {skills} {' OR '.join(locs)}".strip()

    all_hits = []
    for portal in portals:
        s = PORTAL_SEARCHERS.get(portal)
        if not s:
            continue
        hits = s.search(base_q, max_results=max(1, req.max_results // max(1, len(portals))))
        for h in hits:
            h["portal"] = portal
        all_hits.extend(hits)

    ranked = rank_jobs(profile, all_hits, top_k=req.max_results)
    out = [
        JobHit(**{
            "title":   h.get("title", ""),
            "company": h.get("company", "") or "",
            "location": h.get("location"),
            "url":     h.get("url"),
            "portal":  h.get("portal"),
            "snippet": h.get("snippet"),
            "score":   float(h.get("score", 0.0)),
        })
        for h in ranked
    ]
    return SearchResponse(hits=out)

# ---------------------- Contact Enrichment ----------------------

@app.post("/contact/enrich", response_model=ContactInfo)
def contact_enrich(req: EnrichRequest):
    """
    Accepts JSON:
      {
        "job": JobHit,
        "profile_id": "...",
        "query": {
          "company"?: str,
          "job_title"?: str,
          "job_url"?: str,
          "linkedin_url"?: str
        }
      }

    Tries LinkedIn URL first (if provided), otherwise falls back to company/title/url hints.
    """
    q   = req.query or None
    job = req.job

    linkedin_url = (q.linkedin_url if q else None) or None
    company      = (q.company if q else None) or (job.company or None)
    job_title    = (q.job_title if q else None) or (job.title or None)
    job_url      = (q.job_url if q else None) or (job.url or None)

    data = None

    # 1) Prefer direct LinkedIn profile, if provided
    if linkedin_url:
        try:
            data = lookup_hr(linkedin_url=linkedin_url)
        except TypeError:
            data = None  # helper may not support this signature

    # 2) Otherwise try company + role/url hints
    if not data and company:
        try:
            data = lookup_hr(company=company, role_hint=job_title or "recruiter", job_url=job_url)
        except TypeError:
            # legacy helper signature (company, role_hint="recruiter")
            data = lookup_hr(company, "recruiter")

    if not data:
        return ContactInfo(found=False, company=company or None)

    return ContactInfo(
        found=True,
        name=data.get("name"),
        email=data.get("email"),
        linkedin=data.get("linkedin"),
        company=data.get("company") or company,
        title=data.get("title"),
    )

# ---------------------- Compose Email (LangGraph + LangChain) ----------------------

@app.post("/compose", response_model=ComposeResponse)
def compose(req: ComposeRequest):
    profile = get_profile(req.profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Pydantic -> dicts for graph
    job_dict = req.job.model_dump()
    contact_dict = req.contact.model_dump() if req.contact else None

    subject, body = run_email_pipeline(profile, job_dict, contact_dict)
    return ComposeResponse(subject=subject, body=body)

# ---------------------- Simple Orchestrated Pipeline ----------------------

@app.post("/pipeline/run", response_model=SearchResponse)
def pipeline(req: PipelineRequest):
    profile = get_profile(req.profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    roles = profile.get("roles") or []
    skills = " ".join(profile.get("skills") or [])
    locs = profile.get("locations") or []
    q = f"{' OR '.join(roles)} {skills} {' OR '.join(locs)}".strip()

    all_hits = []
    for p in req.portals:
        s = PORTAL_SEARCHERS.get(p)
        if not s:
            continue
        all_hits.extend(s.search(q, max_results=max(1, req.max_results // max(1, len(req.portals)))))

    ranked = rank_jobs(profile, all_hits, top_k=req.max_results)
    out = [JobHit(**{**h, "score": float(h.get("score", 0.0))}) for h in ranked]
    return SearchResponse(hits=out)

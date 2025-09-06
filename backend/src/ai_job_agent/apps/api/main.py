from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import os, tempfile, shutil

from ai_job_agent.apps.api.settings import settings
from ai_job_agent.apps.api.schemas import (
    HealthResponse, UploadResponse, ProfileIn, ProfileOut,
    SearchRequest, SearchResponse, PipelineRequest, ComposeRequest, ComposeResponse, JobHit, ContactInfo
)
from ai_job_agent.apps.profile.resume import extract_text_from_pdf, guess_skills, token_count
from ai_job_agent.apps.profile.profile_store import upsert_profile, get_profile
from ai_job_agent.apps.search.portals import PortalSearcher, DOMAIN_MAP
from ai_job_agent.apps.match.rank import rank_jobs
from ai_job_agent.apps.contacts.rocketreach import lookup_hr
from ai_job_agent.apps.llm.gemini import chat

PORTAL_SEARCHERS = {name: PortalSearcher(name) for name in DOMAIN_MAP.keys()}

app = FastAPI(title="AI Job Agent API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501","http://127.0.0.1:8501","http://localhost:3000"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "Welcome to AI Job agent application"}

@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok", data_dir=settings.data_dir)

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
        with open(pth, "wb") as f: f.write(await file.read())
        text = extract_text_from_pdf(pth)
        skills = guess_skills(text)
        pid = upsert_profile({"resume_text": text, "skills": skills})
        return UploadResponse(ok=True, tokens=token_count(text), extracted_skills=skills, profile_id=pid)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

@app.post("/search_jobs", response_model=SearchResponse)
def search_jobs(req: SearchRequest, profile_id: str):
    profile = get_profile(profile_id)
    if not profile: raise HTTPException(status_code=404, detail="Profile not found")
    roles = profile.get("roles") or []
    locs  = profile.get("locations") or []
    portals = profile.get("portals") or list(PORTAL_SEARCHERS.keys())
    skills = " ".join(profile.get("skills") or [])
    base_q = f"{' OR '.join(roles)} {skills} {' OR '.join(locs)}"

    all_hits = []
    for portal in portals:
        s = PORTAL_SEARCHERS.get(portal)
        if not s: continue
        hits = s.search(base_q, max_results=req.max_results//max(1,len(portals)))
        for h in hits:
            h["portal"] = portal
        all_hits.extend(hits)

    ranked = rank_jobs(profile, all_hits, top_k=req.max_results)
    out = [JobHit(**{
        "title": h.get("title",""),
        "company": h.get("company","") or "",
        "location": h.get("location"),
        "url": h.get("url"),
        "portal": h.get("portal"),
        "snippet": h.get("snippet"),
        "score": float(h.get("score",0.0)),
    }) for h in ranked]
    return SearchResponse(hits=out)

@app.post("/contact/enrich", response_model=ContactInfo)
def contact_enrich(company: str, role_hint: str = "recruiter"):
    data = lookup_hr(company, role_hint)
    if not data:
        return ContactInfo(found=False, company=company)
    return ContactInfo(
        found=True,
        name=data.get("name"),
        email=data.get("email"),
        linkedin=data.get("linkedin"),
        company=data.get("company") or company,
        title=data.get("title"),
    )

@app.post("/compose", response_model=ComposeResponse)
def compose(req: ComposeRequest):
    profile = get_profile(req.profile_id)
    if not profile: raise HTTPException(status_code=404, detail="Profile not found")

    system = "You are an assistant that writes concise, professional, personalized job application emails."
    contact_line = ""
    if req.contact and (req.contact.name or req.contact.title or req.contact.company):
        nm = req.contact.name or "Hiring Team"
        ttl = req.contact.title or ""
        cmp = req.contact.company or ""
        contact_line = f"Recipient: {nm}, {ttl} at {cmp}.\n"

    prompt = f"""
{contact_line}
Job:
- Title: {req.job.title}
- Company: {req.job.company}
- Location: {req.job.location}
- URL: {req.job.url}
- Snippet: {req.job.snippet}

Candidate:
- Name: {profile.get('name','')}
- Email: {profile.get('email','')}
- Phone: {profile.get('phone','')}
- Experience: {profile.get('years_experience','')} years
- Roles: {', '.join(profile.get('roles') or [])}
- Skills: {', '.join(profile.get('skills') or [])}
- Locations: {', '.join(profile.get('locations') or [])}

Write a short email (max ~170 words) expressing interest, citing 3-4 relevant skills, and asking for next steps. Use a clear subject.
"""
    text = chat(prompt)
    subject = "Job application"
    body = text
    if text and text.lower().startswith("subject:"):
        first, *rest = text.splitlines()
        subject = first.split(":",1)[1].strip() or subject
        body = "\n".join(rest).strip()

    return ComposeResponse(subject=subject, body=body)

@app.post("/pipeline/run", response_model=SearchResponse)
def pipeline(req: PipelineRequest):
    profile = get_profile(req.profile_id)
    if not profile: raise HTTPException(status_code=404, detail="Profile not found")
    profile2 = profile.copy()
    roles = profile2.get("roles") or []
    skills = " ".join(profile2.get("skills") or [])
    locs = profile2.get("locations") or []
    q = f"{' OR '.join(roles)} {skills} {' OR '.join(locs)}"
    all_hits=[]
    for p in req.portals:
        s = PORTAL_SEARCHERS.get(p)
        if not s: continue
        all_hits.extend(s.search(q, max_results=req.max_results//max(1,len(req.portals))))
    ranked = rank_jobs(profile2, all_hits, top_k=req.max_results)
    out = [JobHit(**{**h}) for h in ranked]
    return SearchResponse(hits=out)

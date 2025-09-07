# src/ai_job_agent/apps/llm/chains.py
from langchain.prompts import ChatPromptTemplate
from langchain.schema.output_parser import StrOutputParser
from ai_job_agent.apps.llm.lc import llm

_email_prompt = ChatPromptTemplate.from_template(
    """You are a concise, professional assistant that writes short, tailored outreach emails.

{contact_block}
Job:
- Title: {job_title}
- Company: {job_company}
- Location: {job_location}
- URL: {job_url}
- Snippet: {job_snippet}

Candidate:
- Name: {name}
- Email: {email}
- Phone: {phone}
- Experience: {years_experience} years
- Target Roles: {roles}
- Skills: {skills}
- Locations: {locations}

Write:
1) A clear Subject: line (one line)
2) A short email body (<=170 words) highlighting 3–4 relevant skills and asking for next steps.

Return plain text starting with 'Subject:' on the first line."""
)

compose_email_chain = (_email_prompt | llm | StrOutputParser())

def compose_email(profile: dict, job: dict, contact: dict | None):
    contact_block = ""
    if contact and (contact.get("name") or contact.get("title") or contact.get("company")):
        contact_block = f"Recipient: {contact.get('name','Hiring Team')}, {contact.get('title','')} at {contact.get('company','')}.\n"

    text = compose_email_chain.invoke({
        "contact_block": contact_block,
        "job_title": job.get("title",""),
        "job_company": job.get("company",""),
        "job_location": job.get("location",""),
        "job_url": job.get("url",""),
        "job_snippet": job.get("snippet",""),
        "name": profile.get("name",""),
        "email": profile.get("email",""),
        "phone": profile.get("phone",""),
        "years_experience": profile.get("years_experience",""),
        "roles": ", ".join(profile.get("roles") or []),
        "skills": ", ".join(profile.get("skills") or []),
        "locations": ", ".join(profile.get("locations") or []),
    }).strip()

    subject, body = "Job application", text
    if text.lower().startswith("subject:"):
        lines = text.splitlines()
        subject = lines[0].split(":",1)[1].strip() or subject
        body = "\n".join(lines[1:]).strip()
    return subject, body

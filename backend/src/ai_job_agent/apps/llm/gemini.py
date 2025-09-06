import google.generativeai as genai
from ai_job_agent.apps.api.settings import settings

genai.configure(api_key=settings.google_api_key)

def embed(texts, model=None, task_type="retrieval_document"):
    model = model or settings.gemini_embeddings_model
    out = []
    for t in texts:
        t = (t or "").strip()
        if not t:
            out.append([])
        else:
            resp = genai.embed_content(model=model, content=t, task_type=task_type)
            out.append(resp["embedding"])
    return out

def chat(prompt: str, system: str | None = None, model: str = "gemini-1.5-flash"):
    p = prompt if not system else f"{system}\n\n{prompt}"
    resp = genai.GenerativeModel(model).generate_content(p)
    return resp.text

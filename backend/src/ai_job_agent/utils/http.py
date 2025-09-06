import requests
def get(url: str, **kw):
    r = requests.get(url, timeout=kw.pop("timeout",20))
    r.raise_for_status()
    return r.text

import os, time, hmac
from .bot import Env
from .exchange import http_json
from .store import UpstashStore

def authorized(headers, environ=os.environ):
    secret = environ.get("CRON_SECRET", "")
    if not secret: return False                      # gagal tertutup bila secret belum diset
    got = headers.get("Authorization", "")
    return hmac.compare_digest(got, f"Bearer {secret}")

def make_env():
    e = os.environ
    url = e.get("KV_REST_API_URL") or e.get("UPSTASH_REDIS_REST_URL")
    tok = e.get("KV_REST_API_TOKEN") or e.get("UPSTASH_REDIS_REST_TOKEN")
    if not url or not tok: raise RuntimeError("env Upstash belum diset")
    return Env(get=lambda u, on_err=None: http_json(u, on_error=on_err), store=UpstashStore(url, tok), now=time.time)

def make_store():
    return make_env().store

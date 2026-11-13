import os, sys, json
from urllib.parse import urlparse, parse_qs
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from http.server import BaseHTTPRequestHandler
from core.runtime import make_store, authorized
from core.bot import LOG_KEY, SNAP_KEY, STATE_KEY

class handler(BaseHTTPRequestHandler):
    """GET /api/export?what=log|snap|state&start=0&stop=499 -> data mentah untuk hitung_ulang & dashboard."""
    def _send(self, code, obj):
        b = json.dumps(obj).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        if not authorized(self.headers): return self._send(401, {"error": "unauthorized"})
        q = parse_qs(urlparse(self.path).query); what = q.get("what", ["log"])[0]
        a, b = int(q.get("start", ["0"])[0]), int(q.get("stop", ["499"])[0]); S = make_store()
        if what == "state": return self._send(200, {"state": json.loads(S.get(STATE_KEY) or "{}"), "kill": S.get("bot:kill")})
        key = LOG_KEY if what == "log" else SNAP_KEY
        self._send(200, {"items": [json.loads(x) for x in S.lrange(key, a, b)], "start": a, "stop": b})

import json, urllib.request

class MemStore:
    def __init__(self): self.kv, self.lists = {}, {}
    def get(self, k): return self.kv.get(k)
    def set(self, k, v): self.kv[k] = v
    def set_nx(self, k, v, ex):
        if k in self.kv: return False
        self.kv[k] = v; return True
    def delete(self, k): self.kv.pop(k, None)
    def rpush(self, k, v): self.lists.setdefault(k, []).append(v)
    def lrange(self, k, a, b): l = self.lists.get(k, []); return l[a:(None if b == -1 else b + 1)]

class UpstashStore:
    """Upstash Redis lewat REST (tanpa library tambahan)."""
    def __init__(self, url, token): self.url, self.token = url.rstrip("/"), token
    def _cmd(self, *args):
        req = urllib.request.Request(self.url, data=json.dumps([str(a) for a in args]).encode(), method="POST",
                                     headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as r: d = json.loads(r.read())
        if "error" in d: raise RuntimeError(d["error"])
        return d["result"]
    def get(self, k): return self._cmd("GET", k)
    def set(self, k, v): self._cmd("SET", k, v)
    def set_nx(self, k, v, ex): return self._cmd("SET", k, v, "NX", "EX", ex) == "OK"
    def delete(self, k): self._cmd("DEL", k)
    def rpush(self, k, v): self._cmd("RPUSH", k, v)
    def lrange(self, k, a, b): return self._cmd("LRANGE", k, a, b)

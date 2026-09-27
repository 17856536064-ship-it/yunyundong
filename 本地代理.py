# -*- coding: utf-8 -*-
"""本地 CORS 代理：浏览器 → http://127.0.0.1:8787 → 学校网关
用法：python 本地代理.py  然后网页版里接口填 http://127.0.0.1:8787
"""
from __future__ import annotations
import http.server, json, socketserver, urllib.request, urllib.error

PORT = 8787
UPSTREAM = "http://60.174.215.2:8000"

class H(http.server.BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(n) if n else b""
            path = self.path if self.path.startswith("/") else "/" + self.path
            if path.startswith("/m-api") or path.startswith("/api/"):
                url = UPSTREAM + path
            else:
                url = UPSTREAM + "/m-api" + path
            fwd = {k: v for k, v in self.headers.items()
                   if k.lower() not in ("host", "content-length", "connection", "origin", "referer")}
            req = urllib.request.Request(url, data=body, headers=fwd, method="POST")
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read()
                self.send_response(r.status)
                self._cors()
                self.send_header("Content-Type", r.headers.get("Content-Type", "application/json"))
                self.send_header("Content-Encoding", r.headers.get("Content-Encoding", "identity"))
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
        except urllib.error.HTTPError as e:
            data = e.read() if e.fp else b"{}"
            self.send_response(e.code)
            self._cors()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            data = json.dumps({"code": -1, "msg": f"proxy: {e}"}).encode()
            self.send_response(502)
            self._cors()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    def log_message(self, fmt, *args):
        print("[proxy]", args[0] if args else fmt, flush=True)


if __name__ == "__main__":
    print(f"CORS proxy on http://127.0.0.1:{PORT}  →  {UPSTREAM}")
    print("网页版 BASE 填 http://127.0.0.1:8787 即可")
    with socketserver.TCPServer(("127.0.0.1", PORT), H) as s:
        s.allow_reuse_address = True
        s.serve_forever()

"""生产静态服务器 + /api 反向代理。

穿透把所有请求转发到 5667，本服务器负责：
  - /api/*  转发到后端 127.0.0.1:8000（保留 method/query/body/Authorization）
  - 其余    提供 dist/build/h5 下的生产构建静态文件
"""
import http.server
import socketserver
import urllib.request
import urllib.error

BACKEND = "http://127.0.0.1:8000"
DIST_DIR = "F:/eclass/frontend/dist/build/h5"
PORT = 5667


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIST_DIR, **kwargs)

    def do_GET(self):
        if self.path.startswith("/api/"):
            self._proxy("GET")
            return
        super().do_GET()

    def do_POST(self):
        self._route_write("POST")

    def do_PUT(self):
        self._route_write("PUT")

    def do_PATCH(self):
        self._route_write("PATCH")

    def do_DELETE(self):
        self._route_write("DELETE")

    def _route_write(self, method: str) -> None:
        if self.path.startswith("/api/"):
            self._proxy(method)
            return
        self.send_error(405, "Method Not Allowed")

    def _proxy(self, method: str) -> None:
        try:
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length else None
            req = urllib.request.Request(BACKEND + self.path, data=body, method=method)
            req.add_header("Content-Type", self.headers.get("Content-Type", "application/json"))
            auth = self.headers.get("Authorization")
            if auth:
                req.add_header("Authorization", auth)
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = resp.read()
                self.send_response(resp.status)
                self.send_header("Content-Type", resp.headers.get("Content-Type", "application/json"))
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
        except urllib.error.HTTPError as exc:
            data = exc.read()
            self.send_response(exc.code)
            self.send_header("Content-Type", exc.headers.get("Content-Type", "application/json"))
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except Exception as exc:  # backend unreachable
            payload = f'{{"detail":"proxy error: {exc}"}}'.encode()
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)


class ThreadingServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


if __name__ == "__main__":
    print(f"Serving {DIST_DIR} + /api -> {BACKEND} on 0.0.0.0:{PORT}")
    ThreadingServer(("0.0.0.0", PORT), Handler).serve_forever()

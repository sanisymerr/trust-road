"""Serve the exported dashboard on Render using Python's standard library.

Copy this file as serve.py beside dashboard/index.html and run: python serve.py
Optional local override: SDG3_DASHBOARD_DIR=/absolute/path/to/dashboard
"""

from datetime import timezone
from email.utils import formatdate, parsedate_to_datetime
from functools import lru_cache
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit
import gzip
import mimetypes
import os
import signal


DASHBOARD_ROOT = Path(
    os.environ.get("SDG3_DASHBOARD_DIR", str(Path(__file__).resolve().parent / "dashboard"))
).resolve()
INDEX = DASHBOARD_ROOT / "index.html"
ALLOWED_ASSETS = {".js", ".css", ".json", ".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif", ".ico", ".woff", ".woff2", ".ttf"}
TEXT_TYPES = {"text/html", "text/css", "text/javascript", "application/javascript", "application/json", "image/svg+xml"}


def wants_gzip(header):
    for item in header.lower().split(","):
        fields = [part.strip() for part in item.split(";")]
        if fields[0] != "gzip":
            continue
        quality = 1.0
        for field in fields[1:]:
            if field.startswith("q="):
                try:
                    quality = float(field[2:])
                except ValueError:
                    quality = 0.0
        return quality > 0
    return False


@lru_cache(maxsize=32)
def asset_bytes(path, modified_ns, size, compressed):
    content = Path(path).read_bytes()
    return gzip.compress(content, compresslevel=6) if compressed else content


class DashboardHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "SDG3Dashboard"
    sys_version = ""

    def common_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header("X-Frame-Options", "DENY")

    def plain(self, status, text, head=False):
        payload = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.common_headers()
        self.end_headers()
        if not head:
            self.wfile.write(payload)

    def requested_asset(self, path):
        # The project root, report, source data, and template are never served.
        if path.startswith("/dashboard/"):
            path = path[len("/dashboard"):]
        if path in {"/", "/index.html"}:
            return INDEX
        parts = path.lstrip("/").split("/")
        if any(part in {"", ".", ".."} or part.startswith(".") for part in parts):
            return None
        candidate = (DASHBOARD_ROOT / Path(*parts)).resolve()
        if not candidate.is_relative_to(DASHBOARD_ROOT):
            return None
        if candidate.suffix.lower() not in ALLOWED_ASSETS or not candidate.is_file():
            return None
        return candidate

    def serve(self, head=False):
        try:
            path = unquote(urlsplit(self.path).path)
        except (ValueError, UnicodeError):
            self.plain(400, "Invalid URL\n", head)
            return
        if path in {"/_stcore/health", "/health"}:
            healthy = INDEX.is_file() and INDEX.stat().st_size > 0
            self.plain(200 if healthy else 503, "ok\n" if healthy else "dashboard unavailable\n", head)
            return
        if "\x00" in path or "\\" in path:
            self.plain(404, "Not found\n", head)
            return
        asset = self.requested_asset(path)
        if asset is None or not asset.is_file():
            self.plain(404, "Not found\n", head)
            return
        stat = asset.stat()
        mime = "text/html" if asset == INDEX else mimetypes.guess_type(asset.name)[0] or "application/octet-stream"
        if asset.suffix.lower() == ".js":
            mime = "text/javascript"
        compressed = mime in TEXT_TYPES and stat.st_size >= 1024 and wants_gzip(self.headers.get("Accept-Encoding", ""))
        etag = f'W/"{stat.st_mtime_ns:x}-{stat.st_size:x}{"-gz" if compressed else ""}"'
        conditional = self.headers.get("If-None-Match")
        not_modified = conditional is not None and (conditional.strip() == "*" or etag in [v.strip() for v in conditional.split(",")])
        if conditional is None and self.headers.get("If-Modified-Since"):
            try:
                date = parsedate_to_datetime(self.headers["If-Modified-Since"])
                if date.tzinfo is None:
                    date = date.replace(tzinfo=timezone.utc)
                not_modified = int(stat.st_mtime) <= int(date.timestamp())
            except (TypeError, ValueError, OverflowError):
                pass
        payload = b"" if not_modified else asset_bytes(str(asset), stat.st_mtime_ns, stat.st_size, compressed)
        self.send_response(304 if not_modified else 200)
        content_type = mime + "; charset=utf-8" if mime in TEXT_TYPES else mime
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-cache" if asset == INDEX else "public, max-age=3600")
        self.send_header("ETag", etag)
        self.send_header("Last-Modified", formatdate(stat.st_mtime, usegmt=True))
        self.send_header("Vary", "Accept-Encoding")
        if compressed:
            self.send_header("Content-Encoding", "gzip")
        if not not_modified:
            self.send_header("Content-Length", str(len(payload)))
        self.common_headers()
        self.end_headers()
        if not head and not not_modified:
            self.wfile.write(payload)

    def do_GET(self):
        self.serve()

    def do_HEAD(self):
        self.serve(head=True)

    def method_not_allowed(self):
        self.send_response(405)
        self.send_header("Allow", "GET, HEAD")
        self.send_header("Content-Length", "0")
        self.send_header("Cache-Control", "no-store")
        self.common_headers()
        self.end_headers()
        self.close_connection = True

    do_POST = do_PUT = do_PATCH = do_DELETE = do_OPTIONS = method_not_allowed


def main():
    if not INDEX.is_file() or INDEX.stat().st_size == 0:
        raise SystemExit(f"Exported dashboard not found: {INDEX}")
    try:
        port = int(os.environ.get("PORT", "10000"))
    except ValueError:
        raise SystemExit("PORT must be an integer")
    if not 1 <= port <= 65535:
        raise SystemExit("PORT must be between 1 and 65535")
    server = ThreadingHTTPServer(("0.0.0.0", port), DashboardHandler)
    server.daemon_threads = True

    def stop(signum, frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, stop)
    print(f"Serving dashboard on 0.0.0.0:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

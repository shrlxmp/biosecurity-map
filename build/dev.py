#!/usr/bin/env python3
"""Local preview that rebuilds and reloads as you edit.

    python build/dev.py              # http://localhost:8409
    python build/dev.py --port 9000

Whenever build/template.html, build/build.py, build/entries.csv or
build/logos.json changes, index.html is rebuilt and any open browser tab
reloads itself. Edit the template, never index.html.

The reload snippet is added only to the page as served here; the index.html
written to disk is exactly what build.py produces, so it is safe to commit.
"""
import argparse
import http.server
import os
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
WATCHED = ["template.html", "build.py", "entries.csv", "logos.json"]

# Bumped after every rebuild; open pages poll it and reload when it changes.
version = 0

RELOAD = b"""
<script>
(() => {
  let seen = null;
  setInterval(async () => {
    try {
      const v = await (await fetch("/__version", { cache: "no-store" })).text();
      if (seen !== null && v !== seen) location.reload();
      seen = v;
    } catch (e) {}
  }, 700);
})();
</script>
"""


def rebuild():
    global version
    result = subprocess.run([sys.executable, os.path.join(HERE, "build.py")],
                            capture_output=True, text=True)
    stamp = time.strftime("%H:%M:%S")
    if result.returncode == 0:
        version += 1
        print("[%s] rebuilt index.html" % stamp, flush=True)
    else:
        # Keep serving the last good page and show why the build failed.
        print("[%s] build failed:\n%s" % (stamp, result.stderr or result.stdout),
              flush=True)


def mtimes():
    return {name: os.path.getmtime(os.path.join(HERE, name))
            for name in WATCHED if os.path.exists(os.path.join(HERE, name))}


def watch():
    last = mtimes()
    while True:
        time.sleep(0.4)
        now = mtimes()
        if now != last:
            last = now
            rebuild()


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/__version":
            return self.send_text(str(version).encode(), "text/plain")
        if path in ("/", "/index.html"):
            with open(os.path.join(ROOT, "index.html"), "rb") as handle:
                page = handle.read()
            if b"</body>" in page:
                page = page.replace(b"</body>", RELOAD + b"</body>", 1)
            else:
                page += RELOAD
            return self.send_text(page, "text/html; charset=utf-8")
        return super().do_GET()

    def send_text(self, body, content_type):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass  # the poll would otherwise print a line every 0.7 s


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8409)
    args = parser.parse_args()

    rebuild()
    threading.Thread(target=watch, daemon=True).start()
    server = http.server.ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print("serving http://localhost:%d  (Ctrl+C to stop)" % args.port, flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

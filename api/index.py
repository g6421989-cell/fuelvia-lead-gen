"""
Vercel entry point — serves the Fuelvia dashboard HTML directly.
The full Flask app (app.py) cannot run on Vercel serverless because it uses
background threads, SQLite, and long-running SMTP sessions.
This handler just delivers the UI shell; the actual API calls it makes
(/api/dashboard-data etc.) will 404 on Vercel — that is expected.
For full functionality use Render (persistent server).
"""
import os
from http.server import BaseHTTPRequestHandler

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(ROOT, "templates", "dashboard_new.html")


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            with open(TEMPLATE, "r", encoding="utf-8") as f:
                html = f.read()
            body = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            msg = f"Error loading dashboard: {e}".encode()
            self.send_response(500)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)

    def do_POST(self):
        # API calls from the dashboard won't work on Vercel (needs persistent server)
        # Return a friendly JSON error so the UI doesn't show a raw error
        body = b'{"error":"API not available on Vercel. Run locally or on Render."}'
        self.send_response(503)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

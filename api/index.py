import sys
import os

# Add project root to path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

try:
    from app import app as handler
except Exception as e:
    # Fallback: serve the dashboard HTML directly if app fails to import
    from flask import Flask, render_template, send_from_directory
    handler = Flask(__name__, template_folder=os.path.join(ROOT, "templates"),
                    static_folder=os.path.join(ROOT, "static"))

    @handler.route("/", defaults={"path": ""})
    @handler.route("/<path:path>")
    def catch_all(path):
        try:
            return render_template("dashboard_new.html")
        except Exception:
            return f"""<!DOCTYPE html>
<html><head><title>Fuelvia</title>
<style>body{{font-family:sans-serif;background:#0a0a0a;color:#d4d4d4;
display:flex;align-items:center;justify-content:center;height:100vh;margin:0;}}
.box{{text-align:center;padding:40px;}}.title{{font-size:28px;color:#fff;margin-bottom:10px;}}
.sub{{color:#888;font-size:14px;}}</style></head>
<body><div class="box">
<div class="title">Fuelvia — Lead Generation</div>
<div class="sub">System loading... Import error: {str(e)[:120]}</div>
</div></body></html>"""

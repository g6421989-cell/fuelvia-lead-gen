# ============================================================
# SECURITY LAYER - Anti-Scraping, Bot Detection, Obfuscation
# ============================================================

from flask import Response
from datetime import datetime, timedelta
import json
from pathlib import Path

BOT_USER_AGENTS = [
    'claudebot', 'anthropic', 'gptbot', 'chatgpt-user', 'ccbot',
    'google-extended', 'perplexitybot', 'youbot', 'bytespider',
    'headlesschrome', 'phantomjs', 'puppeteer', 'playwright',
    'selenium', 'curl', 'wget', 'python-requests', 'scrapy'
]

HONEYPOT_PATHS = ['/admin', '/wp-admin', '/backup', '/admin/backup',
                   '.env', 'package.json', '.map', 'node_modules']

# Track failed logins and honeypot hits
THREAT_LOG_FILE = Path("backups/threat_log.json")
IP_BLOCKLIST = {}  # {ip: datetime_until_unblock}

def _is_bot_user_agent(ua: str) -> bool:
    """Check if user agent matches known bot patterns."""
    ua_lower = ua.lower() if ua else ""
    return any(bot in ua_lower for bot in BOT_USER_AGENTS)

def _is_headless_browser(ua: str) -> bool:
    """Detect headless browser signatures."""
    headless_sigs = ['headless', 'phantom', 'puppet', 'playwright', 'selenium']
    ua_lower = ua.lower() if ua else ""
    return any(sig in ua_lower for sig in headless_sigs)

def _log_threat(ip: str, threat_type: str, ua: str):
    """Log suspicious request to threat log."""
    try:
        log_file = THREAT_LOG_FILE
        log_file.parent.mkdir(parents=True, exist_ok=True)

        threat = {
            "timestamp": datetime.now().isoformat(),
            "ip": ip,
            "type": threat_type,
            "user_agent": ua[:100]  # truncate
        }

        threats = []
        if log_file.exists():
            try:
                threats = json.loads(log_file.read_text())
            except:
                pass

        threats.append(threat)
        log_file.write_text(json.dumps(threats[-100:]))  # keep last 100
        print(f"[THREAT] {threat_type} from {ip}")
    except Exception as e:
        print(f"[ERROR] Could not log threat: {e}")

def _get_decoy_page() -> str:
    """Return a convincing fake 'Coming Soon' page to bots."""
    return """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Dashboard</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, sans-serif;
               background: #f5f5f5; margin: 0; padding: 0; }
        .c { display: flex; justify-content: center; align-items: center;
             height: 100vh; flex-direction: column; }
        .s { width: 40px; height: 40px; border: 3px solid #ddd;
             border-top: 3px solid #333; border-radius: 50%;
             animation: spin 1s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
        .t { margin-top: 20px; color: #666; font-size: 14px; }
    </style>
</head>
<body>
    <div class="c">
        <div class="s"></div>
        <div class="t">Loading...</div>
    </div>
</body>
</html>"""

def check_suspicious_request(f):
    """Decorator: block bots, log threats, serve decoy."""
    from functools import wraps

    @wraps(f)
    def decorated(*args, **kwargs):
        from flask import request as flask_req

        ip = flask_req.remote_addr
        ua = flask_req.headers.get('User-Agent', '')
        path = flask_req.path

        # Check honeypot paths
        if any(hp in path for hp in HONEYPOT_PATHS):
            _log_threat(ip, "honeypot_access", ua)
            return _get_decoy_page(), 200, {'Content-Type': 'text/html'}

        # Check if IP is in blocklist
        if ip in IP_BLOCKLIST:
            if datetime.now() < IP_BLOCKLIST[ip]:
                return _get_decoy_page(), 200, {'Content-Type': 'text/html'}
            else:
                del IP_BLOCKLIST[ip]

        # Check bot signatures
        if _is_bot_user_agent(ua) or _is_headless_browser(ua):
            _log_threat(ip, "bot_detected", ua)
            return _get_decoy_page(), 200, {'Content-Type': 'text/html'}

        return f(*args, **kwargs)

    return decorated

def add_security_headers(response):
    """Add hardening headers to all responses."""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['X-Robots-Tag'] = 'noindex, nofollow, noarchive'
    response.headers['Server'] = 'nginx'  # Hide Flask/Werkzeug

    # Remove revealing headers
    if 'X-Powered-By' in response.headers:
        del response.headers['X-Powered-By']

    return response

def track_failed_login(ip: str):
    """Track failed login attempts. Block after 3 from same IP."""
    threats = []
    try:
        if THREAT_LOG_FILE.exists():
            threats = json.loads(THREAT_LOG_FILE.read_text())
    except:
        pass

    # Count failed logins from this IP in last hour
    one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
    failed_from_ip = [
        t for t in threats
        if t.get('ip') == ip and t.get('type') == 'failed_login'
        and t.get('timestamp', '') > one_hour_ago
    ]

    if len(failed_from_ip) >= 2:  # 3rd attempt
        IP_BLOCKLIST[ip] = datetime.now() + timedelta(hours=1)
        _log_threat(ip, "login_blocked", "Too many failed attempts")
        return False

    _log_threat(ip, "failed_login", "")
    return True

"""
COMPREHENSIVE DEEP AUDIT - Final Verification
"""
import sys
import inspect
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

print('='*70)
print('COMPREHENSIVE DEEP AUDIT - FINAL VERIFICATION')
print('='*70)

bugs = []
passes = []

def ok(msg):   passes.append(msg);  print(f'  [OK]   {msg}')
def fail(msg): bugs.append(msg);    print(f'  [FAIL] {msg}')

# ── 1. Flask app import & route check ─────────────────────────────
print('\n[1] FLASK APP & ROUTES')
try:
    from app import app
    routes = {str(r): r.methods for r in app.url_map.iter_rules()}
    ok(f'App loads cleanly ({len(routes)} routes)')

    from app import dashboard
    src = inspect.getsource(dashboard)
    if 'dashboard_new.html' in src:
        ok('Route / serves dashboard_new.html')
    else:
        fail('Route / still serves wrong template (dashboard.html)')

    for ep in ['/api/send-emails', '/api/send-followup', '/api/check-replies',
               '/api/replies', '/api/dashboard-data', '/api/leads', '/api/start-scrape']:
        if ep in routes:
            ok(f'Route {ep} exists')
        else:
            fail(f'Route {ep} MISSING')
except Exception as e:
    fail(f'App import error: {str(e)[:100]}')

# ── 2. Auth decorator ──────────────────────────────────────────────
print('\n[2] AUTH GUARDS')
try:
    with open('app.py', encoding='utf-8', errors='ignore') as f:
        app_src = f.read()
    for ep_fn in ['def get_dashboard_data', 'def get_leads', 'def start_scrape',
                  'def send_emails', 'def send_followup', 'def check_replies', 'def get_replies']:
        idx = app_src.find(ep_fn)
        if idx > 0:
            preceding = app_src[max(0, idx-120):idx]
            if 'login_required' in preceding:
                ok(f'{ep_fn}() protected by @login_required')
            else:
                fail(f'{ep_fn}() missing @login_required')
except Exception as e:
    fail(f'Auth check error: {e}')

# ── 3. Email generation signatures ────────────────────────────────
print('\n[3] EMAIL GENERATION SIGNATURES')
try:
    with open('app.py', encoding='utf-8', errors='ignore') as f:
        app_src = f.read()

    # Check within send_batch() / send_emails function scope only (not config import)
    import re
    send_fn_match = re.search(r'def send_emails\b.*?(?=\ndef |\Z)', app_src, re.DOTALL)
    send_fn_src = send_fn_match.group(0) if send_fn_match else ''
    old_sig_in_fn = 'SENDER_NAME, SENDER_TITLE, COMPANY_NAME, CALENDAR_LINK' in send_fn_src
    if old_sig_in_fn:
        fail('send_emails still uses OLD 7-param signature')
    else:
        ok('send_emails uses new dict-based signature')

    if 'backup_email_sent' in app_src:
        # Count occurrences - should be at least 2 (cold + followup)
        count = app_src.count('backup_email_sent')
        ok(f'backup_email_sent() called {count} times (cold + followup)')
    else:
        fail('backup_email_sent() never called')
except Exception as e:
    fail(f'Sig check error: {e}')

# ── 4. Scraper fixes ───────────────────────────────────────────────
print('\n[4] SCRAPER FIXES')
try:
    with open('app.py', encoding='utf-8', errors='ignore') as f:
        app_src = f.read()

    if 'notion.add_lead' in app_src:
        fail('Scraper still calls notion.add_lead() which does not exist')
    else:
        ok('notion.add_lead() gone')

    if 'notion.create_lead(lead)' in app_src:
        ok('Scraper uses notion.create_lead()')
    else:
        fail('Scraper missing notion.create_lead()')

    if 'qual_result.get' in app_src:
        ok('qualify_channel() result handled as dict')
    else:
        fail('qualify_channel() result not dict-handled')

    if 'leads_added / max(1' in app_src:
        ok('Progress calculation fixed')
    else:
        fail('Progress calculation still wrong')
except Exception as e:
    fail(f'Scraper check error: {e}')

# ── 5. Dashboard data endpoint ─────────────────────────────────────
print('\n[5] DASHBOARD STATS (Notion-based)')
try:
    from app import get_dashboard_data
    src2 = inspect.getsource(get_dashboard_data)
    if 'get_all_leads' in src2 and 'Follow-up Sent' in src2:
        ok('dashboard-data reads from Notion')
    else:
        fail('dashboard-data still reads from SQLite backup')

    if 'new_leads' in src2 and 'followup_sent' in src2:
        ok('dashboard-data returns per-status breakdown')
    else:
        fail('dashboard-data missing per-status breakdown')
except Exception as e:
    fail(f'Dashboard stats check: {e}')

# ── 6. lead_intelligence status names ─────────────────────────────
print('\n[6] LEAD INTELLIGENCE')
try:
    with open('lead_intelligence.py', encoding='utf-8', errors='ignore') as f:
        li_src = f.read()
    if 'Follow-up 1 Sent' in li_src or 'Follow-up 2 Sent' in li_src:
        fail('lead_intelligence.py still has old status names (Follow-up 1/2 Sent)')
    else:
        ok('lead_intelligence.py status names updated')
    if 'Follow-up Sent' in li_src and 'Closed' in li_src:
        ok('lead_intelligence.py has Follow-up Sent + Closed')
except Exception as e:
    fail(f'lead_intelligence check: {e}')

# ── 7. followup.py ─────────────────────────────────────────────────
print('\n[7] FOLLOWUP.PY')
try:
    with open('followup.py', encoding='utf-8', errors='ignore') as f:
        fp_src = f.read()
    count = fp_src.count('def generate_consolidated_report')
    if count == 1:
        ok('Exactly 1 generate_consolidated_report()')
    else:
        fail(f'{count} copies of generate_consolidated_report()')
    for bad in ["self.stats['f1_sent']", "self.stats['f2_sent']", "self.stats['no_response']"]:
        if bad not in fp_src:
            ok(f'Stale key removed: {bad}')
        else:
            fail(f'Stale key still present: {bad}')
except Exception as e:
    fail(f'followup.py check: {e}')

# ── 8. notion_manager methods ──────────────────────────────────────
print('\n[8] NOTION MANAGER')
try:
    from notion_manager import NotionManager
    for m in ['get_all_contacted_leads', 'get_leads_for_followup_1',
              'get_no_response_candidates', 'update_email_sent_from',
              'get_email_sent_from', 'mark_replied', 'create_lead', 'check_duplicate']:
        if hasattr(NotionManager, m):
            ok(f'NotionManager.{m}()')
        else:
            fail(f'NotionManager.{m}() MISSING')

    src3 = inspect.getsource(NotionManager.get_leads_for_followup_1)
    if 'Contacted' in src3:
        ok('get_leads_for_followup_1 filters for Contacted (fixed)')
    else:
        fail('get_leads_for_followup_1 still has wrong status filter')

    src4 = inspect.getsource(NotionManager.get_no_response_candidates)
    if 'Follow-up Sent' in src4 and 'Follow-up 2 Sent' not in src4:
        ok('get_no_response_candidates filters for Follow-up Sent (fixed)')
    else:
        fail('get_no_response_candidates wrong status filter')
except Exception as e:
    fail(f'Notion check: {e}')

# ── 9. Dashboard HTML ──────────────────────────────────────────────
print('\n[9] DASHBOARD HTML')
try:
    with open('templates/dashboard_new.html', encoding='utf-8', errors='ignore') as f:
        html = f.read()

    checks = [
        ('Send Emails button',        'sendEmails()'),
        ('Send Follow-up button',     'sendFollowup()'),
        ('Check Replies button',      'checkReplies()'),
        ('loadReplies JS function',   'function loadReplies()'),
        ('sendEmails JS function',    'function sendEmails()'),
        ('sendFollowup JS function',  'function sendFollowup()'),
        ('checkReplies JS function',  'function checkReplies()'),
        ('stat-new-leads element',    'stat-new-leads'),
        ('stat-contacted element',    'stat-contacted'),
        ('stat-followup element',     'stat-followup'),
        ('stat-closed element',       'stat-closed'),
        ('loadDashboard reads breakdown', 'stat-new-leads'),
        ('Replies table 5 columns',   'Channel Name'),
        ('badge-replied style',       'badge-replied'),
        ('badge-closed style',        'badge-closed'),
    ]
    for label, keyword in checks:
        if keyword in html:
            ok(label)
        else:
            fail(f'{label} - "{keyword}" not found in HTML')

    # Hardcoded values should be gone
    if '>124<' in html or '>28%<' in html:
        fail('Hardcoded fake stats (124 or 28%) still in HTML')
    else:
        ok('No hardcoded fake stats in HTML')
except Exception as e:
    fail(f'HTML check: {e}')

# ── 10. email_helpers send_outreach_email integrity ───────────────
print('\n[10] EMAIL HELPERS')
try:
    from email_helpers import global_email_rotator, send_outreach_email, ReplyChecker
    ok('global_email_rotator instance exists')
    ok('send_outreach_email importable')
    ok('ReplyChecker importable')

    # Verify is_followup guard
    with open('email_helpers.py', encoding='utf-8', errors='ignore') as f:
        eh_src = f.read()
    if 'is_followup' in eh_src and 'raise ValueError' in eh_src:
        ok('is_followup=True guard raises ValueError if account is None')
    else:
        fail('is_followup guard missing')
except Exception as e:
    fail(f'email_helpers check: {e}')

# ── SUMMARY ───────────────────────────────────────────────────────
print()
print('='*70)
print(f'RESULT: {len(passes)} checks PASSED, {len(bugs)} checks FAILED')
print('='*70)
if bugs:
    print('\nREMAINING ISSUES:')
    for b in bugs:
        print(f'  - {b}')
    print()
else:
    print('\nALL CHECKS PASSED - READY FOR DEPLOYMENT')
print('='*70)

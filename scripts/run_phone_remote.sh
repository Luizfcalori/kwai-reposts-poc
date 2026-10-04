#!/usr/bin/env bash
set -euo pipefail
umask 077
mkdir -p /tmp/kwai-remote
SERVER_PID=''
TUNNEL_PID=''
cleanup() {
  [ -z "$TUNNEL_PID" ] || kill "$TUNNEL_PID" 2>/dev/null || true
  [ -z "$SERVER_PID" ] || kill "$SERVER_PID" 2>/dev/null || true
  rm -rf artifacts /tmp/kwai-remote
}
trap cleanup EXIT
# Reuse the exact verified installation and legitimate Phone ClickableSpan click.
bash /tmp/run.sh > /tmp/kwai-remote/prelogin.log 2>&1
grep -q '^status=phone_field_visible$' artifacts/result.txt
rm -rf artifacts
adb logcat -c
env -u GH_TOKEN -u KWAI_REMOTE_EMAIL python3 scripts/kwai_phone_remote.py >/dev/null 2>&1 &
SERVER_PID=$!
for _ in $(seq 1 20); do
  curl -fsS http://127.0.0.1:6080/health >/dev/null 2>&1 && break
  sleep 1
done
test "$(curl -fsS http://127.0.0.1:6080/health)" = ready
/tmp/cloudflared tunnel --no-autoupdate --url http://127.0.0.1:6080 --allowed-mail "$KWAI_REMOTE_EMAIL" >/tmp/kwai-remote/tunnel.log 2>&1 &
TUNNEL_PID=$!
URL=''
for _ in $(seq 1 60); do
  URL="$(grep -Eo 'https://[-a-z0-9]+\.trycloudflare\.com' /tmp/kwai-remote/tunnel.log | tail -1 || true)"
  [ -n "$URL" ] && break
  kill -0 "$TUNNEL_PID"
  sleep 2
done
test -n "$URL"
export REMOTE_URL="$URL"
# Require an authentication redirect before announcing the session.
python3 - <<'PY'
import os,time,urllib.request,urllib.error,urllib.parse,json
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args): return None
opener=urllib.request.build_opener(NoRedirect)
verified=False
for _ in range(20):
    try:
        r=opener.open(os.environ['REMOTE_URL']+'/health',timeout=15)
        code,headers,body=r.status,r.headers,r.read(65536)
    except urllib.error.HTTPError as e:
        code,headers,body=e.code,e.headers,e.read(65536)
    except Exception:
        time.sleep(3); continue
    loc=headers.get('Location','').lower()
    dest=urllib.parse.urlparse(loc)
    if code in (301,302,303,307,308) and dest.scheme=='https' and dest.hostname=='login.trycloudflare.com' and dest.path=='/authorize':
        verified=True; break
    if body.strip()==b'ready':
        raise SystemExit('Access check failed: origin accessible without authentication.')
    time.sleep(3)
if not verified: raise SystemExit('Protected gateway not confirmed; session closed.')
payload={'state':'success','context':'kwai/phone-remote','description':'Phone form ready; email-protected session active for 25 minutes','target_url':os.environ['REMOTE_URL']}
req=urllib.request.Request('https://api.github.com/repos/'+os.environ['GITHUB_REPOSITORY']+'/statuses/'+os.environ['GITHUB_SHA'],data=json.dumps(payload).encode(),headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'Accept':'application/vnd.github+json','Content-Type':'application/json'},method='POST')
with urllib.request.urlopen(req,timeout=20) as response:
    assert response.status==201
print('PHONE_REMOTE_READY: email authentication verified; phone field visible.')
PY
echo "Protected session: $URL" >> "$GITHUB_STEP_SUMMARY"
# Keep the runner alive for direct user interaction; no account inspection or logs.
for _ in $(seq 1 150); do
  kill -0 "$SERVER_PID"
  kill -0 "$TUNNEL_PID"
  sleep 10
done

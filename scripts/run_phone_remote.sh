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
python3 - <<'PY'
from pathlib import Path
p=Path('/tmp/probe.py')
p.write_text(p.read_text().replace('time.sleep(8)', 'time.sleep(20)'))
PY
PHONE_READY=false
for attempt in 1 2 3; do
  if [ "$attempt" = 1 ]; then
    bash /tmp/run.sh > /tmp/kwai-remote/prelogin.log 2>&1 || true
  else
    sleep 10
    python3 /tmp/probe.py > /tmp/kwai-remote/prelogin.log 2>&1 || true
  fi
  if grep -q '^status=phone_field_visible$' artifacts/result.txt 2>/dev/null; then
    PHONE_READY=true
    break
  fi
  echo "prelogin_attempt=$attempt phone_field_not_ready"
done
if [ "$PHONE_READY" != true ]; then
  echo 'Phone form not reached; no remote access opened.'
  exit 7
fi
python3 scripts/kwai_select_brazil.py
rm -rf artifacts
adb logcat -c
# Bind the app-level password to the already configured private email secret without logging it.
python3 - <<'PY'
from pathlib import Path
import hashlib, os, re
p = Path('scripts/kwai_phone_remote.py')
s = p.read_text()
digest = hashlib.sha256(os.environ['KWAI_REMOTE_EMAIL'].encode('utf-8')).hexdigest()
new, count = re.subn(r'AUTH_HASH = "[0-9a-f]{64}"', f'AUTH_HASH = "{digest}"', s, count=1)
if count != 1:
    raise SystemExit('AUTH_HASH marker not found')
p.write_text(new)
PY
env -u GH_TOKEN -u KWAI_REMOTE_EMAIL python3 scripts/kwai_phone_remote.py >/dev/null 2>&1 &
SERVER_PID=$!
for _ in $(seq 1 20); do
  curl -fsS http://127.0.0.1:6080/health >/dev/null 2>&1 && break
  sleep 1
done
test "$(curl -fsS http://127.0.0.1:6080/health)" = ready
/tmp/cloudflared tunnel --no-autoupdate --url http://127.0.0.1:6080 >/tmp/kwai-remote/tunnel.log 2>&1 &
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
# Require the public tunnel to expose only the app-level login page before announcing the session.
python3 - <<'PY'
import os,time,urllib.request,json
verified=False
for _ in range(20):
    try:
        with urllib.request.urlopen(os.environ['REMOTE_URL']+'/',timeout=15) as r:
            body=r.read(65536)
            if r.status==200 and b'acesso protegido' in body:
                verified=True
                break
    except Exception:
        pass
    time.sleep(3)
if not verified:
    raise SystemExit('Protected app login page not confirmed; session closed.')
payload={'state':'success','context':'kwai/phone-remote','description':'Brazil +55 selected; app-password protected session ready','target_url':os.environ['REMOTE_URL']}
req=urllib.request.Request('https://api.github.com/repos/'+os.environ['GITHUB_REPOSITORY']+'/statuses/'+os.environ['GITHUB_SHA'],data=json.dumps(payload).encode(),headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'Accept':'application/vnd.github+json','Content-Type':'application/json'},method='POST')
with urllib.request.urlopen(req,timeout=20) as response:
    assert response.status==201
print('PHONE_REMOTE_READY: app-level authentication active; phone field visible.')
PY
echo "Protected session: $URL" >> "$GITHUB_STEP_SUMMARY"
# Keep the runner alive for direct user interaction; no account inspection or logs.
for _ in $(seq 1 150); do
  kill -0 "$SERVER_PID"
  kill -0 "$TUNNEL_PID"
  sleep 10
done

"""Reuse the validated workflow's setup without publishing its UI diagnostics."""
from pathlib import Path
import yaml

w = yaml.safe_load(Path('.github/workflows/kwai-api34-router-phone-proof-v2.yml').read_text())
setup = w['jobs']['router-phone-proof']['steps'][0]['run']
# This writes /tmp/probe.py and /tmp/run.sh; no execution or data from a login yet.

start = setup.index('docker run --rm')
end = setup.index('BUNDLE=', start)
setup = setup[:start] + """for attempt in 1 2 3; do
  timeout 150 docker run --rm --name kwai-phone-download -v "$PWD/apks:/output" ghcr.io/efforg/apkeep:stable \\
    -a 'com.kwai.kuaishou.video.live@13.8.30.646601' -d apk-pure \\
    -o 'acknowledge_dangers=true,arch=arm64-v8a' /output 2>&1 | tee artifacts/download.txt || true
  docker rm -f kwai-phone-download >/dev/null 2>&1 || true
  candidate="$(find apks -maxdepth 1 -type f -size +1M | head -n1)"
  if [ -n "$candidate" ] && unzip -tq "$candidate" >/dev/null 2>&1; then break; fi
  rm -f apks/*
  echo "bundle_download_retry=$attempt"
  sleep 5
done
""" + setup[end:]

Path('/tmp/prepare-phone.sh').write_text(setup)

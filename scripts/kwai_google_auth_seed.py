#!/usr/bin/env python3
import os
import re
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import kwai_ui_probe as p

ART = Path("artifacts/google-auth-seed")
ART.mkdir(parents=True, exist_ok=True)

EMAIL = os.environ.get("KWAI_GOOGLE_EMAIL", "")
PASSWORD = os.environ.get("KWAI_GOOGLE_PASSWORD", "")


def private_dump():
    remote = "/sdcard/kwai-private-auth.xml"
    p.adb("shell", "uiautomator", "dump", remote)
    fd, local = tempfile.mkstemp(prefix="kwai-auth-", suffix=".xml")
    os.close(fd)
    try:
        p.adb("pull", remote, local)
        root = ET.parse(local).getroot()
        texts = []
        for n in root.iter("node"):
            for key in ("text", "content-desc", "hint"):
                v = (n.attrib.get(key) or "").strip()
                if v and v not in texts:
                    texts.append(v)
        return root, texts
    finally:
        try:
            os.unlink(local)
        except OSError:
            pass
        p.adb("shell", "rm", "-f", remote)


def tap_matching(root, rx):
    pat = re.compile(rx, re.I)
    for n in root.iter("node"):
        label = " ".join(filter(None, [n.attrib.get("text", ""), n.attrib.get("content-desc", "")]))
        if pat.search(label):
            pt = p.parse_bounds(n.attrib.get("bounds", ""))
            if pt:
                p.adb("shell", "input", "tap", str(pt[0]), str(pt[1]))
                return True
    return False


def tap_edit(root, password=False):
    candidates = []
    for n in root.iter("node"):
        if "EditText" not in (n.attrib.get("class") or ""):
            continue
        is_pw = (n.attrib.get("password") or "").lower() == "true"
        candidates.append((n, is_pw))
    chosen = None
    if password:
        chosen = next((n for n, is_pw in candidates if is_pw), None)
    else:
        chosen = next((n for n, is_pw in candidates if not is_pw), None)
    if chosen is None and candidates:
        chosen = candidates[0][0]
    if chosen is None:
        return False
    pt = p.parse_bounds(chosen.attrib.get("bounds", ""))
    if not pt:
        return False
    p.adb("shell", "input", "tap", str(pt[0]), str(pt[1]))
    return True


def type_secret(value):
    # Secret travels over stdin, not as a process argument and is never printed.
    cp = subprocess.run(
        ["adb", "shell", "sh", "-c", 'IFS= read -r s; input text "$s"'],
        input=value + "\n",
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if cp.returncode:
        raise RuntimeError("secure ADB text injection failed")


def top_activity():
    _, out = p.adb("shell", "dumpsys", "activity", "activities")
    m = re.search(r"topResumedActivity=.*?\s([A-Za-z0-9._]+/[A-Za-z0-9._$]+)", out)
    return m.group(1) if m else ""


def stage(texts):
    joined = "\n".join(texts)
    if re.search(r"wrong password|incorrect password|password was changed|couldn.?t sign you in|could not sign you in", joined, re.I):
        return "credential_rejected"
    if re.search(r"2-step|2 step|verify it.?s you|verification|check your phone|tap yes|security code|try another way|captcha|recovery|confirm it.?s you", joined, re.I):
        return "challenge_required"
    if re.search(r"enter your password|password", joined, re.I):
        return "password"
    if re.search(r"email or phone|forgot email|use your google account|sign in - google accounts", joined, re.I):
        return "email"
    return "other"


def write_result(status, **extra):
    rows = {"status": status, **extra}
    text = "\n".join(f"{k}={v}" for k, v in rows.items()) + "\n"
    (ART / "result.txt").write_text(text, encoding="utf-8")
    print(text, end="")


def main():
    if not EMAIL or not PASSWORD:
        write_result("missing_secrets", email_present=bool(EMAIL), password_present=bool(PASSWORD))
        raise SystemExit(2)

    root, texts = private_dump()
    initial = stage(texts)
    if initial != "email":
        write_result("unexpected_initial_stage", initial_stage=initial, top_activity=top_activity())
        raise SystemExit(3)

    if not tap_edit(root, password=False):
        write_result("email_field_not_found", top_activity=top_activity())
        raise SystemExit(4)
    type_secret(EMAIL)
    time.sleep(1)
    root, _ = private_dump()
    if not tap_matching(root, r"^next$"):
        p.adb("shell", "input", "keyevent", "66")

    password_ready = False
    challenge = False
    rejected = False
    password_wait = 0
    for i in range(18):
        time.sleep(3)
        password_wait += 3
        root, texts = private_dump()
        s = stage(texts)
        if s == "password":
            password_ready = True
            break
        if s == "challenge_required":
            challenge = True
            break
        if s == "credential_rejected":
            rejected = True
            break

    if rejected:
        write_result("email_or_account_rejected", password_wait_seconds=password_wait, top_activity=top_activity())
        raise SystemExit(5)
    if challenge:
        write_result("challenge_required_before_password", password_wait_seconds=password_wait, top_activity=top_activity())
        raise SystemExit(6)
    if not password_ready:
        write_result("password_screen_not_reached", password_wait_seconds=password_wait, top_activity=top_activity())
        raise SystemExit(7)

    if not tap_edit(root, password=True):
        write_result("password_field_not_found", top_activity=top_activity())
        raise SystemExit(8)
    type_secret(PASSWORD)
    time.sleep(1)
    root, _ = private_dump()
    if not tap_matching(root, r"^next$"):
        p.adb("shell", "input", "keyevent", "66")

    final_status = "timeout"
    final_top = ""
    for _ in range(40):
        time.sleep(3)
        root, texts = private_dump()
        s = stage(texts)
        final_top = top_activity()
        if s == "credential_rejected":
            final_status = "credential_rejected"
            break
        if s == "challenge_required":
            final_status = "challenge_required"
            break
        # Success means Google auth has returned control to a Kwai activity that is no longer the SSO bridge.
        if final_top.startswith("com.kwai.video/") and not re.search(r"SignInHubActivity|TinyGoogleSSOActivity", final_top):
            final_status = "returned_to_kwai"
            break

    write_result(
        final_status,
        password_screen_reached=True,
        top_activity=final_top,
        credentials_logged=False,
        post_credential_screenshot_saved=False,
    )
    if final_status != "returned_to_kwai":
        raise SystemExit(10)


if __name__ == "__main__":
    main()

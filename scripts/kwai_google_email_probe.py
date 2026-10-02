#!/usr/bin/env python3
import os
import pathlib
import re
import subprocess
import time
import xml.etree.ElementTree as ET

RESULT = pathlib.Path("artifacts/google-auth-result.txt")
RESULT.parent.mkdir(parents=True, exist_ok=True)
REMOTE_XML = "/sdcard/kwai-google-auth.xml"
LOCAL_XML = "/tmp/kwai-google-auth.xml"


def adb(*args):
    return subprocess.run(["adb", *args], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def parse_bounds(value):
    m = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", value or "")
    if not m:
        return None
    x1, y1, x2, y2 = map(int, m.groups())
    return (x1 + x2) // 2, (y1 + y2) // 2


def dump_root():
    adb("shell", "uiautomator", "dump", REMOTE_XML)
    adb("pull", REMOTE_XML, LOCAL_XML)
    try:
        return ET.parse(LOCAL_XML).getroot()
    except Exception:
        return None


def texts(root):
    out = []
    if root is None:
        return out
    for node in root.iter("node"):
        for key in ("text", "content-desc"):
            value = (node.attrib.get(key) or "").strip()
            if value and value not in out:
                out.append(value)
    return out


def tap_label(root, pattern):
    if root is None:
        return False
    rx = re.compile(pattern, re.I)
    for node in root.iter("node"):
        label = " ".join(filter(None, [node.attrib.get("text", ""), node.attrib.get("content-desc", "")])).strip()
        if rx.search(label):
            point = parse_bounds(node.attrib.get("bounds", ""))
            if point:
                adb("shell", "input", "tap", str(point[0]), str(point[1]))
                return True
    return False


def tap_first_editable(root):
    if root is None:
        return False
    for node in root.iter("node"):
        if node.attrib.get("class") == "android.widget.EditText" or node.attrib.get("clickable") == "true" and re.search(
            r"email|phone|e-mail", " ".join([node.attrib.get("text", ""), node.attrib.get("content-desc", ""), node.attrib.get("hint", "")]), re.I
        ):
            point = parse_bounds(node.attrib.get("bounds", ""))
            if point:
                adb("shell", "input", "tap", str(point[0]), str(point[1]))
                return True
    return False


def classify(values):
    joined = "\n".join(values)
    checks = [
        ("password_prompt", r"enter your password|password|show password"),
        ("phone_approval", r"check your phone|tap yes|sent a notification|google prompt|confirm on your phone"),
        ("passkey", r"passkey|use your screen lock|use another device"),
        ("two_step", r"2-step verification|two-step verification|verification code|enter the code|authenticator"),
        ("verify_identity", r"verify it.?s you|confirm it.?s you|verify your identity|try another way"),
        ("captcha", r"captcha|prove you.?re not a robot|verify you.?re human"),
        ("blocked", r"couldn.?t sign you in|this browser or app may not be secure|something went wrong|there was a problem"),
        ("account_consent", r"continue to kwai|kwai wants to access|allow|choose what kwai can access"),
    ]
    for state, pattern in checks:
        if re.search(pattern, joined, re.I):
            return state
    return "other"


def save_result(**items):
    RESULT.write_text("\n".join(f"{k}={v}" for k, v in items.items()) + "\n", encoding="utf-8")
    print({k: v for k, v in items.items() if k != "email"})


def main():
    email = os.environ.get("GOOGLE_EMAIL", "").strip()
    if not email:
        save_result(secret_present=False, auth_state="missing_google_email_secret")
        raise SystemExit("GOOGLE_EMAIL secret is missing")

    root = dump_root()
    current = texts(root)
    if not re.search(r"Sign in|Google", "\n".join(current), re.I):
        save_result(secret_present=True, auth_state="google_signin_screen_missing")
        raise SystemExit("Google sign-in screen is not present")

    if not tap_first_editable(root):
        save_result(secret_present=True, auth_state="email_field_not_found")
        raise SystemExit("Email field was not found")

    adb("shell", "input", "text", email)
    time.sleep(1)
    root = dump_root()
    if not tap_label(root, r"^Next$"):
        save_result(secret_present=True, auth_state="next_button_not_found")
        raise SystemExit("Next button was not found")

    state = "other"
    waited = 0
    for _ in range(12):
        time.sleep(5)
        waited += 5
        root = dump_root()
        state = classify(texts(root))
        if state != "other":
            break

    save_result(
        secret_present=True,
        email_submitted=True,
        auth_state=state,
        wait_seconds=waited,
    )

    # Intentionally stop here. No password, OTP, passkey, approval action, screenshot,
    # UI text dump, account token, cookie, or session data is captured or printed.


if __name__ == "__main__":
    main()

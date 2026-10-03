#!/usr/bin/env python3
import os
import pathlib
import re
import subprocess
import time
import xml.etree.ElementTree as ET

ART = pathlib.Path("artifacts/auth-bootstrap")
ART.mkdir(parents=True, exist_ok=True)

EMAIL = os.environ.get("KWAI_GOOGLE_EMAIL", "")
PASSWORD = os.environ.get("KWAI_GOOGLE_PASSWORD", "")


def adb(*args, check=False):
    return subprocess.run(["adb", *args], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=check)


def parse_bounds(value):
    m = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", value or "")
    if not m:
        return None
    x1, y1, x2, y2 = map(int, m.groups())
    return (x1 + x2) // 2, (y1 + y2) // 2


def dump(tag):
    remote = "/sdcard/kwai-auth-bootstrap.xml"
    adb("shell", "uiautomator", "dump", remote)
    xml_path = ART / f"{tag}.xml"
    adb("pull", remote, str(xml_path))
    with open(ART / f"{tag}.png", "wb") as f:
        subprocess.run(["adb", "exec-out", "screencap", "-p"], stdout=f, stderr=subprocess.DEVNULL)
    try:
        root = ET.parse(xml_path).getroot()
    except Exception:
        root = None
    texts = []
    if root is not None:
        for node in root.iter("node"):
            for key in ("text", "content-desc", "hint"):
                value = (node.attrib.get(key) or "").strip()
                if value and value not in texts:
                    texts.append(value)
    (ART / f"{tag}.txt").write_text("\n".join(texts), encoding="utf-8")
    return root, texts


def labels(root):
    if root is None:
        return []
    out = []
    for node in root.iter("node"):
        label = " ".join(filter(None, [
            node.attrib.get("text", ""),
            node.attrib.get("content-desc", ""),
            node.attrib.get("hint", ""),
        ])).strip()
        if label:
            out.append((node, label))
    return out


def tap(root, pattern):
    rx = re.compile(pattern, re.I)
    for node, label in labels(root):
        if rx.search(label):
            point = parse_bounds(node.attrib.get("bounds", ""))
            if point:
                adb("shell", "input", "tap", str(point[0]), str(point[1]))
                return True
    return False


def focus_edit(root, patterns):
    regexes = [re.compile(p, re.I) for p in patterns]
    if root is None:
        return False
    candidates = []
    for node in root.iter("node"):
        clazz = node.attrib.get("class", "")
        label = " ".join(filter(None, [
            node.attrib.get("text", ""),
            node.attrib.get("content-desc", ""),
            node.attrib.get("hint", ""),
        ])).strip()
        if "EditText" in clazz:
            candidates.append((node, label))
    for node, label in candidates:
        if any(rx.search(label) for rx in regexes):
            point = parse_bounds(node.attrib.get("bounds", ""))
            if point:
                adb("shell", "input", "tap", str(point[0]), str(point[1]))
                return True
    if candidates:
        point = parse_bounds(candidates[0][0].attrib.get("bounds", ""))
        if point:
            adb("shell", "input", "tap", str(point[0]), str(point[1]))
            return True
    return False


def adb_input_secret(value):
    # subprocess argument list avoids host-shell interpolation. Android input uses %s for spaces.
    encoded = value.replace("%", "%25").replace(" ", "%s")
    adb("shell", "input", "text", encoded)


def classify(texts):
    joined = "\n".join(texts)
    if re.search(r"Welcome to Kwai|Continue with Google", joined, re.I):
        return "kwai_login"
    if re.search(r"Email or phone|Forgot email\?|Create account", joined, re.I):
        return "google_email"
    if re.search(r"Enter your password|Password", joined, re.I):
        return "google_password"
    if re.search(r"2-Step Verification|Verify it.?s you|Check your phone|Get a verification code|Enter the code|security key|passkey", joined, re.I):
        return "google_challenge"
    if re.search(r"Choose an account|Use another account", joined, re.I):
        return "google_account_chooser"
    if re.search(r"Home|Following|For You|Profile|Discover", joined, re.I) and not re.search(r"Sign in", joined, re.I):
        return "kwai_authenticated"
    if re.search(r"Couldn't sign you in|wrong password|Try again|Something went wrong|There was a problem", joined, re.I):
        return "auth_error"
    return "other"


def write_result(**values):
    pathlib.Path("artifacts/auth-bootstrap-result.txt").write_text(
        "\n".join(f"{k}={v}" for k, v in values.items()) + "\n",
        encoding="utf-8",
    )
    print(values)


def wait_state(tag_prefix, accepted, attempts=18, delay=5):
    last_state = "other"
    last_texts = []
    for i in range(1, attempts + 1):
        time.sleep(delay)
        root, texts = dump(f"{tag_prefix}-{i:02d}")
        state = classify(texts)
        print(f"state={state} wait={i * delay}s")
        last_state, last_texts = state, texts
        if state in accepted:
            return root, texts, state, i * delay
    return root, last_texts, last_state, attempts * delay


def main():
    if not EMAIL or not PASSWORD:
        write_result(status="secrets_missing", email_present=bool(EMAIL), password_present=bool(PASSWORD))
        raise SystemExit("Required GitHub Secrets KWAI_GOOGLE_EMAIL and KWAI_GOOGLE_PASSWORD are not configured")

    root, texts = dump("01-start")
    state = classify(texts)

    if state == "kwai_login":
        if not tap(root, r"^Continue with Google$"):
            write_result(status="continue_google_not_tappable", state=state)
            raise SystemExit("Continue with Google was not tappable")
        root, texts, state, _ = wait_state("02-google-entry", {"google_email", "google_account_chooser", "google_password", "google_challenge", "kwai_authenticated", "auth_error"})

    if state == "google_account_chooser":
        if tap(root, r"Use another account"):
            root, texts, state, _ = wait_state("03-use-another", {"google_email", "google_password", "google_challenge", "kwai_authenticated", "auth_error"})

    if state == "google_email":
        if not focus_edit(root, [r"Email", r"phone"]):
            write_result(status="email_field_not_found", state=state)
            raise SystemExit("Google email field not found")
        adb_input_secret(EMAIL)
        root, texts = dump("04-email-filled")
        if not tap(root, r"^Next$"):
            adb("shell", "input", "keyevent", "66")
        root, texts, state, _ = wait_state("05-after-email", {"google_password", "google_challenge", "kwai_authenticated", "auth_error"}, attempts=12)

    if state == "google_password":
        if not focus_edit(root, [r"password"]):
            write_result(status="password_field_not_found", state=state)
            raise SystemExit("Google password field not found")
        adb_input_secret(PASSWORD)
        root, texts = dump("06-password-filled")
        if not tap(root, r"^Next$"):
            adb("shell", "input", "keyevent", "66")
        root, texts, state, waited = wait_state(
            "07-after-password",
            {"google_challenge", "kwai_authenticated", "auth_error", "kwai_login"},
            attempts=24,
        )
    else:
        waited = 0

    if state == "google_challenge":
        write_result(status="manual_verification_required", final_state=state, wait_seconds=waited)
        raise SystemExit("Google requires a manual verification/2FA step; no attempt was made to bypass it")

    if state == "auth_error":
        write_result(status="authentication_error", final_state=state, wait_seconds=waited)
        raise SystemExit("Google authentication returned an error")

    if state == "kwai_authenticated":
        write_result(status="authenticated", final_state=state, kwai_pid=adb("shell", "pidof", "com.kwai.video").stdout.strip())
        return

    # Some successful Google flows return to Kwai before the home UI is fully rendered.
    root, texts, final_state, final_wait = wait_state(
        "08-final",
        {"kwai_authenticated", "google_challenge", "auth_error"},
        attempts=12,
    )
    if final_state == "kwai_authenticated":
        write_result(status="authenticated", final_state=final_state, wait_seconds=final_wait, kwai_pid=adb("shell", "pidof", "com.kwai.video").stdout.strip())
        return
    if final_state == "google_challenge":
        write_result(status="manual_verification_required", final_state=final_state, wait_seconds=final_wait)
        raise SystemExit("Google requires a manual verification/2FA step; no attempt was made to bypass it")

    write_result(status="not_authenticated", final_state=final_state, wait_seconds=final_wait)
    raise SystemExit(f"Authentication did not complete; final_state={final_state}")


if __name__ == "__main__":
    main()

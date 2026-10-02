#!/usr/bin/env python3
import pathlib
import re
import subprocess
import time
import xml.etree.ElementTree as ET

ART = pathlib.Path("artifacts/ui")
ART.mkdir(parents=True, exist_ok=True)


def run(*args, check=False):
    p = subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if check and p.returncode:
        raise RuntimeError(f"command failed {p.returncode}: {' '.join(args)}\n{p.stdout}")
    return p.returncode, p.stdout


def adb(*args, check=False):
    return run("adb", *args, check=check)


def screen_size():
    _, out = adb("shell", "wm", "size")
    m = re.search(r"(\d+)x(\d+)", out)
    return (int(m.group(1)), int(m.group(2))) if m else (1080, 2400)


def node_texts(root):
    vals = []
    for node in root.iter("node"):
        for key in ("text", "content-desc"):
            value = (node.attrib.get(key) or "").strip()
            if value and value not in vals:
                vals.append(value)
    return vals


def parse_bounds(value):
    m = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", value or "")
    if not m:
        return None
    x1, y1, x2, y2 = map(int, m.groups())
    return (x1 + x2) // 2, (y1 + y2) // 2


def dump(tag):
    remote = "/sdcard/kwai-probe.xml"
    adb("shell", "uiautomator", "dump", remote)
    xml_path = ART / f"{tag}.xml"
    adb("pull", remote, str(xml_path))
    with open(ART / f"{tag}.png", "wb") as f:
        p = subprocess.run(
            ["adb", "exec-out", "screencap", "-p"],
            stdout=f,
            stderr=subprocess.DEVNULL,
        )
        if p.returncode:
            raise RuntimeError("screencap failed")
    if not xml_path.exists():
        return None, []
    try:
        root = ET.parse(xml_path).getroot()
    except ET.ParseError:
        return None, []
    texts = node_texts(root)
    (ART / f"{tag}.txt").write_text("\n".join(texts), encoding="utf-8")
    return root, texts


def tap_node(root, matcher):
    if root is None:
        return False
    for node in root.iter("node"):
        label = " ".join(
            filter(None, [node.attrib.get("text", ""), node.attrib.get("content-desc", "")])
        ).strip()
        if matcher(label):
            point = parse_bounds(node.attrib.get("bounds", ""))
            if point:
                adb("shell", "input", "tap", str(point[0]), str(point[1]))
                return True
    return False


def contains(texts, pattern):
    rx = re.compile(pattern, re.I)
    return any(rx.search(t) for t in texts)


def dismiss_safe_system_overlays(round_no):
    root, texts = dump(f"overlay-{round_no}")
    joined = "\n".join(texts)
    if re.search(r"Pixel Launcher.*isn't responding", joined, re.I):
        if tap_node(root, lambda s: s.strip().lower() == "close app"):
            time.sleep(2)
            return True
    # Never accept account, purchase, publish, or destructive dialogs here.
    # Notification permission is granted with pm grant before launch; this is a fallback only.
    if contains(texts, r"send you notifications|notifications"):
        if tap_node(root, lambda s: s.strip().lower() in {"allow", "while using the app"}):
            time.sleep(2)
            return True
    return False


def main():
    w, h = screen_size()
    print(f"screen={w}x{h}")

    # Avoid first-run notification modal masking Kwai UI.
    adb("shell", "pm", "grant", "com.kwai.video", "android.permission.POST_NOTIFICATIONS")
    adb("shell", "am", "force-stop", "com.kwai.video")
    adb(
        "shell",
        "am",
        "start",
        "-n",
        "com.kwai.video/com.yxcorp.gifshow.tiny.TinyLaunchActivity",
    )
    time.sleep(12)

    for i in range(3):
        if not dismiss_safe_system_overlays(i):
            break

    root, texts = dump("01-first-clear-view")

    # First-run preference onboarding is 1/5 ... 5/5. Choosing a preference is harmless.
    for step in range(1, 8):
        joined = "\n".join(texts)
        if not (
            re.search(r"\b[1-5]/5\b", joined)
            or re.search(r"like or dislike|know you better", joined, re.I)
        ):
            break
        # Left preference button observed on first-run screen; relative coordinate survives density changes.
        adb("shell", "input", "tap", str(int(w * 0.27)), str(int(h * 0.93)))
        time.sleep(2)
        root, texts = dump(f"02-onboarding-{step}")

    root, texts = dump("03-after-onboarding")

    # Try a semantic profile tab first, then the conventional bottom-right profile position.
    profile_patterns = [r"^Profile$", r"^Me$", r"^Eu$", r"^Perfil$", r"^Account$", r"^Conta$"]
    clicked_profile = False
    for pat in profile_patterns:
        rx = re.compile(pat, re.I)
        if tap_node(root, lambda s, rx=rx: bool(rx.search(s))):
            clicked_profile = True
            break
    if not clicked_profile:
        adb("shell", "input", "tap", str(int(w * 0.92)), str(int(h * 0.965)))
    time.sleep(5)
    root, texts = dump("04-profile-attempt")

    # If a login entry point is present, open it but never enter credentials.
    login_labels = [
        r"^Log in$",
        r"^Login$",
        r"^Sign in$",
        r"^Entrar$",
        r"^Fazer login$",
        r"^Sign up or log in$",
        r"^Cadastre-se ou entre$",
        r"^Entrar ou cadastrar$",
    ]
    clicked_login = False
    for pat in login_labels:
        rx = re.compile(pat, re.I)
        if tap_node(root, lambda s, rx=rx: bool(rx.search(s))):
            clicked_login = True
            time.sleep(5)
            break

    root, texts = dump("05-final")
    joined = "\n".join(texts)
    login_screen = bool(
        re.search(
            r"phone|telefone|mobile|email|google|facebook|log in|login|sign in|entrar|verification|c[oó]digo",
            joined,
            re.I,
        )
    )

    result = {
        "clicked_profile": clicked_profile,
        "clicked_login": clicked_login,
        "login_screen_detected": login_screen,
        "pid": adb("shell", "pidof", "com.kwai.video")[1].strip(),
    }
    pathlib.Path("artifacts/ui-result.txt").write_text(
        "\n".join(f"{k}={v}" for k, v in result.items()) + "\n", encoding="utf-8"
    )
    print(result)

    # This probe is intentionally successful if Kwai remains alive even if UI labels change.
    # Evidence is uploaded for the next deterministic adjustment.
    if not result["pid"]:
        raise SystemExit("Kwai process stopped during safe UI probe")


if __name__ == "__main__":
    main()

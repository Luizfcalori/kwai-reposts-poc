#!/usr/bin/env python3
import pathlib
import re
import subprocess
import time
import xml.etree.ElementTree as ET

ART = pathlib.Path("artifacts/google")
ART.mkdir(parents=True, exist_ok=True)


def adb(*args):
    return subprocess.run(["adb", *args], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def parse_bounds(value):
    m = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", value or "")
    if not m:
        return None
    x1, y1, x2, y2 = map(int, m.groups())
    return (x1 + x2) // 2, (y1 + y2) // 2


def dump(tag):
    remote = "/sdcard/kwai-google-probe.xml"
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
            for key in ("text", "content-desc"):
                value = (node.attrib.get(key) or "").strip()
                if value and value not in texts:
                    texts.append(value)
    (ART / f"{tag}.txt").write_text("\n".join(texts), encoding="utf-8")
    return root, texts


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


def main():
    root, texts = dump("01-kwai-login")
    joined = "\n".join(texts)
    if not re.search(r"Welcome to Kwai|Continue with Google", joined, re.I):
        raise SystemExit("Kwai Google entry screen not present")

    clicked = tap_label(root, r"^Continue with Google$")
    if not clicked:
        raise SystemExit("Continue with Google button not tappable")

    time.sleep(10)
    root, texts = dump("02-google-screen")
    joined = "\n".join(texts)

    next_step = bool(re.search(
        r"Choose an account|Sign in|Google|Use another account|Add account|Email or phone|Couldn't sign you in|This browser or app may not be secure",
        joined,
        re.I,
    ))

    result = {
        "clicked_continue_with_google": clicked,
        "google_next_step_detected": next_step,
        "kwai_pid": adb("shell", "pidof", "com.kwai.video").stdout.strip(),
    }
    pathlib.Path("artifacts/google-result.txt").write_text(
        "\n".join(f"{k}={v}" for k, v in result.items()) + "\n",
        encoding="utf-8",
    )
    print(result)
    print("Visible Google-step text:")
    for text in texts:
        print(text)

    if not next_step:
        raise SystemExit("Google sign-in next step not detected")


if __name__ == "__main__":
    main()

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


def tap_resource_id(root, resource_id):
    if root is None:
        return False
    for node in root.iter("node"):
        if node.attrib.get("resource-id") == resource_id:
            point = parse_bounds(node.attrib.get("bounds", ""))
            if point:
                adb("shell", "input", "tap", str(point[0]), str(point[1]))
                return True
    return False


def contains(texts, pattern):
    rx = re.compile(pattern, re.I)
    return any(rx.search(t) for t in texts)


def onboarding_counter(texts):
    joined = "\n".join(texts)
    m = re.search(r"\b(\d+)/(5|12)\b", joined)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def tap_profile(root, w, h):
    profile_patterns = [r"^Profile$", r"^Me$", r"^Eu$", r"^Perfil$", r"^Account$", r"^Conta$"]
    for pat in profile_patterns:
        rx = re.compile(pat, re.I)
        if tap_node(root, lambda s, rx=rx: bool(rx.search(s))):
            return "semantic"
    adb("shell", "input", "tap", str(int(w * 0.92)), str(int(h * 0.955)))
    return "coordinate"


def dismiss_safe_system_overlays(round_no):
    root, texts = dump(f"overlay-{round_no}")
    joined = "\n".join(texts)
    if re.search(r"Pixel Launcher.*isn't responding", joined, re.I):
        if tap_node(root, lambda s: s.strip().lower() == "close app"):
            time.sleep(2)
            return True
    if contains(texts, r"send you notifications|notifications"):
        if tap_node(root, lambda s: s.strip().lower() in {"allow", "while using the app"}):
            time.sleep(2)
            return True
    return False


def swipe_to_next_onboarding(root, texts, w, h, step):
    before = onboarding_counter(texts)
    attempts = [
        (0.50, 0.79, 0.50, 0.18, 900),
        (0.38, 0.82, 0.38, 0.16, 1200),
        (0.62, 0.80, 0.62, 0.14, 700),
        (0.50, 0.86, 0.50, 0.12, 1500),
    ]

    for attempt, (x1, y1, x2, y2, duration) in enumerate(attempts, start=1):
        adb(
            "shell",
            "input",
            "touchscreen",
            "swipe",
            str(int(w * x1)),
            str(int(h * y1)),
            str(int(w * x2)),
            str(int(h * y2)),
            str(duration),
        )
        time.sleep(3)
        root, texts = dump(f"02-onboarding-{step:02d}-swipe-{attempt}")
        after = onboarding_counter(texts)
        print(f"onboarding swipe attempt={attempt} before={before} after={after} duration_ms={duration}")

        if before and after and after != before:
            return root, texts, True, attempt
        if before and not after:
            return root, texts, True, attempt
        if not contains(texts, r"swipe up to view the next video") and after != before:
            return root, texts, True, attempt

    return root, texts, False, len(attempts)


def run_preference_onboarding(root, texts, w, h):
    steps = 0
    swipe_failures = 0
    last_counter = onboarding_counter(texts)

    for step in range(1, 25):
        joined = "\n".join(texts)
        active = bool(
            re.search(r"\b\d+/(?:5|12)\b", joined)
            or re.search(r"choose like or dislike|know you better|swipe up to view the next video", joined, re.I)
        )
        if not active:
            break

        steps += 1
        counter = onboarding_counter(texts)
        print(f"onboarding step={step} counter={counter}")

        # This is only the pre-login preference selector; it does not act on an authenticated account.
        chose = tap_resource_id(root, "com.kwai.video:id/tiny_discovery_like_button")
        if not chose and re.search(r"choose like or dislike|know you better", joined, re.I):
            adb("shell", "input", "tap", str(int(w * 0.27)), str(int(h * 0.915)))
            chose = True

        if chose:
            time.sleep(1.5)
            root, texts = dump(f"02-onboarding-{step:02d}-chosen")

        joined = "\n".join(texts)
        if re.search(r"swipe up to view the next video", joined, re.I) or re.search(r"\b\d+/12\b", joined):
            root, texts, advanced, attempts = swipe_to_next_onboarding(root, texts, w, h, step)
            if not advanced:
                swipe_failures += 1
                print(f"onboarding swipe failed after {attempts} gesture variants; stopping instead of looping blindly")
                break
            last_counter = onboarding_counter(texts)
        elif chose:
            time.sleep(1)
            root, texts = dump(f"02-onboarding-{step:02d}-advanced")
            last_counter = onboarding_counter(texts)
        else:
            break

        # If the tutorial explicitly reaches its last card, allow the next loop to verify it cleared.
        if last_counter and last_counter[0] >= last_counter[1]:
            time.sleep(2)

    return root, texts, steps, swipe_failures, last_counter


def main():
    w, h = screen_size()
    print(f"screen={w}x{h}")

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
    root, texts, onboarding_steps, swipe_failures, final_onboarding_counter = run_preference_onboarding(root, texts, w, h)
    root, texts = dump("03-after-onboarding")

    profile_tap_method = tap_profile(root, w, h)
    time.sleep(5)
    root, texts = dump("04-profile-attempt")

    resource_seen = contains(texts, r"Resource downloading|access to all the features when it.s done")
    resource_completed = not resource_seen
    resource_wait_seconds = 0

    if resource_seen:
        print("Kwai profile resource download detected; waiting safely before retrying Profile.")
        for step in range(1, 13):
            time.sleep(10)
            resource_wait_seconds += 10
            root, texts = dump(f"04-resource-wait-{step:02d}")
            if not contains(texts, r"Resource downloading|access to all the features when it.s done"):
                resource_completed = True
                print(f"Kwai profile resource overlay cleared after {resource_wait_seconds}s.")
                break

        if not resource_completed:
            print("Resource overlay still present after 120s; hiding only the progress overlay and retrying Profile.")
            tap_node(root, lambda s: s.strip().lower() == "hide")
            time.sleep(3)
            root, texts = dump("04-resource-hidden")

        tap_profile(root, w, h)
        time.sleep(8)
        root, texts = dump("04-profile-retry")

    login_patterns = [
        r"^Log in$",
        r"^Login$",
        r"^Sign in$",
        r"^Entrar$",
        r"^Fazer login$",
        r"^Sign up or log in$",
        r"^Cadastre-se ou entre$",
        r"^Entrar ou cadastrar$",
        r"Log in to",
        r"Sign in to",
    ]
    clicked_login = False
    for pat in login_patterns:
        rx = re.compile(pat, re.I)
        if tap_node(root, lambda s, rx=rx: bool(rx.search(s))):
            clicked_login = True
            time.sleep(5)
            break

    root, texts = dump("05-final")
    joined = "\n".join(texts)
    login_screen = bool(
        re.search(
            r"phone|telefone|mobile|email|google|facebook|log in|login|sign in|entrar|verification|c[oó]digo|continue with",
            joined,
            re.I,
        )
    )

    result = {
        "onboarding_steps": onboarding_steps,
        "swipe_failures": swipe_failures,
        "final_onboarding_counter": final_onboarding_counter,
        "profile_tap_method": profile_tap_method,
        "resource_seen": resource_seen,
        "resource_completed": resource_completed,
        "resource_wait_seconds": resource_wait_seconds,
        "clicked_login": clicked_login,
        "login_screen_detected": login_screen,
        "pid": adb("shell", "pidof", "com.kwai.video")[1].strip(),
    }
    pathlib.Path("artifacts/ui-result.txt").write_text(
        "\n".join(f"{k}={v}" for k, v in result.items()) + "\n", encoding="utf-8"
    )
    print(result)

    if not result["pid"]:
        raise SystemExit("Kwai process stopped during safe UI probe")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import pathlib
import re
import subprocess
import time
import xml.etree.ElementTree as ET

PKG = "com.kwai.video"
ART = pathlib.Path("artifacts/manifest-phone-route")
ART.mkdir(parents=True, exist_ok=True)

ROUTES = [
    "ikwai://loginchannel",
    "ikwai://bind/phone",
    "kwai://bind/phone",
]


def run(*args, timeout=30):
    return subprocess.run(list(args), text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)


def adb(*args, timeout=30):
    return run("adb", *args, timeout=timeout)


def safe(value):
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value)


def dump(tag):
    remote = "/sdcard/kwai-manifest-phone-route.xml"
    adb("shell", "uiautomator", "dump", remote)
    xml_path = ART / f"{tag}.xml"
    adb("pull", remote, str(xml_path))
    with open(ART / f"{tag}.png", "wb") as f:
        subprocess.run(["adb", "exec-out", "screencap", "-p"], stdout=f, stderr=subprocess.DEVNULL)

    focus = adb("shell", "dumpsys", "window", "windows").stdout
    (ART / f"{tag}-window.txt").write_text(focus, encoding="utf-8")

    texts = []
    edits = []
    rows = []
    try:
        root = ET.parse(xml_path).getroot()
    except Exception:
        root = None

    if root is not None:
        for node in root.iter("node"):
            label = " ".join(filter(None, [
                node.attrib.get("text", ""),
                node.attrib.get("content-desc", ""),
                node.attrib.get("hint", ""),
            ])).strip()
            klass = node.attrib.get("class", "")
            if label and label not in texts:
                texts.append(label)
            if "EditText" in klass:
                edits.append(label)
            if label or "EditText" in klass or node.attrib.get("clickable") == "true":
                rows.append(" | ".join([
                    f"label={label}",
                    f"id={node.attrib.get('resource-id','')}",
                    f"class={klass}",
                    f"clickable={node.attrib.get('clickable','')}",
                    f"bounds={node.attrib.get('bounds','')}",
                ]))

    (ART / f"{tag}-texts.txt").write_text("\n".join(texts), encoding="utf-8")
    (ART / f"{tag}-nodes.txt").write_text("\n".join(rows), encoding="utf-8")
    return texts, edits, focus


def is_phone_number_screen(texts, edits):
    joined = "\n".join(texts)
    if re.search(r"phone number|mobile number|telefone|n[uú]mero de telefone|celular|country code|c[oó]digo do pa[ií]s|\+55", joined, re.I):
        return True
    return any(re.search(r"phone|mobile|telefone|celular|n[uú]mero", x or "", re.I) for x in edits)


def main():
    summary = []
    success = None

    for idx, route in enumerate(ROUTES, 1):
        tag = f"{idx:02d}-{safe(route)}"
        adb("shell", "am", "force-stop", PKG)
        time.sleep(1)
        cmd = adb(
            "shell", "am", "start", "-W",
            "-a", "android.intent.action.VIEW",
            "-c", "android.intent.category.BROWSABLE",
            "-d", route,
            PKG,
        )
        (ART / f"{tag}-start.txt").write_text(cmd.stdout, encoding="utf-8")
        time.sleep(7)
        texts, edits, focus = dump(tag)
        visible = is_phone_number_screen(texts, edits)
        focused = "\n".join(
            line.strip() for line in focus.splitlines()
            if "mCurrentFocus" in line or "mFocusedApp" in line or "topResumedActivity" in line
        )
        summary.append(
            f"route={route}\n"
            f"start_output={cmd.stdout.strip()}\n"
            f"focused={focused}\n"
            f"phone_number_screen={str(visible).lower()}\n"
            f"texts={' | '.join(texts[:25])}\n"
        )
        if visible:
            success = route
            break

    (ART / "result.txt").write_text(
        f"status={'phone_number_screen_reached' if success else 'not_reached'}\n"
        f"successful_route={success or 'none'}\n\n" + "\n---\n".join(summary),
        encoding="utf-8",
    )
    print((ART / "result.txt").read_text(encoding="utf-8"))
    if not success:
        raise SystemExit("New manifest-declared phone routes did not reach the phone-number entry screen; inspect UI evidence")


if __name__ == "__main__":
    main()

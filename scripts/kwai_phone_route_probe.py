#!/usr/bin/env python3
import pathlib
import re
import subprocess
import time
import xml.etree.ElementTree as ET

ART = pathlib.Path("artifacts/phone-route")
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
    remote = "/sdcard/kwai-phone-route.xml"
    adb("shell", "uiautomator", "dump", remote)
    xml_path = ART / f"{tag}.xml"
    adb("pull", remote, str(xml_path))
    with open(ART / f"{tag}.png", "wb") as f:
        subprocess.run(["adb", "exec-out", "screencap", "-p"], stdout=f, stderr=subprocess.DEVNULL)
    try:
        root = ET.parse(xml_path).getroot()
    except Exception:
        root = None
    rows = []
    texts = []
    if root is not None:
        for node in root.iter("node"):
            label = " ".join(filter(None, [
                node.attrib.get("text", ""),
                node.attrib.get("content-desc", ""),
                node.attrib.get("hint", ""),
            ])).strip()
            if label and label not in texts:
                texts.append(label)
            if label or node.attrib.get("clickable") == "true" or "EditText" in node.attrib.get("class", ""):
                rows.append(
                    " | ".join([
                        f"label={label}",
                        f"id={node.attrib.get('resource-id','')}",
                        f"class={node.attrib.get('class','')}",
                        f"clickable={node.attrib.get('clickable','')}",
                        f"bounds={node.attrib.get('bounds','')}",
                    ])
                )
    (ART / f"{tag}.txt").write_text("\n".join(texts), encoding="utf-8")
    (ART / f"{tag}-nodes.txt").write_text("\n".join(rows), encoding="utf-8")
    return root, texts


def label_of(node):
    return " ".join(filter(None, [
        node.attrib.get("text", ""), node.attrib.get("content-desc", ""), node.attrib.get("hint", "")
    ])).strip()


def tap_pattern(root, patterns):
    if root is None:
        return None
    regexes = [re.compile(p, re.I) for p in patterns]
    for node in root.iter("node"):
        label = label_of(node)
        if label and any(rx.search(label) for rx in regexes):
            point = parse_bounds(node.attrib.get("bounds", ""))
            if point:
                adb("shell", "input", "tap", str(point[0]), str(point[1]))
                return label
    return None


def has_phone_field(root, texts):
    joined = "\n".join(texts)
    if re.search(r"phone number|mobile number|telefone|n[uú]mero de telefone|celular", joined, re.I):
        return True
    if root is not None:
        edits = [n for n in root.iter("node") if "EditText" in n.attrib.get("class", "")]
        if edits:
            return True
    return False


def main():
    root, texts = dump("01-login-entry")
    if has_phone_field(root, texts):
        status = "phone_field_visible"
        clicked = ""
    else:
        clicked = tap_pattern(root, [
            r"phone", r"telefone", r"mobile", r"celular", r"n[uú]mero",
            r"other login", r"more login", r"more options", r"other methods",
            r"use another", r"log in with", r"sign in with",
        ]) or ""
        if clicked:
            time.sleep(5)
            root, texts = dump("02-after-route-tap")

        if not has_phone_field(root, texts):
            clicked2 = tap_pattern(root, [r"^Log in$", r"^Login$", r"^Sign in$", r"^Entrar$", r"^Fazer login$"])
            if clicked2:
                clicked = clicked or clicked2
                time.sleep(5)
                root, texts = dump("03-after-login-tap")

        status = "phone_field_visible" if has_phone_field(root, texts) else "phone_route_not_found"

    pathlib.Path("artifacts/phone-route-result.txt").write_text(
        f"status={status}\nroute_tap={clicked or 'none'}\n",
        encoding="utf-8",
    )
    print(f"status={status} route_tap={clicked or 'none'}")
    if status != "phone_field_visible":
        raise SystemExit("Phone login field was not reached; inspect safe UI evidence")


if __name__ == "__main__":
    main()

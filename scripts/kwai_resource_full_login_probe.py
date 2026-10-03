#!/usr/bin/env python3
import pathlib
import re
import time
import xml.etree.ElementTree as ET

import kwai_ui_probe as p

PKG = "com.kwai.video"
ART = pathlib.Path("artifacts/resource-full-login")
ART.mkdir(parents=True, exist_ok=True)


def capture_state(tag):
    root, texts = p.dump(tag)
    _, paths = p.adb("shell", "pm", "path", PKG)
    _, pkg = p.adb("shell", "dumpsys", "package", PKG)
    _, act = p.adb("shell", "dumpsys", "activity", "activities")
    (ART / f"{tag}-pm-path.txt").write_text(paths, encoding="utf-8")
    (ART / f"{tag}-package.txt").write_text(pkg, encoding="utf-8")
    (ART / f"{tag}-activities.txt").write_text(act, encoding="utf-8")
    return root, texts


def save_login_intent_state(tag):
    for cmd, name in [
        (("shell", "dumpsys", "activity", "activities"), "activities"),
        (("shell", "dumpsys", "activity", "top"), "activity-top"),
        (("shell", "dumpsys", "window", "windows"), "windows"),
        (("shell", "dumpsys", "package", PKG), "package"),
    ]:
        _, out = p.adb(*cmd)
        (ART / f"{tag}-{name}.txt").write_text(out, encoding="utf-8")


def phone_screen(root, texts):
    joined = "\n".join(texts)
    if re.search(r"phone number|mobile number|telefone|n[uú]mero de telefone|celular|country code|c[oó]digo do pa[ií]s|\+55", joined, re.I):
        return True
    if root is not None:
        for node in root.iter("node"):
            if "EditText" not in (node.attrib.get("class") or ""):
                continue
            label = " ".join([node.attrib.get("text", ""), node.attrib.get("content-desc", ""), node.attrib.get("hint", "")])
            if re.search(r"phone|mobile|telefone|celular|n[uú]mero", label, re.I):
                return True
    return False


def main():
    w, h = p.screen_size()
    p.adb("shell", "pm", "grant", PKG, "android.permission.POST_NOTIFICATIONS")
    p.adb("shell", "am", "force-stop", PKG)
    p.adb("shell", "logcat", "-c")
    p.adb("shell", "am", "start", "-n", f"{PKG}/com.yxcorp.gifshow.tiny.TinyLaunchActivity")
    time.sleep(12)

    for i in range(3):
        if not p.dismiss_safe_system_overlays(i):
            break

    root, texts = p.dump("01-first-clear-view")
    root, texts, onboarding_steps, swipe_failures, final_counter = p.run_onboarding(root, texts, w, h)
    root, texts = p.dump("03-after-onboarding")
    root, texts, clicked_start = p.finish_onboarding(root, texts, w, h)

    # Preserve the previously proven way through the slow-preparation prompt.
    root, texts, skipped_slow = p.skip_slow_loader(root, texts, w, h, "03c-after-slow-skip")

    profile_method = p.tap_profile(root, w, h)
    time.sleep(6)
    root, texts = capture_state("04-profile-before-resource-wait")

    resource_rx = r"Resource downloading|access to all the features when it.s done"
    resource_seen = p.contains(texts, resource_rx)
    resource_completed = not resource_seen
    waited = 0

    if resource_seen:
        # Do NOT hide the downloader while waiting. Give the runtime module four minutes.
        for step in range(1, 17):
            time.sleep(15)
            waited += 15
            root, texts = capture_state(f"04-resource-wait-{step:02d}")
            print(f"resource_wait={waited}s visible={p.contains(texts, resource_rx)}")
            if not p.contains(texts, resource_rx):
                resource_completed = True
                break

    # Capture app-owned module/download messages before navigating away.
    _, uid_line = p.adb("shell", "dumpsys", "package", PKG)
    m = re.search(r"userId=(\d+)", uid_line)
    uid = m.group(1) if m else ""
    if uid:
        _, logs = p.adb("logcat", "-d", "--uid", uid, "-t", "5000")
    else:
        _, logs = p.adb("logcat", "-d", "-t", "5000")
    (ART / "resource-logcat.txt").write_text(logs, encoding="utf-8")

    # If still blocked after the long wait, only hide the status panel; do not skip/cancel download.
    if p.contains(texts, resource_rx):
        hidden = p.tap_node(root, lambda s: s.strip().lower() == "hide")
        print(f"resource_panel_hidden={hidden}")
        time.sleep(3)
        root, texts = p.dump("04-resource-panel-hidden")

    clicked_login, root, texts = p.try_login_button(root, texts)
    fallback_method = "not_needed"
    fallback_attempts = []
    if not clicked_login and not p.is_login_screen(texts):
        root, texts, fallback_method, fallback_attempts = p.auth_fallback(root, texts, w, h)

    root, texts = p.dump("05-final")
    save_login_intent_state("05-final")
    reached_phone = phone_screen(root, texts)
    tiny_login = "TinyLoginActivity" in (ART / "05-final-activities.txt").read_text(encoding="utf-8", errors="ignore")

    result = {
        "onboarding_steps": onboarding_steps,
        "swipe_failures": swipe_failures,
        "final_onboarding_counter": final_counter,
        "clicked_start_now": clicked_start,
        "skipped_slow_preparation": skipped_slow,
        "profile_tap_method": profile_method,
        "resource_seen": resource_seen,
        "resource_completed": resource_completed,
        "resource_wait_seconds": waited,
        "clicked_login": clicked_login,
        "fallback_method": fallback_method,
        "fallback_attempts": ";".join(fallback_attempts),
        "tiny_login_activity_visible": tiny_login,
        "phone_number_screen_reached": reached_phone,
    }
    text = "\n".join(f"{k}={v}" for k, v in result.items()) + "\n"
    (ART / "result.txt").write_text(text, encoding="utf-8")
    print(text)

    # Success condition is deliberately only visual proof of the number-entry screen.
    if not reached_phone:
        raise SystemExit("Phone-number entry screen not reached; evidence captured for next correction")


if __name__ == "__main__":
    main()

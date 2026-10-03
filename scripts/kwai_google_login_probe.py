#!/usr/bin/env python3
import pathlib
import re
import time

import kwai_ui_probe as p

PKG = "com.kwai.video"
ART = pathlib.Path("artifacts/google-login")
ART.mkdir(parents=True, exist_ok=True)


def capture(tag):
    root, texts = p.dump(tag)
    for cmd, name in [
        (("shell", "dumpsys", "activity", "activities"), "activities"),
        (("shell", "dumpsys", "activity", "top"), "activity-top"),
        (("shell", "dumpsys", "window", "windows"), "windows"),
    ]:
        _, out = p.adb(*cmd)
        (ART / f"{tag}-{name}.txt").write_text(out, encoding="utf-8")
    return root, texts


def google_surface(texts, diag):
    joined = "\n".join(texts) + "\n" + diag
    return bool(re.search(
        r"choose an account|use another account|add account|sign in with google|"
        r"continue with google|TinyGoogleSSOActivity|SignInHubActivity|GoogleApiActivity|"
        r"MinuteMaidActivity|com\.google\.android\.gms.*auth|"
        r"com\.google\.android\.gms/.+signin|accounts\.google",
        joined,
        re.I,
    ))


def google_credential_ready(root, texts):
    joined = "\n".join(texts)
    if re.search(
        r"email or phone|email address|enter your email|use your google account|"
        r"forgot email|create account|choose an account|use another account",
        joined,
        re.I,
    ):
        return True
    if root is not None:
        for node in root.iter("node"):
            cls = node.attrib.get("class") or ""
            if "EditText" not in cls:
                continue
            label = " ".join([
                node.attrib.get("text", ""),
                node.attrib.get("content-desc", ""),
                node.attrib.get("hint", ""),
            ])
            if re.search(r"email|phone|google|account", label, re.I):
                return True
    return False


def read_diag(tag):
    parts = []
    for name in ("activities", "activity-top", "windows"):
        path = ART / f"{tag}-{name}.txt"
        if path.exists():
            parts.append(path.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(parts)


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
    root, texts = p.dump("02-after-onboarding")
    root, texts, clicked_start = p.finish_onboarding(root, texts, w, h)
    root, texts, skipped_slow = p.skip_slow_loader(root, texts, w, h, "03-after-slow-skip")

    profile_method = p.tap_profile(root, w, h)
    time.sleep(6)
    root, texts = p.dump("04-profile")

    if p.contains(texts, r"Resource downloading|access to all the features when it.s done"):
        for step in range(1, 9):
            time.sleep(15)
            root, texts = p.dump(f"04-resource-wait-{step:02d}")
            if not p.contains(texts, r"Resource downloading|access to all the features when it.s done"):
                break
        if p.contains(texts, r"Resource downloading|access to all the features when it.s done"):
            p.tap_node(root, lambda s: s.strip().lower() == "hide")
            time.sleep(3)
            root, texts = p.dump("04-resource-hidden")

    clicked_login, root, texts = p.try_login_button(root, texts)
    fallback_method = "not_needed"
    fallback_attempts = []
    if not clicked_login and not p.is_login_screen(texts):
        root, texts, fallback_method, fallback_attempts = p.auth_fallback(root, texts, w, h)

    root, texts = capture("05-login-screen")
    google_present = p.contains(texts, r"continue with google|google")

    clicked_google = p.tap_node(root, lambda s: bool(re.search(r"continue with google|^google$|sign in with google", s, re.I)))
    if not clicked_google and google_present:
        for node in root.iter("node") if root is not None else []:
            label = " ".join(filter(None, [node.attrib.get("text", ""), node.attrib.get("content-desc", "")]))
            if re.search(r"continue with google|google", label, re.I):
                point = p.parse_bounds(node.attrib.get("bounds", ""))
                if point:
                    p.adb("shell", "input", "tap", str(point[0]), str(point[1]))
                    clicked_google = True
                    break

    # First proof immediately after the click.
    time.sleep(10)
    root, texts = capture("06-after-google-click")
    reached_google = google_surface(texts, read_diag("06-after-google-click"))

    # Let the official Google add-account WebView finish loading. Do not type or tap anything here.
    credential_ready = google_credential_ready(root, texts)
    final_google_tag = "06-after-google-click"
    google_wait_seconds = 10
    for step in range(1, 13):
        if credential_ready:
            break
        time.sleep(10)
        google_wait_seconds += 10
        tag = f"07-google-ready-wait-{step:02d}"
        root, texts = capture(tag)
        final_google_tag = tag
        reached_google = reached_google or google_surface(texts, read_diag(tag))
        credential_ready = google_credential_ready(root, texts)
        print(f"google_wait={google_wait_seconds}s credential_ready={credential_ready} texts={texts[:20]}")

    _, logcat = p.adb("logcat", "-d", "-t", "5000")
    (ART / "logcat.txt").write_text(logcat, encoding="utf-8")
    final_text = "\n".join(texts)
    (ART / "final-google-visible-text.txt").write_text(final_text + "\n", encoding="utf-8")

    result = {
        "onboarding_steps": onboarding_steps,
        "swipe_failures": swipe_failures,
        "final_onboarding_counter": final_counter,
        "clicked_start_now": clicked_start,
        "skipped_slow_preparation": skipped_slow,
        "profile_tap_method": profile_method,
        "clicked_login": clicked_login,
        "fallback_method": fallback_method,
        "fallback_attempts": ";".join(fallback_attempts),
        "google_option_present": google_present,
        "clicked_google": clicked_google,
        "google_auth_surface_reached": reached_google,
        "google_credential_entry_ready": credential_ready,
        "google_wait_seconds": google_wait_seconds,
        "final_google_tag": final_google_tag,
        "final_google_visible_text": " | ".join(texts[:30]),
    }
    text = "\n".join(f"{k}={v}" for k, v in result.items()) + "\n"
    (ART / "result.txt").write_text(text, encoding="utf-8")
    print(text)

    # Deliberately stop before entering any Google account, email, password, OTP, or other credential.
    if not reached_google:
        raise SystemExit("Google authentication surface was not reached; evidence captured")
    if not credential_ready:
        raise SystemExit("Google auth opened, but credential-entry controls did not finish loading; evidence captured")


if __name__ == "__main__":
    main()

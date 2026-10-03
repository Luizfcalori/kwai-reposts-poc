#!/usr/bin/env python3
import pathlib
import re
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import kwai_ui_probe as probe

ART = pathlib.Path("artifacts/resource-phone")
ART.mkdir(parents=True, exist_ok=True)

RESOURCE_RX = re.compile(r"resource downloading|access to all the features|internet.?s a bit slow|hang in there|prepar", re.I)
PHONE_RX = re.compile(
    r"phone number|mobile number|n[uú]mero de telefone|n[uú]mero do celular|country code|"
    r"c[oó]digo do pa[ií]s|get code|send code|verification code|c[oó]digo de verifica|sms code",
    re.I,
)


def dump(tag):
    root, texts = probe.dump(tag)
    (ART / f"{tag}.txt").write_text("\n".join(texts), encoding="utf-8")
    return root, texts


def has_resource(texts):
    return bool(RESOURCE_RX.search("\n".join(texts)))


def has_phone(texts):
    return bool(PHONE_RX.search("\n".join(texts)))


def wait_resource(root, texts, prefix, max_seconds=420):
    elapsed = 0
    history = []
    clear_rounds = 0
    while True:
        resource = has_resource(texts)
        history.append(f"{elapsed}s resource={resource} texts={' | '.join(texts[:14])}")
        print(history[-1])
        if not resource:
            clear_rounds += 1
            if clear_rounds >= 2:
                return root, texts, True, elapsed, history
        else:
            clear_rounds = 0
        if elapsed >= max_seconds:
            return root, texts, False, elapsed, history
        time.sleep(15)
        elapsed += 15
        root, texts = dump(f"{prefix}-{elapsed:03d}s")


def main():
    w, h = probe.screen_size()
    probe.adb("shell", "pm", "grant", "com.kwai.video", "android.permission.POST_NOTIFICATIONS")
    probe.adb("shell", "am", "force-stop", "com.kwai.video")
    probe.adb("shell", "am", "start", "-n", "com.kwai.video/com.yxcorp.gifshow.tiny.TinyLaunchActivity")
    time.sleep(12)

    for i in range(3):
        if not probe.dismiss_safe_system_overlays(i):
            break

    root, texts = dump("01-first-clear-view")
    root, texts, onboarding_steps, swipe_failures, final_counter = probe.run_onboarding(root, texts, w, h)
    root, texts = dump("02-after-onboarding")
    root, texts, clicked_start_now = probe.finish_onboarding(root, texts, w, h)
    root, texts = dump("03-after-start-now")

    resource_seen = has_resource(texts)
    resource_completed = not resource_seen
    waited = 0
    history = []
    if resource_seen:
        root, texts, resource_completed, waited, history = wait_resource(root, texts, "04-resource")
    (ART / "resource-history.txt").write_text("\n".join(history) + "\n", encoding="utf-8")

    route = "resource_incomplete"
    attempts = []
    if resource_completed:
        method = probe.tap_profile(root, w, h)
        attempts.append(f"profile={method}")
        time.sleep(6)
        root, texts = dump("05-profile")
        if has_resource(texts):
            root, texts, done2, waited2, hist2 = wait_resource(root, texts, "05-profile-resource", 300)
            attempts += [f"profile_resource_completed={done2}", f"profile_resource_waited={waited2}"]
            (ART / "profile-resource-history.txt").write_text("\n".join(hist2) + "\n", encoding="utf-8")
            resource_completed = resource_completed and done2
            if done2:
                method = probe.tap_profile(root, w, h)
                attempts.append(f"profile_retry={method}")
                time.sleep(5)
                root, texts = dump("05-profile-retry")
        if has_phone(texts):
            route = "profile-phone"
        else:
            clicked, root, texts = probe.try_login_button(root, texts)
            attempts.append(f"login_button={clicked}")
            root, texts = dump("06-after-login")
            route = "login-button" if clicked else "profile"

    root, texts = dump("07-final")
    result = {
        "onboarding_steps": onboarding_steps,
        "swipe_failures": swipe_failures,
        "final_onboarding_counter": final_counter,
        "clicked_start_now": clicked_start_now,
        "resource_seen": resource_seen,
        "resource_completed": resource_completed,
        "resource_wait_seconds": waited,
        "route": route,
        "phone_route_detected": has_phone(texts),
        "login_screen_detected": probe.is_login_screen(texts),
        "pid": probe.adb("shell", "pidof", "com.kwai.video")[1].strip(),
        "attempts": ";".join(attempts),
    }
    pathlib.Path("artifacts/resource-phone-result.txt").write_text(
        "\n".join(f"{k}={v}" for k, v in result.items()) + "\n", encoding="utf-8"
    )
    (ART / "final-visible-text.txt").write_text("\n".join(texts), encoding="utf-8")
    print(result)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import time
import kwai_ui_probe as probe

POSITIVE_BUTTON_ID = "com.kwai.video:id/tiny_alert_dialog_positive_button"


def skip_slow_loader(root, texts, w, h, tag):
    slow = probe.contains(texts, r"internet.?s a bit slow|hang in there|^Skip$")
    if not slow:
        return root, texts, False

    skipped = probe.tap_node(root, lambda s: s.strip().lower() == "skip")
    if not skipped:
        probe.adb("shell", "input", "tap", str(int(w * 0.73)), str(int(h * 0.88)))
        skipped = True

    time.sleep(3)
    root, texts = probe.dump(f"{tag}-confirm")

    for attempt in range(1, 4):
        if not probe.contains(texts, r"skip the preparation|^yes, skip$"):
            break

        confirmed = probe.tap_resource_id(root, POSITIVE_BUTTON_ID)
        if not confirmed:
            confirmed = probe.tap_node(root, lambda s: s.strip().lower() == "yes, skip")
        if not confirmed:
            probe.adb("shell", "input", "tap", str(int(w * 0.50)), str(int(h * 0.55)))

        time.sleep(3)
        root, texts = probe.dump(f"{tag}-confirm-{attempt}")

    if probe.contains(texts, r"skip the preparation|^yes, skip$"):
        print("skip confirmation remained visible after retries")
        return root, texts, skipped

    time.sleep(4)
    root, texts = probe.dump(tag)
    return root, texts, skipped


probe.skip_slow_loader = skip_slow_loader
probe.main()

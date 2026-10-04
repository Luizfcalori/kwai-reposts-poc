# Safe mode

This build intentionally does not declare or use Android AccessibilityService. It only uses Android's normal document picker and ACTION_SEND sharing flow to hand a user-selected video (and optional text) to Kwai. It does not read passwords, SMS, account data, notifications, contacts, or screen content.

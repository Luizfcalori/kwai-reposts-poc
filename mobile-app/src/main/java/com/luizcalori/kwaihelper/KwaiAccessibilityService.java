package com.luizcalori.kwaihelper;

import android.accessibilityservice.AccessibilityService;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.os.SystemClock;
import android.view.accessibility.AccessibilityEvent;
import android.view.accessibility.AccessibilityNodeInfo;

import java.util.ArrayDeque;
import java.util.Arrays;
import java.util.Deque;
import java.util.List;

public class KwaiAccessibilityService extends AccessibilityService {
    private static final String KWAI_PACKAGE = "com.kwai.kuaishou.video.live";
    private long lastActionAt = 0;

    private static final List<String> NEXT_TEXTS = Arrays.asList(
            "Próximo", "Avançar", "Continuar", "Next", "Continue"
    );
    private static final List<String> POST_TEXTS = Arrays.asList(
            "Publicar", "Postar", "Compartilhar", "Post", "Publish"
    );

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {
        if (event == null || event.getPackageName() == null) return;
        if (!KWAI_PACKAGE.contentEquals(event.getPackageName())) return;

        SharedPreferences prefs = getSharedPreferences("kwai_job", MODE_PRIVATE);
        if (!prefs.getBoolean("active", false)) return;
        if (SystemClock.elapsedRealtime() - lastActionAt < 900) return;

        AccessibilityNodeInfo root = getRootInActiveWindow();
        if (root == null) return;

        String caption = prefs.getString("caption", "");
        boolean captionDone = prefs.getBoolean("caption_done", false);
        boolean autoPost = prefs.getBoolean("auto_post", false);

        if (!captionDone && !caption.isEmpty()) {
            AccessibilityNodeInfo edit = findBestEditable(root);
            if (edit != null && setText(edit, caption)) {
                prefs.edit().putBoolean("caption_done", true).apply();
                lastActionAt = SystemClock.elapsedRealtime();
                return;
            }
        }

        if (clickByText(root, NEXT_TEXTS)) {
            lastActionAt = SystemClock.elapsedRealtime();
            return;
        }

        if (autoPost && clickByText(root, POST_TEXTS)) {
            prefs.edit().putBoolean("active", false).apply();
            lastActionAt = SystemClock.elapsedRealtime();
        }
    }

    private AccessibilityNodeInfo findBestEditable(AccessibilityNodeInfo root) {
        Deque<AccessibilityNodeInfo> q = new ArrayDeque<>();
        q.add(root);
        AccessibilityNodeInfo fallback = null;
        while (!q.isEmpty()) {
            AccessibilityNodeInfo n = q.removeFirst();
            if (n.isEditable()) {
                CharSequence hint = n.getHintText();
                CharSequence text = n.getText();
                String joined = ((hint == null ? "" : hint.toString()) + " " + (text == null ? "" : text.toString())).toLowerCase();
                if (joined.contains("legenda") || joined.contains("caption") || joined.contains("descri") || joined.contains("diga algo")) {
                    return n;
                }
                if (fallback == null) fallback = n;
            }
            for (int i = 0; i < n.getChildCount(); i++) {
                AccessibilityNodeInfo c = n.getChild(i);
                if (c != null) q.addLast(c);
            }
        }
        return fallback;
    }

    private boolean setText(AccessibilityNodeInfo node, String text) {
        if (!node.isEnabled()) return false;
        Bundle args = new Bundle();
        args.putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, text);
        return node.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args);
    }

    private boolean clickByText(AccessibilityNodeInfo root, List<String> texts) {
        for (String text : texts) {
            List<AccessibilityNodeInfo> nodes = root.findAccessibilityNodeInfosByText(text);
            for (AccessibilityNodeInfo n : nodes) {
                if (n == null || !n.isVisibleToUser()) continue;
                AccessibilityNodeInfo clickable = n;
                for (int i = 0; i < 4 && clickable != null; i++) {
                    if (clickable.isClickable() && clickable.isEnabled()) {
                        return clickable.performAction(AccessibilityNodeInfo.ACTION_CLICK);
                    }
                    clickable = clickable.getParent();
                }
            }
        }
        return false;
    }

    @Override
    public void onInterrupt() {
    }
}

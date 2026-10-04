from pathlib import Path

java_path = Path('mobile-app/src/main/java/com/luizcalori/kwaihelper/MainActivity.java')
gradle_path = Path('mobile-app/build.gradle')

text = java_path.read_text(encoding='utf-8')

# Version label shown in the app.
text = text.replace('title.setText("Kwai Phone Helper v12");', 'title.setText("Kwai Phone Helper v14");')
text = text.replace('title.setText("Kwai Phone Helper v13");', 'title.setText("Kwai Phone Helper v14");')

# Larger, less-cropped preview for vertical Kwai content.
text = text.replace('thumbnail.setScaleType(ImageView.ScaleType.CENTER_CROP);',
                    'thumbnail.setScaleType(ImageView.ScaleType.FIT_CENTER);')
text = text.replace('new LinearLayout.LayoutParams(-1, dp(150));',
                    'new LinearLayout.LayoutParams(-1, dp(280));')

# Avoid a storage scan while the first screen is being created.
text = text.replace(
    'summaryLabel.setText("Pendentes: 0   •   Publicados: " + getPostedIds().size() + "   •   Local: 0 MB");',
    'summaryLabel.setText("Pendentes: 0   •   Publicados: carregando...   •   Local: 0 MB");'
)

# Add in-memory cache fields once.
anchor = '    private final List<QueueItem> pending = new ArrayList<>();\n'
cache_fields = (
    anchor
    + '    private final Object postedIdsLock = new Object();\n'
    + '    private Set<String> postedIdsCache = null;\n'
)
if 'private final Object postedIdsLock' not in text:
    if anchor not in text:
        raise SystemExit('pending anchor not found')
    text = text.replace(anchor, cache_fields, 1)

# Do not synchronously scan MediaStore during onCreate; warm it in the background.
old_tail = '''        historyLabel.setBackgroundColor(Color.WHITE);\n        box.addView(historyLabel, fullWidth());\n        refreshHistory();\n        updateSummary();\n\n        ScrollView scroll = new ScrollView(this);\n        scroll.addView(box);\n        setContentView(scroll);\n    }'''
new_tail = '''        historyLabel.setBackgroundColor(Color.WHITE);\n        box.addView(historyLabel, fullWidth());\n        refreshHistory();\n\n        ScrollView scroll = new ScrollView(this);\n        scroll.addView(box);\n        setContentView(scroll);\n        warmPostedIdsCache();\n    }'''
if old_tail not in text:
    raise SystemExit('onCreate tail anchor not found')
text = text.replace(old_tail, new_tail, 1)

# Replace getPostedIds with a lazy cached implementation.
start = text.index('    private Set<String> getPostedIds() {')
end = text.index('    private Set<String> readDurablePostedIds() {', start)
new_get = '''    private void warmPostedIdsCache() {\n        executor.execute(() -> {\n            getPostedIds();\n            runOnUiThread(this::updateSummary);\n        });\n    }\n\n    private void setPostedIdsCache(Set<String> ids) {\n        synchronized (postedIdsLock) {\n            postedIdsCache = new HashSet<>(ids);\n        }\n    }\n\n    private Set<String> getPostedIds() {\n        synchronized (postedIdsLock) {\n            if (postedIdsCache != null) return new HashSet<>(postedIdsCache);\n        }\n\n        SharedPreferences prefs = getSharedPreferences(PREFS, MODE_PRIVATE);\n        Set<String> result = new HashSet<>(prefs.getStringSet("posted_ids", new HashSet<>()));\n        result.addAll(readDurablePostedIds());\n        String folderUri = prefs.getString("history_folder_uri", "");\n        if (folderUri != null && !folderUri.isEmpty()) {\n            result.addAll(readPostedIdsFromHistoryFolder(Uri.parse(folderUri)));\n        }\n        String backupUri = prefs.getString("history_backup_uri", "");\n        if (backupUri != null && !backupUri.isEmpty()) {\n            try {\n                result.addAll(readPostedIdsFromUri(Uri.parse(backupUri)));\n            } catch (Exception ignored) {\n            }\n        }\n\n        synchronized (postedIdsLock) {\n            if (postedIdsCache == null) postedIdsCache = new HashSet<>(result);\n            else postedIdsCache.addAll(result);\n            return new HashSet<>(postedIdsCache);\n        }\n    }\n\n'''
text = text[:start] + new_get + text[end:]

# Keep the cache authoritative whenever the app writes a new posted set.
persist_anchor = '''    private void persistPostedIds(Set<String> posted) {\n        Set<String> safe = new HashSet<>(posted);\n        SharedPreferences prefs = getSharedPreferences(PREFS, MODE_PRIVATE);'''
persist_repl = '''    private void persistPostedIds(Set<String> posted) {\n        Set<String> safe = new HashSet<>(posted);\n        setPostedIdsCache(safe);\n        SharedPreferences prefs = getSharedPreferences(PREFS, MODE_PRIVATE);'''
if persist_anchor not in text:
    raise SystemExit('persist anchor not found')
text = text.replace(persist_anchor, persist_repl, 1)

# Refresh cache after the folder consolidation operation.
consolidate_anchor = '''            getSharedPreferences(PREFS, MODE_PRIVATE).edit()\n                    .putString("history_folder_uri", folderUri.toString())\n                    .putString("history_backup_uri", canonical.getUri().toString())\n                    .putStringSet("posted_ids", new HashSet<>(merged))\n                    .apply();\n\n            Toast.makeText(this, "Histórico consolidado: "'''
consolidate_repl = '''            getSharedPreferences(PREFS, MODE_PRIVATE).edit()\n                    .putString("history_folder_uri", folderUri.toString())\n                    .putString("history_backup_uri", canonical.getUri().toString())\n                    .putStringSet("posted_ids", new HashSet<>(merged))\n                    .apply();\n            setPostedIdsCache(merged);\n\n            Toast.makeText(this, "Histórico consolidado: "'''
if consolidate_anchor not in text:
    raise SystemExit('consolidation anchor not found')
text = text.replace(consolidate_anchor, consolidate_repl, 1)

# Refresh cache after legacy single-file import too.
import_anchor = '''            getSharedPreferences(PREFS, MODE_PRIVATE)\n                    .edit()\n                    .putString("history_backup_uri", uri.toString())\n                    .putStringSet("posted_ids", new HashSet<>(merged))\n                    .apply();\n            saveDurablePostedIds(merged);'''
import_repl = '''            getSharedPreferences(PREFS, MODE_PRIVATE)\n                    .edit()\n                    .putString("history_backup_uri", uri.toString())\n                    .putStringSet("posted_ids", new HashSet<>(merged))\n                    .apply();\n            setPostedIdsCache(merged);\n            saveDurablePostedIds(merged);'''
if import_anchor in text:
    text = text.replace(import_anchor, import_repl, 1)

java_path.write_text(text, encoding='utf-8')

gradle = gradle_path.read_text(encoding='utf-8')
gradle = gradle.replace('versionCode 13', 'versionCode 14')
gradle = gradle.replace("versionName '1.3.0'", "versionName '1.4.0'")
gradle_path.write_text(gradle, encoding='utf-8')

print('v14 performance + larger preview patch applied')

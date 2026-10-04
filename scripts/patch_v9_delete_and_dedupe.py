#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JAVA = ROOT / "mobile-app/src/main/java/com/luizcalori/kwaihelper/MainActivity.java"
GRADLE = ROOT / "mobile-app/build.gradle"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f"missing patch anchor: {label}")
    return text.replace(old, new, 1)


text = JAVA.read_text(encoding="utf-8")

text = replace_once(
    text,
    "import android.content.ActivityNotFoundException;\n",
    "import android.content.ActivityNotFoundException;\nimport android.content.ContentUris;\n",
    "ContentUris import",
)
text = replace_once(
    text,
    "import android.graphics.Color;\n",
    "import android.graphics.Color;\nimport android.database.Cursor;\n",
    "Cursor import",
)

text = replace_once(
    text,
    '    private static final String PUBLIC_DOWNLOADED = Environment.DIRECTORY_MOVIES + "/KwaiHelper/Baixados";\n'
    '    private static final String PUBLIC_PUBLISHED = Environment.DIRECTORY_MOVIES + "/KwaiHelper/Publicados";\n',
    '    private static final String PUBLIC_DOWNLOADED = Environment.DIRECTORY_MOVIES + "/KwaiHelper/Baixados";\n'
    '    private static final String LEGACY_PUBLIC_PUBLISHED = Environment.DIRECTORY_MOVIES + "/KwaiHelper/Publicados/";\n'
    '    private static final String STATE_RELATIVE_PATH = Environment.DIRECTORY_DOWNLOADS + "/KwaiHelper/";\n'
    '    private static final String STATE_FILE_NAME = "kwaihelper_publicados.json";\n',
    "storage constants",
)

text = replace_once(
    text,
    "    private Button skipButton;\n",
    "    private Button skipButton;\n    private Button alreadyPostedButton;\n",
    "alreadyPosted field",
)

text = text.replace("Kwai Phone Helper v8", "Kwai Phone Helper v9")
text = text.replace("KwaiPhoneHelper/0.8 Android", "KwaiPhoneHelper/0.9 Android")
text = text.replace("KwaiPhoneHelper/0.8", "KwaiPhoneHelper/0.9")
text = text.replace(
    'postedButton = button("✓ Publicado — mover para Publicados e preparar próximo");',
    'postedButton = button("✓ Publicado — excluir definitivamente e preparar próximo");',
)

text = replace_once(
    text,
    "        super.onCreate(savedInstanceState);\n\n        int pad = dp(16);",
    "        super.onCreate(savedInstanceState);\n        migrateLegacyPublishedFolder();\n\n        int pad = dp(16);",
    "legacy migration onCreate",
)

old_folder_buttons = '''        Button openDownloaded = button("📂 Abrir KwaiHelper/Baixados");
        openDownloaded.setOnClickListener(v -> openPublicFolder("Movies/KwaiHelper/Baixados"));
        box.addView(openDownloaded);

        Button openPublished = button("📂 Abrir KwaiHelper/Publicados");
        openPublished.setOnClickListener(v -> openPublicFolder("Movies/KwaiHelper/Publicados"));
        box.addView(openPublished);
'''
new_folder_buttons = '''        Button openDownloaded = button("📂 Abrir KwaiHelper/Baixados");
        openDownloaded.setOnClickListener(v -> openPublicFolder("Movies/KwaiHelper/Baixados"));
        box.addView(openDownloaded);
'''
text = replace_once(text, old_folder_buttons, new_folder_buttons, "remove Publicados folder button")

skip_block = '''        skipButton = button("↪ Pular este vídeo");
        skipButton.setEnabled(false);
        skipButton.setOnClickListener(v -> skipCurrent());
        box.addView(skipButton);
'''
new_skip_block = skip_block + '''
        alreadyPostedButton = button("⛔ Já publiquei antes — não mostrar novamente");
        alreadyPostedButton.setEnabled(false);
        alreadyPostedButton.setOnClickListener(v -> markAlreadyPosted());
        box.addView(alreadyPostedButton);
'''
text = replace_once(text, skip_block, new_skip_block, "already published button")

text = replace_once(
    text,
    "            skipButton.setEnabled(false);\n            updateSummary();",
    "            skipButton.setEnabled(false);\n            alreadyPostedButton.setEnabled(false);\n            updateSummary();",
    "disable already button on empty",
)
text = replace_once(
    text,
    "        skipButton.setEnabled(pending.size() > 1);\n        setChip(\"AGUARDANDO DOWNLOAD\");",
    "        skipButton.setEnabled(pending.size() > 1);\n        alreadyPostedButton.setEnabled(true);\n        setChip(\"AGUARDANDO DOWNLOAD\");",
    "enable already button",
)

old_mark = '''        QueueItem postedItem = current;
        boolean archived = false;
        if (publicMediaUri != null) {
            try {
                movePublicMedia(publicMediaUri, PUBLIC_PUBLISHED);
                archived = true;
            } catch (Exception exc) {
                Toast.makeText(this, "Publicado, mas não consegui mover a cópia para Publicados: " + shortMessage(exc), Toast.LENGTH_LONG).show();
            }
        }
        if (downloadedFile != null && downloadedFile.exists() && !downloadedFile.delete()) {
            Toast.makeText(this, "Não consegui excluir o arquivo temporário do app agora.", Toast.LENGTH_LONG).show();
        }

        Set<String> posted = getPostedIds();
        posted.add(postedItem.key());
        getSharedPreferences(PREFS, MODE_PRIVATE)
                .edit()
                .putStringSet("posted_ids", new HashSet<>(posted))
                .apply();
        appendHistory(postedItem);
'''
new_mark = '''        QueueItem postedItem = current;
        if (publicMediaUri != null) {
            try {
                getContentResolver().delete(publicMediaUri, null, null);
            } catch (Exception exc) {
                Toast.makeText(this, "Não consegui excluir a cópia visível agora: " + shortMessage(exc), Toast.LENGTH_LONG).show();
            }
            publicMediaUri = null;
        }
        if (downloadedFile != null && downloadedFile.exists() && !downloadedFile.delete()) {
            Toast.makeText(this, "Não consegui excluir o arquivo temporário do app agora.", Toast.LENGTH_LONG).show();
        }

        Set<String> posted = getPostedIds();
        posted.add(postedItem.key());
        persistPostedIds(posted);
        appendHistory(postedItem);
'''
text = replace_once(text, old_mark, new_mark, "delete posted video")

text = replace_once(
    text,
    '            setStatus(archived ? "Publicado ✓ Movido para Movies/KwaiHelper/Publicados. Preparando o próximo vídeo..." : "Publicado ✓ Preparando o próximo vídeo...");',
    '            setStatus("Publicado ✓ Vídeo excluído definitivamente do celular. Preparando o próximo...");',
    "posted status",
)

insert_before_skip = '''    private void skipCurrent() {
'''
mark_already = '''    private void markAlreadyPosted() {
        if (current == null) return;

        QueueItem item = current;
        if (publicMediaUri != null) {
            try { getContentResolver().delete(publicMediaUri, null, null); } catch (Exception ignored) {}
            publicMediaUri = null;
        }
        if (downloadedFile != null && downloadedFile.exists()) downloadedFile.delete();

        Set<String> posted = getPostedIds();
        posted.add(item.key());
        persistPostedIds(posted);
        appendHistory(item);

        if (!pending.isEmpty()) pending.remove(0);
        downloadedFile = null;
        refreshHistory();
        selectFirstPending();

        if (current != null) {
            setStatus("Marcado como já publicado. Esse vídeo não voltará para a fila. Preparando o próximo...");
            downloadCurrent();
        } else {
            setStatus("Marcado como já publicado. Fila concluída.");
            setChip("FILA CONCLUÍDA");
        }
        updateSummary();
    }

'''
text = replace_once(text, insert_before_skip, mark_already + insert_before_skip, "mark already published method")

old_get = '''    private Set<String> getPostedIds() {
        SharedPreferences prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        Set<String> stored = prefs.getStringSet("posted_ids", null);
        return stored == null ? new HashSet<>() : new HashSet<>(stored);
    }
'''
new_get = '''    private Set<String> getPostedIds() {
        SharedPreferences prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        Set<String> stored = prefs.getStringSet("posted_ids", null);
        Set<String> local = stored == null ? new HashSet<>() : new HashSet<>(stored);
        Set<String> durable = loadDurablePostedIds();
        Set<String> merged = new HashSet<>(durable);
        merged.addAll(local);

        if (!merged.equals(local)) {
            prefs.edit().putStringSet("posted_ids", new HashSet<>(merged)).apply();
        }
        if (!merged.equals(durable)) {
            saveDurablePostedIds(merged);
        }
        return merged;
    }

    private void persistPostedIds(Set<String> posted) {
        Set<String> copy = new HashSet<>(posted);
        getSharedPreferences(PREFS, MODE_PRIVATE)
                .edit()
                .putStringSet("posted_ids", copy)
                .apply();
        saveDurablePostedIds(copy);
    }

    private Set<String> loadDurablePostedIds() {
        Set<String> result = new HashSet<>();
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) return result;
        Uri uri = findDurableStateUri();
        if (uri == null) return result;

        try (BufferedReader reader = new BufferedReader(
                new InputStreamReader(getContentResolver().openInputStream(uri), StandardCharsets.UTF_8))) {
            StringBuilder text = new StringBuilder();
            String line;
            while ((line = reader.readLine()) != null) text.append(line);
            if (text.length() == 0) return result;
            JSONObject root = new JSONObject(text.toString());
            JSONArray ids = root.optJSONArray("posted_ids");
            if (ids != null) {
                for (int i = 0; i < ids.length(); i++) {
                    String value = ids.optString(i, "").trim();
                    if (!value.isEmpty()) result.add(value);
                }
            }
        } catch (Exception ignored) {
        }
        return result;
    }

    private Uri findDurableStateUri() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) return null;
        String[] projection = {MediaStore.Downloads._ID};
        String selection = MediaStore.Downloads.DISPLAY_NAME + "=? AND "
                + MediaStore.Downloads.RELATIVE_PATH + "=?";
        String[] args = {STATE_FILE_NAME, STATE_RELATIVE_PATH};
        try (Cursor cursor = getContentResolver().query(
                MediaStore.Downloads.EXTERNAL_CONTENT_URI,
                projection,
                selection,
                args,
                MediaStore.Downloads.DATE_ADDED + " DESC")) {
            if (cursor != null && cursor.moveToFirst()) {
                return ContentUris.withAppendedId(
                        MediaStore.Downloads.EXTERNAL_CONTENT_URI,
                        cursor.getLong(0));
            }
        } catch (Exception ignored) {
        }
        return null;
    }

    private void saveDurablePostedIds(Set<String> posted) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) return;
        try {
            Uri uri = findDurableStateUri();
            boolean created = false;
            if (uri == null) {
                ContentValues values = new ContentValues();
                values.put(MediaStore.Downloads.DISPLAY_NAME, STATE_FILE_NAME);
                values.put(MediaStore.Downloads.MIME_TYPE, "application/json");
                values.put(MediaStore.Downloads.RELATIVE_PATH, STATE_RELATIVE_PATH);
                values.put(MediaStore.Downloads.IS_PENDING, 1);
                uri = getContentResolver().insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values);
                created = true;
            }
            if (uri == null) return;

            JSONObject root = new JSONObject();
            JSONArray ids = new JSONArray();
            List<String> sorted = new ArrayList<>(posted);
            java.util.Collections.sort(sorted);
            for (String value : sorted) ids.put(value);
            root.put("posted_ids", ids);

            try (OutputStream output = getContentResolver().openOutputStream(uri, "wt")) {
                if (output == null) return;
                output.write(root.toString().getBytes(StandardCharsets.UTF_8));
                output.flush();
            }

            if (created) {
                ContentValues ready = new ContentValues();
                ready.put(MediaStore.Downloads.IS_PENDING, 0);
                getContentResolver().update(uri, ready, null, null);
            }
        } catch (Exception ignored) {
        }
    }

    private void migrateLegacyPublishedFolder() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) return;
        Set<String> posted = getPostedIds();
        List<Uri> toDelete = new ArrayList<>();
        String[] projection = {
                MediaStore.Video.Media._ID,
                MediaStore.Video.Media.DISPLAY_NAME
        };
        String selection = MediaStore.Video.Media.RELATIVE_PATH + "=?";
        String[] args = {LEGACY_PUBLIC_PUBLISHED};

        try (Cursor cursor = getContentResolver().query(
                MediaStore.Video.Media.EXTERNAL_CONTENT_URI,
                projection,
                selection,
                args,
                null)) {
            if (cursor != null) {
                int idColumn = cursor.getColumnIndexOrThrow(MediaStore.Video.Media._ID);
                int nameColumn = cursor.getColumnIndexOrThrow(MediaStore.Video.Media.DISPLAY_NAME);
                while (cursor.moveToNext()) {
                    long id = cursor.getLong(idColumn);
                    String name = cursor.getString(nameColumn);
                    if (name != null && name.endsWith(".mp4")) {
                        String base = name.substring(0, name.length() - 4);
                        int split = base.lastIndexOf('_');
                        if (split > 0 && split < base.length() - 1) {
                            String sourceId = base.substring(0, split);
                            String videoId = base.substring(split + 1);
                            if (videoId.matches("\\d+")) posted.add(sourceId + ":" + videoId);
                        }
                    }
                    toDelete.add(ContentUris.withAppendedId(MediaStore.Video.Media.EXTERNAL_CONTENT_URI, id));
                }
            }
        } catch (Exception ignored) {
        }

        if (!toDelete.isEmpty()) {
            persistPostedIds(posted);
            for (Uri uri : toDelete) {
                try { getContentResolver().delete(uri, null, null); } catch (Exception ignored) {}
            }
        }
    }
'''
text = replace_once(text, old_get, new_get, "persistent posted IDs")

old_move = '''    private void movePublicMedia(Uri uri, String relativePath) {
        if (uri == null || Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) return;
        ContentValues values = new ContentValues();
        values.put(MediaStore.Video.Media.RELATIVE_PATH, relativePath);
        int updated = getContentResolver().update(uri, values, null, null);
        if (updated <= 0) throw new IllegalStateException("Android não moveu o vídeo para a pasta Publicados.");
    }

'''
text = replace_once(text, old_move, "", "remove move-to-published helper")

JAVA.write_text(text, encoding="utf-8")

gradle = GRADLE.read_text(encoding="utf-8")
gradle = replace_once(gradle, "versionCode 8", "versionCode 9", "versionCode")
gradle = replace_once(gradle, "versionName '0.8.0'", "versionName '0.9.0'", "versionName")
GRADLE.write_text(gradle, encoding="utf-8")
print("v9 delete + persistent dedupe patch applied")

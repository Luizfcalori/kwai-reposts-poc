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
    "import android.content.ClipData;\n",
    "import android.content.ClipData;\nimport android.content.ContentValues;\n",
    "ContentValues import",
)
text = replace_once(
    text,
    "import android.os.Bundle;\n",
    "import android.os.Bundle;\nimport android.os.Build;\n",
    "Build import",
)
text = replace_once(
    text,
    "import android.os.Environment;\n",
    "import android.os.Environment;\nimport android.provider.DocumentsContract;\nimport android.provider.MediaStore;\n",
    "provider imports",
)
text = replace_once(
    text,
    "import java.io.FileOutputStream;\n",
    "import java.io.FileOutputStream;\nimport java.io.FileInputStream;\nimport java.io.OutputStream;\n",
    "stream imports",
)

text = replace_once(
    text,
    '    private static final String PREFS = "kwai_queue_state";\n',
    '    private static final String PREFS = "kwai_queue_state";\n'
    '    private static final String PUBLIC_DOWNLOADED = Environment.DIRECTORY_MOVIES + "/KwaiHelper/Baixados";\n'
    '    private static final String PUBLIC_PUBLISHED = Environment.DIRECTORY_MOVIES + "/KwaiHelper/Publicados";\n',
    "public folder constants",
)
text = replace_once(
    text,
    "    private File downloadedFile;\n",
    "    private File downloadedFile;\n    private Uri publicMediaUri;\n",
    "publicMediaUri field",
)

text = text.replace("Kwai Phone Helper v7", "Kwai Phone Helper v8")
text = text.replace("KwaiPhoneHelper/0.7 Android", "KwaiPhoneHelper/0.8 Android")
text = text.replace("KwaiPhoneHelper/0.7", "KwaiPhoneHelper/0.8")
text = text.replace(
    'postedButton = button("✓ Publicado — excluir e preparar próximo");',
    'postedButton = button("✓ Publicado — mover para Publicados e preparar próximo");',
)

anchor = '''        skipButton = button("↪ Pular este vídeo");
        skipButton.setEnabled(false);
        skipButton.setOnClickListener(v -> skipCurrent());
        box.addView(skipButton);
'''
insert = anchor + '''
        TextView foldersTitle = new TextView(this);
        foldersTitle.setText("PASTAS NO CELULAR");
        foldersTitle.setTextSize(13);
        foldersTitle.setTextColor(Color.GRAY);
        foldersTitle.setPadding(0, dp(10), 0, dp(4));
        box.addView(foldersTitle);

        Button openDownloaded = button("📂 Abrir KwaiHelper/Baixados");
        openDownloaded.setOnClickListener(v -> openPublicFolder("Movies/KwaiHelper/Baixados"));
        box.addView(openDownloaded);

        Button openPublished = button("📂 Abrir KwaiHelper/Publicados");
        openPublished.setOnClickListener(v -> openPublicFolder("Movies/KwaiHelper/Publicados"));
        box.addView(openPublished);
'''
text = replace_once(text, anchor, insert, "folder buttons")

text = replace_once(
    text,
    "        downloadedFile = null;\n        shareButton.setEnabled(false);",
    "        downloadedFile = null;\n        publicMediaUri = null;\n        shareButton.setEnabled(false);",
    "reset public uri",
)

old = '''                downloadedFile = target;
                runOnUiThread(() -> {
                    downloadButton.setEnabled(true);
                    shareButton.setEnabled(true);
                    postedButton.setEnabled(true);
                    copyButton.setEnabled(!caption.getText().toString().trim().isEmpty());
                    setStatus("Vídeo pronto. Copie a legenda e envie para o Kwai.");
                    setChip("PRONTO PARA ENVIAR");
                    updateSummary();
                });
'''
new = '''                downloadedFile = target;
                String publicNote = "";
                try {
                    if (publicMediaUri != null) {
                        try { getContentResolver().delete(publicMediaUri, null, null); } catch (Exception ignored) {}
                    }
                    publicMediaUri = copyToPublicFolder(target, PUBLIC_DOWNLOADED);
                } catch (Exception storageExc) {
                    publicMediaUri = null;
                    publicNote = " A cópia visível não pôde ser criada: " + shortMessage(storageExc);
                }
                String finalPublicNote = publicNote;
                runOnUiThread(() -> {
                    downloadButton.setEnabled(true);
                    shareButton.setEnabled(true);
                    postedButton.setEnabled(true);
                    copyButton.setEnabled(!caption.getText().toString().trim().isEmpty());
                    setStatus("Vídeo pronto em Movies/KwaiHelper/Baixados. Copie a legenda e envie para o Kwai." + finalPublicNote);
                    setChip("PRONTO PARA ENVIAR");
                    updateSummary();
                });
'''
text = replace_once(text, old, new, "download public copy")

old = '''        QueueItem postedItem = current;
        if (downloadedFile != null && downloadedFile.exists() && !downloadedFile.delete()) {
            Toast.makeText(this, "Não consegui excluir o arquivo local agora.", Toast.LENGTH_LONG).show();
        }
'''
new = '''        QueueItem postedItem = current;
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
'''
text = replace_once(text, old, new, "archive posted media")

text = replace_once(
    text,
    '            setStatus("Publicado ✓ Arquivo excluído. Preparando o próximo vídeo...");',
    '            setStatus(archived ? "Publicado ✓ Movido para Movies/KwaiHelper/Publicados. Preparando o próximo vídeo..." : "Publicado ✓ Preparando o próximo vídeo...");',
    "posted status",
)

old = '''        if (downloadedFile != null && downloadedFile.exists()) downloadedFile.delete();
        QueueItem skipped = pending.remove(0);
'''
new = '''        if (downloadedFile != null && downloadedFile.exists()) downloadedFile.delete();
        if (publicMediaUri != null) {
            try { getContentResolver().delete(publicMediaUri, null, null); } catch (Exception ignored) {}
            publicMediaUri = null;
        }
        QueueItem skipped = pending.remove(0);
'''
text = replace_once(text, old, new, "skip public cleanup")

anchor = '''    private File videoFolder() {
        return new File(getExternalFilesDir(Environment.DIRECTORY_MOVIES), "KwaiHelper");
    }
'''
helpers = '''    private Uri copyToPublicFolder(File source, String relativePath) throws Exception {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) {
            return null;
        }

        ContentValues values = new ContentValues();
        values.put(MediaStore.Video.Media.DISPLAY_NAME, source.getName());
        values.put(MediaStore.Video.Media.MIME_TYPE, "video/mp4");
        values.put(MediaStore.Video.Media.RELATIVE_PATH, relativePath);
        values.put(MediaStore.Video.Media.IS_PENDING, 1);

        Uri uri = getContentResolver().insert(MediaStore.Video.Media.EXTERNAL_CONTENT_URI, values);
        if (uri == null) throw new IllegalStateException("MediaStore não criou o arquivo visível.");

        try (InputStream input = new FileInputStream(source);
             OutputStream output = getContentResolver().openOutputStream(uri, "w")) {
            if (output == null) throw new IllegalStateException("Não foi possível abrir a pasta pública.");
            byte[] buffer = new byte[64 * 1024];
            int read;
            while ((read = input.read(buffer)) != -1) output.write(buffer, 0, read);
            output.flush();
        } catch (Exception exc) {
            try { getContentResolver().delete(uri, null, null); } catch (Exception ignored) {}
            throw exc;
        }

        ContentValues ready = new ContentValues();
        ready.put(MediaStore.Video.Media.IS_PENDING, 0);
        getContentResolver().update(uri, ready, null, null);
        return uri;
    }

    private void movePublicMedia(Uri uri, String relativePath) {
        if (uri == null || Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) return;
        ContentValues values = new ContentValues();
        values.put(MediaStore.Video.Media.RELATIVE_PATH, relativePath);
        int updated = getContentResolver().update(uri, values, null, null);
        if (updated <= 0) throw new IllegalStateException("Android não moveu o vídeo para a pasta Publicados.");
    }

    private void openPublicFolder(String relativePath) {
        String documentId = "primary:" + relativePath;
        Uri uri = DocumentsContract.buildDocumentUri("com.android.externalstorage.documents", documentId);
        try {
            Intent view = new Intent(Intent.ACTION_VIEW);
            view.setDataAndType(uri, "vnd.android.document/directory");
            view.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
            startActivity(view);
        } catch (Exception first) {
            try {
                Intent picker = new Intent(Intent.ACTION_OPEN_DOCUMENT_TREE);
                picker.putExtra(DocumentsContract.EXTRA_INITIAL_URI, uri);
                startActivity(picker);
                Toast.makeText(this, "Pasta: Armazenamento interno/" + relativePath, Toast.LENGTH_LONG).show();
            } catch (Exception second) {
                Toast.makeText(this, "Abra Meus Arquivos > Armazenamento interno > " + relativePath, Toast.LENGTH_LONG).show();
            }
        }
    }

''' + anchor
text = replace_once(text, anchor, helpers, "MediaStore helpers")

JAVA.write_text(text, encoding="utf-8")

gradle = GRADLE.read_text(encoding="utf-8")
gradle = replace_once(gradle, "versionCode 3", "versionCode 4", "versionCode")
gradle = replace_once(gradle, "versionName '0.7.0'", "versionName '0.8.0'", "versionName")
GRADLE.write_text(gradle, encoding="utf-8")
print("v8 public folders patch applied")

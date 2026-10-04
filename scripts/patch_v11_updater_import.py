from pathlib import Path

java_path = Path('mobile-app/src/main/java/com/luizcalori/kwaihelper/MainActivity.java')
gradle_path = Path('mobile-app/build.gradle')
manifest_path = Path('mobile-app/src/main/AndroidManifest.xml')
paths_path = Path('mobile-app/src/main/res/xml/file_paths.xml')

text = java_path.read_text(encoding='utf-8')

text = text.replace('import android.provider.MediaStore;\n', 'import android.provider.MediaStore;\nimport android.provider.Settings;\n')
text = text.replace('import java.nio.charset.StandardCharsets;\n', 'import java.nio.charset.StandardCharsets;\nimport java.security.MessageDigest;\n')

text = text.replace(
'''    private static final String STATE_FILE_NAME = "kwaihelper_publicados.json";\n''',
'''    private static final String STATE_FILE_NAME = "kwaihelper_publicados.json";\n    private static final String LATEST_INFO_URL =\n            "https://raw.githubusercontent.com/Luizfcalori/kwai-reposts-poc/main/releases/latest.json";\n    private static final String TRUSTED_APK_PREFIX =\n            "https://raw.githubusercontent.com/Luizfcalori/kwai-reposts-poc/";\n    private static final int REQ_IMPORT_HISTORY = 701;\n''')

text = text.replace(
'''    private final ExecutorService imageExecutor = Executors.newSingleThreadExecutor();\n''',
'''    private final ExecutorService imageExecutor = Executors.newSingleThreadExecutor();\n    private final ExecutorService updateExecutor = Executors.newSingleThreadExecutor();\n''')

text = text.replace(
'''    private Button alreadyPostedButton;\n\n    private QueueItem current;\n''',
'''    private Button alreadyPostedButton;\n    private Button updateButton;\n    private Button importHistoryButton;\n\n    private QueueItem current;\n''')

text = text.replace(
'''    private Uri publicMediaUri;\n''',
'''    private Uri publicMediaUri;\n    private File pendingUpdateFile;\n''', 1)

text = text.replace('title.setText("Kwai Phone Helper v10");', 'title.setText("Kwai Phone Helper v11");')

anchor = '''        syncButton = button("↻ Sincronizar fila e baixar próximo");\n        syncButton.setOnClickListener(v -> syncQueue(true));\n        box.addView(syncButton);\n\n'''
insert = anchor + '''        updateButton = button("⬆ Atualizar app");\n        updateButton.setOnClickListener(v -> checkForUpdate());\n\n        importHistoryButton = button("📥 Importar histórico");\n        importHistoryButton.setOnClickListener(v -> chooseHistoryBackup());\n        box.addView(actionRow(updateButton, importHistoryButton));\n\n'''
if anchor not in text:
    raise SystemExit('sync anchor not found')
text = text.replace(anchor, insert, 1)

methods_anchor = '    private void syncQueue(boolean downloadAfterSync) {'
methods = r'''    @Override
    protected void onResume() {
        super.onResume();
        if (pendingUpdateFile != null
                && pendingUpdateFile.exists()
                && (Build.VERSION.SDK_INT < Build.VERSION_CODES.O
                || getPackageManager().canRequestPackageInstalls())) {
            File ready = pendingUpdateFile;
            pendingUpdateFile = null;
            installUpdateApk(ready);
        }
    }

    private void chooseHistoryBackup() {
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.setType("application/json");
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_WRITE_URI_PERMISSION
                | Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION);
        try {
            startActivityForResult(intent, REQ_IMPORT_HISTORY);
        } catch (ActivityNotFoundException ex) {
            intent.setType("*/*");
            startActivityForResult(intent, REQ_IMPORT_HISTORY);
        }
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode != REQ_IMPORT_HISTORY || resultCode != RESULT_OK || data == null) return;
        Uri uri = data.getData();
        if (uri == null) return;

        try {
            int flags = data.getFlags() & (Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_WRITE_URI_PERMISSION);
            getContentResolver().takePersistableUriPermission(uri, flags);
        } catch (Exception ignored) {
        }

        try {
            Set<String> imported = readPostedIdsFromUri(uri);
            if (imported.isEmpty()) {
                Toast.makeText(this, "O arquivo não contém IDs publicados.", Toast.LENGTH_LONG).show();
                return;
            }
            Set<String> merged = getPostedIds();
            int before = merged.size();
            merged.addAll(imported);
            getSharedPreferences(PREFS, MODE_PRIVATE)
                    .edit()
                    .putString("history_backup_uri", uri.toString())
                    .putStringSet("posted_ids", new HashSet<>(merged))
                    .apply();
            saveDurablePostedIds(merged);
            int added = merged.size() - before;
            Toast.makeText(this, "Histórico importado: " + added + " IDs recuperados.", Toast.LENGTH_LONG).show();
            updateSummary();
            syncQueue(true);
        } catch (Exception exc) {
            Toast.makeText(this, "Falha ao importar histórico: " + shortMessage(exc), Toast.LENGTH_LONG).show();
        }
    }

    private Set<String> readPostedIdsFromUri(Uri uri) throws Exception {
        Set<String> result = new HashSet<>();
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
        }
        return result;
    }

    private void writePostedIdsToUri(Uri uri, Set<String> posted) throws Exception {
        JSONObject root = new JSONObject();
        JSONArray ids = new JSONArray();
        List<String> sorted = new ArrayList<>(posted);
        java.util.Collections.sort(sorted);
        for (String value : sorted) ids.put(value);
        root.put("posted_ids", ids);

        try (OutputStream output = getContentResolver().openOutputStream(uri, "wt")) {
            if (output == null) throw new IllegalStateException("Não foi possível abrir o arquivo de histórico.");
            output.write(root.toString().getBytes(StandardCharsets.UTF_8));
            output.flush();
        }
    }

    private void checkForUpdate() {
        updateButton.setEnabled(false);
        setStatus("Verificando atualização do Helper...");
        updateExecutor.execute(() -> {
            HttpURLConnection connection = null;
            try {
                URL url = new URL(LATEST_INFO_URL + "?t=" + System.currentTimeMillis());
                connection = (HttpURLConnection) url.openConnection();
                connection.setConnectTimeout(20000);
                connection.setReadTimeout(30000);
                connection.setUseCaches(false);
                connection.setRequestProperty("User-Agent", "KwaiPhoneHelper-Updater/1.0");

                StringBuilder raw = new StringBuilder();
                try (BufferedReader reader = new BufferedReader(
                        new InputStreamReader(connection.getInputStream(), StandardCharsets.UTF_8))) {
                    String line;
                    while ((line = reader.readLine()) != null) raw.append(line);
                }

                JSONObject info = new JSONObject(raw.toString());
                long remoteCode = info.optLong("version_code", 0);
                String remoteName = info.optString("version_name", "nova");
                String apkUrl = info.optString("apk_url", "");
                String expectedSha = info.optString("sha256", "").toLowerCase(Locale.ROOT);
                long currentCode = currentVersionCode();

                if (remoteCode <= currentCode) {
                    runOnUiThread(() -> {
                        updateButton.setEnabled(true);
                        setStatus("Você já está na versão mais recente.");
                        Toast.makeText(this, "App já está atualizado ✓", Toast.LENGTH_SHORT).show();
                    });
                    return;
                }
                if (!apkUrl.startsWith(TRUSTED_APK_PREFIX) || expectedSha.length() != 64) {
                    throw new SecurityException("Metadados de atualização inválidos.");
                }

                File dir = getExternalFilesDir(Environment.DIRECTORY_DOWNLOADS);
                if (dir == null) throw new IllegalStateException("Pasta de atualização indisponível.");
                if (!dir.exists() && !dir.mkdirs()) throw new IllegalStateException("Não foi possível criar a pasta de atualização.");
                File target = new File(dir, "kwai-phone-helper-v" + remoteCode + ".apk");
                downloadUpdateFile(apkUrl, target);
                String actualSha = sha256(target);
                if (!actualSha.equalsIgnoreCase(expectedSha)) {
                    target.delete();
                    throw new SecurityException("Assinatura SHA-256 do download não confere.");
                }

                runOnUiThread(() -> {
                    updateButton.setEnabled(true);
                    setStatus("Versão " + remoteName + " baixada. O Android vai pedir sua confirmação para atualizar.");
                    installUpdateApk(target);
                });
            } catch (Exception exc) {
                runOnUiThread(() -> {
                    updateButton.setEnabled(true);
                    setStatus("Falha ao atualizar: " + shortMessage(exc));
                    Toast.makeText(this, "Não consegui atualizar: " + shortMessage(exc), Toast.LENGTH_LONG).show();
                });
            } finally {
                if (connection != null) connection.disconnect();
            }
        });
    }

    private long currentVersionCode() throws Exception {
        android.content.pm.PackageInfo info = getPackageManager().getPackageInfo(getPackageName(), 0);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) return info.getLongVersionCode();
        return info.versionCode;
    }

    private void downloadUpdateFile(String urlText, File target) throws Exception {
        HttpURLConnection connection = null;
        try {
            connection = (HttpURLConnection) new URL(urlText + "?t=" + System.currentTimeMillis()).openConnection();
            connection.setConnectTimeout(25000);
            connection.setReadTimeout(120000);
            connection.setInstanceFollowRedirects(true);
            connection.setUseCaches(false);
            connection.setRequestProperty("User-Agent", "KwaiPhoneHelper-Updater/1.0");
            int response = connection.getResponseCode();
            if (response < 200 || response >= 300) throw new IllegalStateException("HTTP " + response);
            try (InputStream input = new BufferedInputStream(connection.getInputStream());
                 FileOutputStream output = new FileOutputStream(target)) {
                byte[] buffer = new byte[64 * 1024];
                int read;
                while ((read = input.read(buffer)) != -1) output.write(buffer, 0, read);
                output.flush();
            }
            if (target.length() < 1024 * 100) throw new IllegalStateException("APK recebido parece inválido.");
        } finally {
            if (connection != null) connection.disconnect();
        }
    }

    private String sha256(File file) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        try (InputStream input = new BufferedInputStream(new FileInputStream(file))) {
            byte[] buffer = new byte[64 * 1024];
            int read;
            while ((read = input.read(buffer)) != -1) digest.update(buffer, 0, read);
        }
        StringBuilder out = new StringBuilder();
        for (byte b : digest.digest()) out.append(String.format(Locale.ROOT, "%02x", b & 0xff));
        return out.toString();
    }

    private void installUpdateApk(File apk) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O && !getPackageManager().canRequestPackageInstalls()) {
            pendingUpdateFile = apk;
            Intent settings = new Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,
                    Uri.parse("package:" + getPackageName()));
            Toast.makeText(this, "Ative 'Permitir desta fonte' e volte ao Helper.", Toast.LENGTH_LONG).show();
            startActivity(settings);
            return;
        }

        Uri uri = FileProvider.getUriForFile(this, getPackageName() + ".files", apk);
        Intent install = new Intent(Intent.ACTION_VIEW);
        install.setDataAndType(uri, "application/vnd.android.package-archive");
        install.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
        try {
            startActivity(install);
        } catch (ActivityNotFoundException ex) {
            Toast.makeText(this, "O instalador do Android não foi encontrado.", Toast.LENGTH_LONG).show();
        }
    }

'''
if methods_anchor not in text:
    raise SystemExit('sync method anchor not found')
text = text.replace(methods_anchor, methods + methods_anchor, 1)

old_load = '''    private Set<String> loadDurablePostedIds() {\n        Set<String> result = new HashSet<>();\n        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) return result;\n        Uri uri = findDurableStateUri();\n'''
new_load = '''    private Set<String> loadDurablePostedIds() {\n        Set<String> result = new HashSet<>();\n        String selected = getSharedPreferences(PREFS, MODE_PRIVATE).getString("history_backup_uri", "");\n        if (selected != null && !selected.isEmpty()) {\n            try { result.addAll(readPostedIdsFromUri(Uri.parse(selected))); } catch (Exception ignored) {}\n        }\n        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) return result;\n        Uri uri = findDurableStateUri();\n'''
if old_load not in text:
    raise SystemExit('load durable anchor not found')
text = text.replace(old_load, new_load, 1)

old_save = '''    private void saveDurablePostedIds(Set<String> posted) {\n        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) return;\n        try {\n'''
new_save = '''    private void saveDurablePostedIds(Set<String> posted) {\n        String selected = getSharedPreferences(PREFS, MODE_PRIVATE).getString("history_backup_uri", "");\n        if (selected != null && !selected.isEmpty()) {\n            try {\n                writePostedIdsToUri(Uri.parse(selected), posted);\n                return;\n            } catch (Exception ignored) {}\n        }\n        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) return;\n        try {\n'''
if old_save not in text:
    raise SystemExit('save durable anchor not found')
text = text.replace(old_save, new_save, 1)

java_path.write_text(text, encoding='utf-8')

gradle = gradle_path.read_text(encoding='utf-8')
gradle = gradle.replace('versionCode 10', 'versionCode 11')
gradle = gradle.replace("versionName '1.0.0'", "versionName '1.1.0'")
gradle_path.write_text(gradle, encoding='utf-8')

manifest = manifest_path.read_text(encoding='utf-8')
if 'android.permission.REQUEST_INSTALL_PACKAGES' not in manifest:
    manifest = manifest.replace(
        '    <uses-permission android:name="android.permission.INTERNET" />\n',
        '    <uses-permission android:name="android.permission.INTERNET" />\n    <uses-permission android:name="android.permission.REQUEST_INSTALL_PACKAGES" />\n')
manifest_path.write_text(manifest, encoding='utf-8')

paths = paths_path.read_text(encoding='utf-8')
if 'name="kwai_updates"' not in paths:
    paths = paths.replace(
        '    <external-files-path name="kwai_movies" path="Movies/" />\n',
        '    <external-files-path name="kwai_movies" path="Movies/" />\n    <external-files-path name="kwai_updates" path="Download/" />\n')
paths_path.write_text(paths, encoding='utf-8')

print('v11 updater + history import patch applied')

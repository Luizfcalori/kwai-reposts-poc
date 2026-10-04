package com.luizcalori.kwaihelper;

import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.ContentUris;
import android.content.ClipData;
import android.content.ContentValues;
import android.content.ClipboardManager;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Color;
import android.database.Cursor;
import android.net.Uri;
import android.os.Bundle;
import android.os.Build;
import android.os.Environment;
import android.provider.DocumentsContract;
import android.provider.MediaStore;
import android.provider.Settings;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import androidx.core.content.FileProvider;
import androidx.documentfile.provider.DocumentFile;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedInputStream;
import java.io.BufferedReader;
import java.io.File;
import java.io.FileOutputStream;
import java.io.FileInputStream;
import java.io.OutputStream;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.text.DateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends Activity {
    private static final String QUEUE_URL =
            "https://raw.githubusercontent.com/Luizfcalori/kwai-reposts-poc/main/data/kwai_queue.json";
    private static final String PREFS = "kwai_queue_state";
    private static final String PUBLIC_DOWNLOADED = Environment.DIRECTORY_MOVIES + "/KwaiHelper/Baixados";
    private static final String LEGACY_PUBLIC_PUBLISHED = Environment.DIRECTORY_MOVIES + "/KwaiHelper/Publicados/";
    private static final String STATE_RELATIVE_PATH = Environment.DIRECTORY_DOWNLOADS + "/KwaiHelper/";
    private static final String STATE_FILE_NAME = "kwaihelper_publicados.json";
    private static final String LATEST_INFO_URL =
            "https://raw.githubusercontent.com/Luizfcalori/kwai-reposts-poc/main/releases/latest.json";
    private static final String TRUSTED_APK_PREFIX =
            "https://raw.githubusercontent.com/Luizfcalori/kwai-reposts-poc/";
    private static final int REQ_IMPORT_HISTORY = 701;
    private static final int REQ_IMPORT_HISTORY_FOLDER = 702;

    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private final ExecutorService imageExecutor = Executors.newSingleThreadExecutor();
    private final ExecutorService updateExecutor = Executors.newSingleThreadExecutor();
    private final List<QueueItem> pending = new ArrayList<>();
    private final Object postedIdsLock = new Object();
    private Set<String> postedIdsCache = null;

    private TextView summaryLabel;
    private TextView sourceLabel;
    private TextView statusChip;
    private TextView status;
    private TextView historyLabel;
    private TextView thumbnailHint;
    private ImageView thumbnail;
    private EditText caption;
    private Button syncButton;
    private Button downloadButton;
    private Button copyButton;
    private Button shareButton;
    private Button postedButton;
    private Button skipButton;
    private Button alreadyPostedButton;
    private Button updateButton;
    private Button importHistoryButton;

    private QueueItem current;
    private File downloadedFile;
    private Uri publicMediaUri;
    private File pendingUpdateFile;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        migrateLegacyPublishedFolder();

        int pad = dp(16);
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setPadding(pad, pad, pad, pad);
        box.setBackgroundColor(Color.rgb(247, 247, 247));

        TextView title = new TextView(this);
        title.setText("Kwai Phone Helper v14");
        title.setTextSize(26);
        title.setTextColor(Color.rgb(25, 25, 25));
        title.setPadding(0, 0, 0, dp(4));
        box.addView(title);

        TextView subtitle = new TextView(this);
        subtitle.setText("Fila visual • download 1 por vez • legenda automática • postagem manual");
        subtitle.setTextSize(14);
        subtitle.setTextColor(Color.DKGRAY);
        subtitle.setPadding(0, 0, 0, dp(14));
        box.addView(subtitle);

        summaryLabel = new TextView(this);
        summaryLabel.setText("Pendentes: 0   •   Publicados: carregando...   •   Local: 0 MB");
        summaryLabel.setTextSize(15);
        summaryLabel.setTextColor(Color.rgb(55, 55, 55));
        summaryLabel.setPadding(dp(12), dp(10), dp(12), dp(10));
        summaryLabel.setBackgroundColor(Color.WHITE);
        box.addView(summaryLabel, fullWidth());

        syncButton = button("↻ Sincronizar fila e baixar próximo");
        syncButton.setOnClickListener(v -> syncQueue(true));
        box.addView(syncButton);

        updateButton = button("⬆ Atualizar app");
        updateButton.setOnClickListener(v -> checkForUpdate());

        importHistoryButton = button("🧹 Consolidar histórico");
        importHistoryButton.setOnClickListener(v -> chooseHistoryFolder());
        box.addView(actionRow(updateButton, importHistoryButton));

        TextView quickTitle = new TextView(this);
        quickTitle.setText("AÇÕES RÁPIDAS");
        quickTitle.setTextSize(13);
        quickTitle.setTextColor(Color.GRAY);
        quickTitle.setPadding(0, dp(8), 0, dp(3));
        box.addView(quickTitle);

        copyButton = button("📋 Copiar legenda");
        copyButton.setEnabled(false);
        copyButton.setOnClickListener(v -> copyCaption(true));

        shareButton = button("▶ Enviar ao Kwai");
        shareButton.setEnabled(false);
        shareButton.setOnClickListener(v -> shareCurrent());
        box.addView(actionRow(copyButton, shareButton));

        postedButton = button("✓ Publiquei — excluir");
        postedButton.setEnabled(false);
        postedButton.setOnClickListener(v -> markPostedAndDelete());

        alreadyPostedButton = button("⛔ Já publiquei");
        alreadyPostedButton.setEnabled(false);
        alreadyPostedButton.setOnClickListener(v -> markAlreadyPosted());
        box.addView(actionRow(postedButton, alreadyPostedButton));

        downloadButton = button("⬇ Baixar novamente");
        downloadButton.setEnabled(false);
        downloadButton.setOnClickListener(v -> downloadCurrent());

        skipButton = button("↪ Pular vídeo");
        skipButton.setEnabled(false);
        skipButton.setOnClickListener(v -> skipCurrent());
        box.addView(actionRow(downloadButton, skipButton));

        TextView cardTitle = new TextView(this);
        cardTitle.setText("PRÓXIMO VÍDEO");
        cardTitle.setTextSize(13);
        cardTitle.setTextColor(Color.GRAY);
        cardTitle.setPadding(0, dp(10), 0, dp(5));
        box.addView(cardTitle);

        thumbnail = new ImageView(this);
        thumbnail.setBackgroundColor(Color.rgb(225, 225, 225));
        thumbnail.setScaleType(ImageView.ScaleType.FIT_CENTER);
        LinearLayout.LayoutParams imageParams = new LinearLayout.LayoutParams(-1, dp(280));
        box.addView(thumbnail, imageParams);

        thumbnailHint = new TextView(this);
        thumbnailHint.setText("Sincronize para carregar a miniatura");
        thumbnailHint.setGravity(Gravity.CENTER);
        thumbnailHint.setTextColor(Color.GRAY);
        thumbnailHint.setPadding(0, dp(3), 0, dp(5));
        box.addView(thumbnailHint);

        sourceLabel = new TextView(this);
        sourceLabel.setText("Nenhum vídeo carregado");
        sourceLabel.setTextSize(17);
        sourceLabel.setTextColor(Color.BLACK);
        sourceLabel.setPadding(0, dp(3), 0, dp(3));
        box.addView(sourceLabel);

        statusChip = new TextView(this);
        statusChip.setText("AGUARDANDO SINCRONIZAÇÃO");
        statusChip.setTextSize(12);
        statusChip.setTextColor(Color.rgb(90, 90, 90));
        statusChip.setPadding(dp(8), dp(5), dp(8), dp(5));
        statusChip.setBackgroundColor(Color.rgb(235, 235, 235));
        box.addView(statusChip);

        TextView captionTitle = new TextView(this);
        captionTitle.setText("Legenda + hashtags");
        captionTitle.setTextSize(15);
        captionTitle.setTextColor(Color.DKGRAY);
        captionTitle.setPadding(0, dp(10), 0, dp(4));
        box.addView(captionTitle);

        caption = new EditText(this);
        caption.setHint("A legenda aparecerá aqui automaticamente");
        caption.setMinLines(4);
        caption.setGravity(Gravity.TOP);
        caption.setBackgroundColor(Color.WHITE);
        caption.setPadding(dp(12), dp(10), dp(12), dp(10));
        box.addView(caption, fullWidth());

        TextView foldersTitle = new TextView(this);
        foldersTitle.setText("PASTAS NO CELULAR");
        foldersTitle.setTextSize(13);
        foldersTitle.setTextColor(Color.GRAY);
        foldersTitle.setPadding(0, dp(10), 0, dp(4));
        box.addView(foldersTitle);

        Button openDownloaded = button("📂 Abrir KwaiHelper/Baixados");
        openDownloaded.setOnClickListener(v -> openPublicFolder("Movies/KwaiHelper/Baixados"));
        box.addView(openDownloaded);

        status = new TextView(this);
        status.setText("Pronto para sincronizar.");
        status.setTextSize(14);
        status.setTextColor(Color.rgb(65, 65, 65));
        status.setPadding(0, dp(12), 0, dp(12));
        box.addView(status);

        TextView historyTitle = new TextView(this);
        historyTitle.setText("ÚLTIMOS PUBLICADOS");
        historyTitle.setTextSize(13);
        historyTitle.setTextColor(Color.GRAY);
        historyTitle.setPadding(0, dp(4), 0, dp(5));
        box.addView(historyTitle);

        historyLabel = new TextView(this);
        historyLabel.setTextColor(Color.DKGRAY);
        historyLabel.setPadding(dp(10), dp(8), dp(10), dp(8));
        historyLabel.setBackgroundColor(Color.WHITE);
        box.addView(historyLabel, fullWidth());
        refreshHistory();

        ScrollView scroll = new ScrollView(this);
        scroll.addView(box);
        setContentView(scroll);
        warmPostedIdsCache();
    }

    private LinearLayout.LayoutParams fullWidth() {
        return new LinearLayout.LayoutParams(-1, -2);
    }

    private Button button(String text) {
        Button b = new Button(this);
        b.setText(text);
        b.setAllCaps(false);
        b.setTextSize(15);
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(-1, -2);
        p.setMargins(0, dp(5), 0, dp(5));
        b.setLayoutParams(p);
        return b;
    }

    private LinearLayout actionRow(Button left, Button right) {
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setGravity(Gravity.CENTER_VERTICAL);
        LinearLayout.LayoutParams rowParams = new LinearLayout.LayoutParams(-1, -2);
        rowParams.setMargins(0, dp(2), 0, dp(2));
        row.setLayoutParams(rowParams);

        LinearLayout.LayoutParams leftParams = new LinearLayout.LayoutParams(0, -2, 1f);
        leftParams.setMargins(0, 0, dp(3), 0);
        LinearLayout.LayoutParams rightParams = new LinearLayout.LayoutParams(0, -2, 1f);
        rightParams.setMargins(dp(3), 0, 0, 0);
        row.addView(left, leftParams);
        row.addView(right, rightParams);
        return row;
    }

    @Override
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

    private void chooseHistoryFolder() {
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT_TREE);
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_WRITE_URI_PERMISSION
                | Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            try {
                Uri initial = DocumentsContract.buildDocumentUri(
                        "com.android.externalstorage.documents",
                        "primary:" + Environment.DIRECTORY_DOWNLOADS + "/KwaiHelper");
                intent.putExtra(DocumentsContract.EXTRA_INITIAL_URI, initial);
            } catch (Exception ignored) {}
        }
        startActivityForResult(intent, REQ_IMPORT_HISTORY_FOLDER);
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
        if (requestCode == REQ_IMPORT_HISTORY_FOLDER) {
            if (resultCode != RESULT_OK || data == null || data.getData() == null) return;
            Uri folderUri = data.getData();
            try {
                int flags = data.getFlags() & (Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_WRITE_URI_PERMISSION);
                getContentResolver().takePersistableUriPermission(folderUri, flags);
            } catch (Exception ignored) {}
            consolidateHistoryFolder(folderUri);
            return;
        }
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
            setPostedIdsCache(merged);
            saveDurablePostedIds(merged);
            int added = merged.size() - before;
            Toast.makeText(this, "Histórico importado: " + added + " IDs recuperados.", Toast.LENGTH_LONG).show();
            updateSummary();
            syncQueue(true);
        } catch (Exception exc) {
            Toast.makeText(this, "Falha ao importar histórico: " + shortMessage(exc), Toast.LENGTH_LONG).show();
        }
    }

    private void consolidateHistoryFolder(Uri folderUri) {
        try {
            DocumentFile folder = DocumentFile.fromTreeUri(this, folderUri);
            if (folder == null || !folder.isDirectory()) {
                Toast.makeText(this, "Escolha a pasta Downloads/KwaiHelper.", Toast.LENGTH_LONG).show();
                return;
            }

            Set<String> merged = new HashSet<>(getPostedIds());
            List<DocumentFile> historyFiles = new ArrayList<>();
            DocumentFile canonical = null;

            for (DocumentFile file : folder.listFiles()) {
                if (!file.isFile()) continue;
                String name = file.getName();
                if (name == null) continue;
                String lower = name.toLowerCase(Locale.ROOT);
                if (!lower.startsWith("kwaihelper_publicados") || !lower.endsWith(".json")) continue;
                historyFiles.add(file);
                try { merged.addAll(readPostedIdsFromUri(file.getUri())); } catch (Exception ignored) {}
                if (STATE_FILE_NAME.equals(name)) canonical = file;
            }

            if (canonical == null) {
                canonical = folder.createFile("application/json", STATE_FILE_NAME);
            }
            if (canonical == null) throw new IllegalStateException("Não consegui criar o histórico mestre.");

            writePostedIdsToUri(canonical.getUri(), merged);
            int removed = 0;
            for (DocumentFile file : historyFiles) {
                if (file.getUri().equals(canonical.getUri())) continue;
                try { if (file.delete()) removed++; } catch (Exception ignored) {}
            }

            getSharedPreferences(PREFS, MODE_PRIVATE).edit()
                    .putString("history_folder_uri", folderUri.toString())
                    .putString("history_backup_uri", canonical.getUri().toString())
                    .putStringSet("posted_ids", new HashSet<>(merged))
                    .apply();
            setPostedIdsCache(merged);

            Toast.makeText(this, "Histórico consolidado: " + merged.size() + " IDs • " + removed + " duplicados removidos.", Toast.LENGTH_LONG).show();
            updateSummary();
            syncQueue(true);
        } catch (Exception exc) {
            Toast.makeText(this, "Falha ao consolidar histórico: " + shortMessage(exc), Toast.LENGTH_LONG).show();
        }
    }

    private Set<String> readPostedIdsFromHistoryFolder(Uri folderUri) {
        Set<String> result = new HashSet<>();
        try {
            DocumentFile folder = DocumentFile.fromTreeUri(this, folderUri);
            if (folder == null || !folder.isDirectory()) return result;
            for (DocumentFile file : folder.listFiles()) {
                if (!file.isFile()) continue;
                String name = file.getName();
                if (name == null) continue;
                String lower = name.toLowerCase(Locale.ROOT);
                if (lower.startsWith("kwaihelper_publicados") && lower.endsWith(".json")) {
                    try { result.addAll(readPostedIdsFromUri(file.getUri())); } catch (Exception ignored) {}
                }
            }
        } catch (Exception ignored) {}
        return result;
    }

    private boolean writePostedIdsToHistoryFolder(Uri folderUri, Set<String> posted) {
        try {
            DocumentFile folder = DocumentFile.fromTreeUri(this, folderUri);
            if (folder == null || !folder.isDirectory()) return false;
            DocumentFile canonical = folder.findFile(STATE_FILE_NAME);
            if (canonical == null) canonical = folder.createFile("application/json", STATE_FILE_NAME);
            if (canonical == null) return false;
            writePostedIdsToUri(canonical.getUri(), posted);
            getSharedPreferences(PREFS, MODE_PRIVATE).edit()
                    .putString("history_backup_uri", canonical.getUri().toString())
                    .apply();
            return true;
        } catch (Exception ignored) {
            return false;
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
        install.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_ACTIVITY_NEW_TASK);
        startActivity(install);
    }

    private void syncQueue(boolean downloadAfterSync) {
        setStatus("Sincronizando os canais autorizados...");
        setChip("SINCRONIZANDO");
        syncButton.setEnabled(false);

        executor.execute(() -> {
            HttpURLConnection connection = null;
            try {
                URL url = new URL(QUEUE_URL + "?t=" + System.currentTimeMillis());
                connection = (HttpURLConnection) url.openConnection();
                connection.setConnectTimeout(20000);
                connection.setReadTimeout(30000);
                connection.setRequestProperty("User-Agent", "KwaiPhoneHelper/1.0 Android");
                connection.setUseCaches(false);

                StringBuilder jsonText = new StringBuilder();
                try (BufferedReader reader = new BufferedReader(
                        new InputStreamReader(connection.getInputStream(), StandardCharsets.UTF_8))) {
                    String line;
                    while ((line = reader.readLine()) != null) {
                        jsonText.append(line).append('\n');
                    }
                }

                JSONObject root = new JSONObject(jsonText.toString());
                JSONArray items = root.optJSONArray("items");
                List<QueueItem> fresh = new ArrayList<>();
                Set<String> postedIds = getPostedIds();

                if (items != null) {
                    for (int i = 0; i < items.length(); i++) {
                        JSONObject obj = items.optJSONObject(i);
                        if (obj == null || !obj.optBoolean("rights_confirmed", false)) continue;
                        if (!"ready_for_phone".equals(obj.optString("status"))) continue;

                        String mediaUrl = obj.optString("media_url", "");
                        if (!mediaUrl.startsWith("http")) continue;

                        QueueItem item = new QueueItem();
                        item.sourceId = obj.optString("source_id", "source");
                        item.sourceName = obj.optString("source_display_name", obj.optString("source_handle", "Kwai"));
                        item.videoId = obj.optString("video_id", "");
                        item.videoUrl = obj.optString("video_url", "");
                        item.mediaUrl = mediaUrl;
                        item.thumbnailUrl = obj.optString("thumbnail_url", "");
                        item.postText = obj.optString("post_text", "");

                        if (item.postText.isEmpty()) {
                            item.postText = obj.optString("generated_caption", "");
                            JSONArray tags = obj.optJSONArray("hashtags");
                            if (tags != null && tags.length() > 0) {
                                StringBuilder tagText = new StringBuilder();
                                for (int t = 0; t < tags.length(); t++) {
                                    if (tagText.length() > 0) tagText.append(' ');
                                    tagText.append(tags.optString(t));
                                }
                                if (tagText.length() > 0) item.postText += "\n\n" + tagText;
                            }
                        }

                        if (!item.videoId.isEmpty() && !postedIds.contains(item.key())) fresh.add(item);
                    }
                }

                List<QueueItem> balanced = roundRobinBySource(fresh);
                runOnUiThread(() -> {
                    pending.clear();
                    pending.addAll(balanced);
                    syncButton.setEnabled(true);
                    selectFirstPending();
                    updateSummary();
                    if (current == null) {
                        setStatus("Nenhum vídeo novo pronto para o celular.");
                        setChip("FILA VAZIA");
                    } else if (downloadAfterSync) {
                        downloadCurrent();
                    }
                });
            } catch (Exception exc) {
                runOnUiThread(() -> {
                    syncButton.setEnabled(true);
                    setStatus("Falha ao sincronizar: " + shortMessage(exc));
                    setChip("ERRO DE SINCRONIZAÇÃO");
                });
            } finally {
                if (connection != null) connection.disconnect();
            }
        });
    }

    private List<QueueItem> roundRobinBySource(List<QueueItem> input) {
        Map<String, List<QueueItem>> groups = new LinkedHashMap<>();
        for (QueueItem item : input) {
            groups.computeIfAbsent(item.sourceId, key -> new ArrayList<>()).add(item);
        }

        List<QueueItem> result = new ArrayList<>();
        int index = 0;
        boolean added;
        do {
            added = false;
            for (List<QueueItem> group : groups.values()) {
                if (index < group.size()) {
                    result.add(group.get(index));
                    added = true;
                }
            }
            index++;
        } while (added);
        return result;
    }

    private void selectFirstPending() {
        downloadedFile = null;
        publicMediaUri = null;
        shareButton.setEnabled(false);
        postedButton.setEnabled(false);
        thumbnail.setImageDrawable(null);
        thumbnail.setBackgroundColor(Color.rgb(225, 225, 225));

        if (pending.isEmpty()) {
            current = null;
            sourceLabel.setText("Nenhum vídeo pendente");
            caption.setText("");
            thumbnailHint.setText("Fila concluída");
            downloadButton.setEnabled(false);
            copyButton.setEnabled(false);
            skipButton.setEnabled(false);
            alreadyPostedButton.setEnabled(false);
            updateSummary();
            return;
        }

        current = pending.get(0);
        sourceLabel.setText(current.sourceName + "  •  vídeo " + current.videoId);
        caption.setText(current.postText);
        copyButton.setEnabled(!current.postText.trim().isEmpty());
        downloadButton.setEnabled(true);
        skipButton.setEnabled(pending.size() > 1);
        alreadyPostedButton.setEnabled(true);
        setChip("AGUARDANDO DOWNLOAD");
        loadThumbnail(current);
        updateSummary();
    }

    private void loadThumbnail(QueueItem item) {
        if (item == null || item.thumbnailUrl == null || !item.thumbnailUrl.startsWith("http")) {
            thumbnailHint.setText("Miniatura não disponível");
            return;
        }

        thumbnailHint.setText("Carregando miniatura...");
        String expectedKey = item.key();
        imageExecutor.execute(() -> {
            HttpURLConnection connection = null;
            try {
                connection = (HttpURLConnection) new URL(item.thumbnailUrl).openConnection();
                connection.setConnectTimeout(15000);
                connection.setReadTimeout(20000);
                connection.setRequestProperty("User-Agent", "KwaiPhoneHelper/1.0 Android");
                Bitmap bitmap;
                try (InputStream input = new BufferedInputStream(connection.getInputStream())) {
                    bitmap = BitmapFactory.decodeStream(input);
                }
                if (bitmap != null) {
                    runOnUiThread(() -> {
                        if (current != null && expectedKey.equals(current.key())) {
                            thumbnail.setImageBitmap(bitmap);
                            thumbnailHint.setText("Prévia do vídeo");
                        }
                    });
                }
            } catch (Exception ignored) {
                runOnUiThread(() -> {
                    if (current != null && expectedKey.equals(current.key())) {
                        thumbnailHint.setText("Não consegui carregar a miniatura");
                    }
                });
            } finally {
                if (connection != null) connection.disconnect();
            }
        });
    }

    private void downloadCurrent() {
        QueueItem item = current;
        if (item == null) {
            Toast.makeText(this, "Sincronize a fila primeiro.", Toast.LENGTH_LONG).show();
            return;
        }

        setStatus("Baixando vídeo de " + item.sourceName + "...");
        setChip("BAIXANDO");
        downloadButton.setEnabled(false);
        shareButton.setEnabled(false);
        postedButton.setEnabled(false);

        executor.execute(() -> {
            HttpURLConnection connection = null;
            File partial = null;
            try {
                File base = videoFolder();
                if (!base.exists() && !base.mkdirs()) {
                    throw new IllegalStateException("Não foi possível criar a pasta local.");
                }

                File target = new File(base, safeFileName(item.sourceId + "_" + item.videoId) + ".mp4");
                partial = new File(base, target.getName() + ".part");
                if (partial.exists()) partial.delete();

                connection = (HttpURLConnection) new URL(item.mediaUrl).openConnection();
                connection.setConnectTimeout(25000);
                connection.setReadTimeout(90000);
                connection.setRequestProperty("User-Agent", "Mozilla/5.0 (Linux; Android) KwaiPhoneHelper/1.0");
                connection.setInstanceFollowRedirects(true);

                int response = connection.getResponseCode();
                if (response < 200 || response >= 300) {
                    throw new IllegalStateException("Servidor respondeu HTTP " + response + ". Sincronize novamente.");
                }

                long total = 0;
                try (InputStream input = new BufferedInputStream(connection.getInputStream());
                     FileOutputStream output = new FileOutputStream(partial)) {
                    byte[] buffer = new byte[64 * 1024];
                    int read;
                    while ((read = input.read(buffer)) != -1) {
                        output.write(buffer, 0, read);
                        total += read;
                    }
                    output.flush();
                }

                if (total < 1024) throw new IllegalStateException("O arquivo recebido parece inválido.");
                if (target.exists()) target.delete();
                if (!partial.renameTo(target)) throw new IllegalStateException("Não foi possível finalizar o arquivo.");

                downloadedFile = target;
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
            } catch (Exception exc) {
                if (partial != null && partial.exists()) partial.delete();
                runOnUiThread(() -> {
                    downloadButton.setEnabled(true);
                    setStatus("Falha no download: " + shortMessage(exc));
                    setChip("ERRO NO DOWNLOAD");
                    updateSummary();
                });
            } finally {
                if (connection != null) connection.disconnect();
            }
        });
    }

    private boolean copyCaption(boolean showToast) {
        String text = caption.getText().toString().trim();
        if (text.isEmpty()) {
            if (showToast) Toast.makeText(this, "A legenda está vazia.", Toast.LENGTH_LONG).show();
            return false;
        }

        ClipboardManager clipboard = (ClipboardManager) getSystemService(CLIPBOARD_SERVICE);
        clipboard.setPrimaryClip(ClipData.newPlainText("Legenda Kwai", text));
        setChip("LEGENDA COPIADA ✓");
        setStatus("Legenda + hashtags copiadas. No Kwai, toque no campo de descrição e use Colar.");
        if (showToast) Toast.makeText(this, "Legenda + hashtags copiadas ✓", Toast.LENGTH_SHORT).show();
        return true;
    }

    private void shareCurrent() {
        if (current == null || downloadedFile == null || !downloadedFile.exists()) {
            Toast.makeText(this, "Baixe o vídeo antes de enviar.", Toast.LENGTH_LONG).show();
            return;
        }

        String text = caption.getText().toString().trim();
        if (!text.isEmpty()) copyCaption(false);

        Uri videoUri = FileProvider.getUriForFile(this, getPackageName() + ".files", downloadedFile);
        Intent share = new Intent(Intent.ACTION_SEND);
        share.setType("video/mp4");
        share.putExtra(Intent.EXTRA_STREAM, videoUri);
        if (!text.isEmpty()) share.putExtra(Intent.EXTRA_TEXT, text);
        share.setClipData(ClipData.newUri(getContentResolver(), "video", videoUri));
        share.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);

        try {
            startActivity(Intent.createChooser(share, "Escolha o Kwai"));
            setStatus("Vídeo enviado. A legenda está copiada — cole no campo de descrição do Kwai.");
            setChip("ENVIADO AO KWAI • TEXTO COPIADO");
        } catch (ActivityNotFoundException ex) {
            Toast.makeText(this, "Nenhum aplicativo compatível foi encontrado.", Toast.LENGTH_LONG).show();
        }
    }

    private void markPostedAndDelete() {
        if (current == null) return;

        QueueItem postedItem = current;
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

        if (!pending.isEmpty()) pending.remove(0);
        downloadedFile = null;
        refreshHistory();
        selectFirstPending();

        if (current != null) {
            setStatus("Publicado ✓ Vídeo excluído definitivamente do celular. Preparando o próximo...");
            downloadCurrent();
        } else {
            setStatus("Fila concluída. Toque em Sincronizar para verificar novidades.");
            setChip("FILA CONCLUÍDA");
        }
        updateSummary();
    }

    private void markAlreadyPosted() {
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

    private void skipCurrent() {
        if (current == null || pending.size() <= 1) {
            Toast.makeText(this, "Não há outro vídeo na fila agora.", Toast.LENGTH_SHORT).show();
            return;
        }

        if (downloadedFile != null && downloadedFile.exists()) downloadedFile.delete();
        if (publicMediaUri != null) {
            try { getContentResolver().delete(publicMediaUri, null, null); } catch (Exception ignored) {}
            publicMediaUri = null;
        }
        QueueItem skipped = pending.remove(0);
        pending.add(skipped);
        downloadedFile = null;
        selectFirstPending();
        setStatus("Vídeo pulado nesta sessão. Preparando o próximo...");
        downloadCurrent();
    }

    private File videoFolder() {
        File root = getExternalFilesDir(Environment.DIRECTORY_MOVIES);
        if (root == null) root = getFilesDir();
        return new File(root, "KwaiHelper");
    }

    private Uri copyToPublicFolder(File source, String relativePath) throws Exception {
        ContentValues values = new ContentValues();
        values.put(MediaStore.Video.Media.DISPLAY_NAME, source.getName());
        values.put(MediaStore.Video.Media.MIME_TYPE, "video/mp4");
        values.put(MediaStore.Video.Media.RELATIVE_PATH, relativePath);
        values.put(MediaStore.Video.Media.IS_PENDING, 1);

        Uri uri = getContentResolver().insert(MediaStore.Video.Media.EXTERNAL_CONTENT_URI, values);
        if (uri == null) throw new IllegalStateException("MediaStore não criou o arquivo.");

        try {
            try (InputStream input = new BufferedInputStream(new FileInputStream(source));
                 OutputStream output = getContentResolver().openOutputStream(uri, "w")) {
                if (output == null) throw new IllegalStateException("Não foi possível abrir o destino.");
                byte[] buffer = new byte[64 * 1024];
                int read;
                while ((read = input.read(buffer)) != -1) output.write(buffer, 0, read);
                output.flush();
            }
            ContentValues ready = new ContentValues();
            ready.put(MediaStore.Video.Media.IS_PENDING, 0);
            getContentResolver().update(uri, ready, null, null);
            return uri;
        } catch (Exception exc) {
            try { getContentResolver().delete(uri, null, null); } catch (Exception ignored) {}
            throw exc;
        }
    }

    private void openPublicFolder(String initialPath) {
        try {
            Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT_TREE);
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                Uri initial = DocumentsContract.buildDocumentUri(
                        "com.android.externalstorage.documents",
                        "primary:" + initialPath);
                intent.putExtra(DocumentsContract.EXTRA_INITIAL_URI, initial);
            }
            startActivity(intent);
        } catch (Exception exc) {
            Toast.makeText(this, "Abra Meus Arquivos > Armazenamento interno > Movies > KwaiHelper > Baixados.", Toast.LENGTH_LONG).show();
        }
    }

    private void migrateLegacyPublishedFolder() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) return;
        executor.execute(() -> {
            Set<String> migrated = getPostedIds();
            boolean changed = false;
            Cursor cursor = null;
            try {
                String[] projection = {
                        MediaStore.Video.Media._ID,
                        MediaStore.Video.Media.DISPLAY_NAME
                };
                String selection = MediaStore.Video.Media.RELATIVE_PATH + "=?";
                String[] args = { LEGACY_PUBLIC_PUBLISHED };
                cursor = getContentResolver().query(
                        MediaStore.Video.Media.EXTERNAL_CONTENT_URI,
                        projection,
                        selection,
                        args,
                        null);
                if (cursor != null) {
                    int idCol = cursor.getColumnIndexOrThrow(MediaStore.Video.Media._ID);
                    int nameCol = cursor.getColumnIndexOrThrow(MediaStore.Video.Media.DISPLAY_NAME);
                    while (cursor.moveToNext()) {
                        long rowId = cursor.getLong(idCol);
                        String displayName = cursor.getString(nameCol);
                        String key = keyFromDownloadedFileName(displayName);
                        if (key != null && !key.isEmpty()) {
                            migrated.add(key);
                            changed = true;
                        }
                        Uri uri = ContentUris.withAppendedId(MediaStore.Video.Media.EXTERNAL_CONTENT_URI, rowId);
                        try { getContentResolver().delete(uri, null, null); } catch (Exception ignored) {}
                    }
                }
            } catch (Exception ignored) {
            } finally {
                if (cursor != null) cursor.close();
            }
            if (changed) {
                persistPostedIds(migrated);
                runOnUiThread(() -> {
                    refreshHistory();
                    updateSummary();
                });
            }
        });
    }

    private String keyFromDownloadedFileName(String displayName) {
        if (displayName == null) return null;
        String clean = displayName;
        if (clean.endsWith(".mp4")) clean = clean.substring(0, clean.length() - 4);
        int underscore = clean.lastIndexOf('_');
        if (underscore <= 0 || underscore >= clean.length() - 1) return null;
        String source = clean.substring(0, underscore);
        String video = clean.substring(underscore + 1);
        if (!video.matches("\\d+")) return null;
        return source + ":" + video;
    }

    private void warmPostedIdsCache() {
        executor.execute(() -> {
            getPostedIds();
            runOnUiThread(this::updateSummary);
        });
    }

    private void setPostedIdsCache(Set<String> ids) {
        synchronized (postedIdsLock) {
            postedIdsCache = new HashSet<>(ids);
        }
    }

    private Set<String> getPostedIds() {
        synchronized (postedIdsLock) {
            if (postedIdsCache != null) return new HashSet<>(postedIdsCache);
        }

        SharedPreferences prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        Set<String> result = new HashSet<>(prefs.getStringSet("posted_ids", new HashSet<>()));
        result.addAll(readDurablePostedIds());
        String folderUri = prefs.getString("history_folder_uri", "");
        if (folderUri != null && !folderUri.isEmpty()) {
            result.addAll(readPostedIdsFromHistoryFolder(Uri.parse(folderUri)));
        }
        String backupUri = prefs.getString("history_backup_uri", "");
        if (backupUri != null && !backupUri.isEmpty()) {
            try {
                result.addAll(readPostedIdsFromUri(Uri.parse(backupUri)));
            } catch (Exception ignored) {
            }
        }

        synchronized (postedIdsLock) {
            if (postedIdsCache == null) postedIdsCache = new HashSet<>(result);
            else postedIdsCache.addAll(result);
            return new HashSet<>(postedIdsCache);
        }
    }

    private Set<String> readDurablePostedIds() {
        Set<String> result = new HashSet<>();
        Cursor cursor = null;
        try {
            Uri collection = MediaStore.Downloads.EXTERNAL_CONTENT_URI;
            String[] projection = { MediaStore.Downloads._ID, MediaStore.Downloads.DISPLAY_NAME };
            String selection = MediaStore.Downloads.RELATIVE_PATH + "=? AND "
                    + MediaStore.Downloads.DISPLAY_NAME + " LIKE ?";
            String[] args = { STATE_RELATIVE_PATH, "kwaihelper_publicados%" };
            cursor = getContentResolver().query(collection, projection, selection, args, null);
            if (cursor == null) return result;
            int idCol = cursor.getColumnIndexOrThrow(MediaStore.Downloads._ID);
            while (cursor.moveToNext()) {
                long id = cursor.getLong(idCol);
                Uri uri = ContentUris.withAppendedId(collection, id);
                try { result.addAll(readPostedIdsFromUri(uri)); } catch (Exception ignored) {}
            }
        } catch (Exception ignored) {
        } finally {
            if (cursor != null) cursor.close();
        }
        return result;
    }

    private void persistPostedIds(Set<String> posted) {
        Set<String> safe = new HashSet<>(posted);
        setPostedIdsCache(safe);
        SharedPreferences prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        prefs.edit().putStringSet("posted_ids", safe).apply();
        String folderUri = prefs.getString("history_folder_uri", "");
        boolean savedToFolder = false;
        if (folderUri != null && !folderUri.isEmpty()) {
            savedToFolder = writePostedIdsToHistoryFolder(Uri.parse(folderUri), safe);
        }
        if (!savedToFolder) saveDurablePostedIds(safe);
        String backupUri = prefs.getString("history_backup_uri", "");
        if (backupUri != null && !backupUri.isEmpty()) {
            try {
                writePostedIdsToUri(Uri.parse(backupUri), safe);
            } catch (Exception ignored) {
            }
        }
    }

    private void saveDurablePostedIds(Set<String> posted) {
        Cursor cursor = null;
        Uri uri = null;
        Set<String> merged = new HashSet<>(posted);
        try {
            Uri collection = MediaStore.Downloads.EXTERNAL_CONTENT_URI;
            String[] projection = { MediaStore.Downloads._ID, MediaStore.Downloads.DISPLAY_NAME };
            String selection = MediaStore.Downloads.RELATIVE_PATH + "=? AND "
                    + MediaStore.Downloads.DISPLAY_NAME + " LIKE ?";
            String[] args = { STATE_RELATIVE_PATH, "kwaihelper_publicados%" };
            cursor = getContentResolver().query(collection, projection, selection, args, null);
            if (cursor != null) {
                int idCol = cursor.getColumnIndexOrThrow(MediaStore.Downloads._ID);
                while (cursor.moveToNext()) {
                    long id = cursor.getLong(idCol);
                    Uri candidate = ContentUris.withAppendedId(collection, id);
                    if (uri == null) uri = candidate;
                    try { merged.addAll(readPostedIdsFromUri(candidate)); } catch (Exception ignored) {}
                }
                cursor.close();
                cursor = null;
            }
            if (uri == null) {
                ContentValues values = new ContentValues();
                values.put(MediaStore.Downloads.DISPLAY_NAME, STATE_FILE_NAME);
                values.put(MediaStore.Downloads.MIME_TYPE, "application/json");
                values.put(MediaStore.Downloads.RELATIVE_PATH, STATE_RELATIVE_PATH);
                uri = getContentResolver().insert(collection, values);
            }
            if (uri == null) return;
            writePostedIdsToUri(uri, merged);
        } catch (Exception ignored) {
        } finally {
            if (cursor != null) cursor.close();
        }
    }

    private void appendHistory(QueueItem item) {
        SharedPreferences prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        String currentHistory = prefs.getString("history", "");
        String line = DateFormat.getDateTimeInstance(DateFormat.SHORT, DateFormat.SHORT)
                .format(new Date()) + "  •  " + item.sourceName + "  •  " + item.videoId;
        String merged = line + (currentHistory.isEmpty() ? "" : "\n" + currentHistory);
        String[] lines = merged.split("\n");
        StringBuilder limited = new StringBuilder();
        for (int i = 0; i < Math.min(lines.length, 8); i++) {
            if (i > 0) limited.append('\n');
            limited.append(lines[i]);
        }
        prefs.edit().putString("history", limited.toString()).apply();
    }

    private void refreshHistory() {
        String history = getSharedPreferences(PREFS, MODE_PRIVATE).getString("history", "");
        historyLabel.setText(history == null || history.trim().isEmpty()
                ? "Ainda não há publicações registradas nesta instalação."
                : history);
    }

    private void updateSummary() {
        long bytes = folderBytes(videoFolder());
        summaryLabel.setText(String.format(Locale.getDefault(),
                "Pendentes: %d   •   Publicados: %d   •   Local: %.1f MB",
                pending.size(), getPostedIds().size(), bytes / 1024d / 1024d));
    }

    private long folderBytes(File folder) {
        if (folder == null || !folder.exists()) return 0;
        File[] files = folder.listFiles();
        if (files == null) return 0;
        long total = 0;
        for (File file : files) {
            if (file.isFile()) total += file.length();
        }
        return total;
    }

    private void setStatus(String value) {
        status.setText(value);
    }

    private void setChip(String value) {
        statusChip.setText(value);
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    private String safeFileName(String value) {
        return value.replaceAll("[^a-zA-Z0-9._-]", "_");
    }

    private String shortMessage(Throwable error) {
        String message = error.getMessage();
        if (message == null || message.trim().isEmpty()) return error.getClass().getSimpleName();
        return message.length() > 150 ? message.substring(0, 150) : message;
    }

    private static final class QueueItem {
        String sourceId;
        String sourceName;
        String videoId;
        String videoUrl;
        String mediaUrl;
        String thumbnailUrl;
        String postText;

        String key() {
            return sourceId + ":" + videoId;
        }
    }
}

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

    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private final ExecutorService imageExecutor = Executors.newSingleThreadExecutor();
    private final List<QueueItem> pending = new ArrayList<>();

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

    private QueueItem current;
    private File downloadedFile;
    private Uri publicMediaUri;

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
        title.setText("Kwai Phone Helper v9");
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
        summaryLabel.setText("Pendentes: 0   •   Publicados: " + getPostedIds().size() + "   •   Local: 0 MB");
        summaryLabel.setTextSize(15);
        summaryLabel.setTextColor(Color.rgb(55, 55, 55));
        summaryLabel.setPadding(dp(12), dp(10), dp(12), dp(10));
        summaryLabel.setBackgroundColor(Color.WHITE);
        box.addView(summaryLabel, fullWidth());

        syncButton = button("↻ Sincronizar fila e baixar próximo");
        syncButton.setOnClickListener(v -> syncQueue(true));
        box.addView(syncButton);

        TextView cardTitle = new TextView(this);
        cardTitle.setText("PRÓXIMO VÍDEO");
        cardTitle.setTextSize(13);
        cardTitle.setTextColor(Color.GRAY);
        cardTitle.setPadding(0, dp(12), 0, dp(6));
        box.addView(cardTitle);

        thumbnail = new ImageView(this);
        thumbnail.setBackgroundColor(Color.rgb(225, 225, 225));
        thumbnail.setScaleType(ImageView.ScaleType.CENTER_CROP);
        LinearLayout.LayoutParams imageParams = new LinearLayout.LayoutParams(-1, dp(220));
        box.addView(thumbnail, imageParams);

        thumbnailHint = new TextView(this);
        thumbnailHint.setText("Sincronize para carregar a miniatura");
        thumbnailHint.setGravity(Gravity.CENTER);
        thumbnailHint.setTextColor(Color.GRAY);
        thumbnailHint.setPadding(0, dp(4), 0, dp(8));
        box.addView(thumbnailHint);

        sourceLabel = new TextView(this);
        sourceLabel.setText("Nenhum vídeo carregado");
        sourceLabel.setTextSize(19);
        sourceLabel.setTextColor(Color.BLACK);
        sourceLabel.setPadding(0, dp(4), 0, dp(4));
        box.addView(sourceLabel);

        statusChip = new TextView(this);
        statusChip.setText("AGUARDANDO SINCRONIZAÇÃO");
        statusChip.setTextSize(13);
        statusChip.setTextColor(Color.rgb(90, 90, 90));
        statusChip.setPadding(dp(10), dp(6), dp(10), dp(6));
        statusChip.setBackgroundColor(Color.rgb(235, 235, 235));
        box.addView(statusChip);

        TextView captionTitle = new TextView(this);
        captionTitle.setText("Legenda + hashtags");
        captionTitle.setTextSize(15);
        captionTitle.setTextColor(Color.DKGRAY);
        captionTitle.setPadding(0, dp(12), 0, dp(4));
        box.addView(captionTitle);

        caption = new EditText(this);
        caption.setHint("A legenda aparecerá aqui automaticamente");
        caption.setMinLines(5);
        caption.setGravity(Gravity.TOP);
        caption.setBackgroundColor(Color.WHITE);
        caption.setPadding(dp(12), dp(10), dp(12), dp(10));
        box.addView(caption, fullWidth());

        copyButton = button("📋 Copiar legenda + hashtags");
        copyButton.setEnabled(false);
        copyButton.setOnClickListener(v -> copyCaption(true));
        box.addView(copyButton);

        downloadButton = button("⬇ Baixar novamente");
        downloadButton.setEnabled(false);
        downloadButton.setOnClickListener(v -> downloadCurrent());
        box.addView(downloadButton);

        shareButton = button("▶ Enviar vídeo para o Kwai");
        shareButton.setEnabled(false);
        shareButton.setOnClickListener(v -> shareCurrent());
        box.addView(shareButton);

        postedButton = button("✓ Publicado — excluir definitivamente e preparar próximo");
        postedButton.setEnabled(false);
        postedButton.setOnClickListener(v -> markPostedAndDelete());
        box.addView(postedButton);

        skipButton = button("↪ Pular este vídeo");
        skipButton.setEnabled(false);
        skipButton.setOnClickListener(v -> skipCurrent());
        box.addView(skipButton);

        alreadyPostedButton = button("⛔ Já publiquei antes — não mostrar novamente");
        alreadyPostedButton.setEnabled(false);
        alreadyPostedButton.setOnClickListener(v -> markAlreadyPosted());
        box.addView(alreadyPostedButton);

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
        updateSummary();

        ScrollView scroll = new ScrollView(this);
        scroll.addView(box);
        setContentView(scroll);
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
                connection.setRequestProperty("User-Agent", "KwaiPhoneHelper/0.9 Android");
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
                connection.setRequestProperty("User-Agent", "KwaiPhoneHelper/0.9 Android");
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
                connection.setRequestProperty("User-Agent", "Mozilla/5.0 (Linux; Android) KwaiPhoneHelper/0.9");
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
        setStatus("Vídeo pulado. Baixando o próximo da fila...");
        downloadCurrent();
    }

    private void appendHistory(QueueItem item) {
        SharedPreferences prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        String old = prefs.getString("history", "");
        String when = DateFormat.getDateTimeInstance(DateFormat.SHORT, DateFormat.SHORT, new Locale("pt", "BR")).format(new Date());
        String line = when + " • " + item.sourceName + " • " + item.videoId;
        String combined = line + (old.isEmpty() ? "" : "\n" + old);
        String[] lines = combined.split("\n");
        StringBuilder trimmed = new StringBuilder();
        for (int i = 0; i < lines.length && i < 20; i++) {
            if (i > 0) trimmed.append('\n');
            trimmed.append(lines[i]);
        }
        prefs.edit().putString("history", trimmed.toString()).apply();
    }

    private void refreshHistory() {
        String history = getSharedPreferences(PREFS, MODE_PRIVATE).getString("history", "");
        if (history == null || history.trim().isEmpty()) {
            historyLabel.setText("Nenhuma publicação marcada ainda.");
            return;
        }
        String[] lines = history.split("\n");
        StringBuilder visible = new StringBuilder();
        for (int i = 0; i < lines.length && i < 5; i++) {
            if (i > 0) visible.append('\n');
            visible.append("• ").append(lines[i]);
        }
        historyLabel.setText(visible.toString());
    }

    private Set<String> getPostedIds() {
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
                            if (videoId.matches("\d+")) posted.add(sourceId + ":" + videoId);
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

    private Uri copyToPublicFolder(File source, String relativePath) throws Exception {
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

    private File videoFolder() {
        return new File(getExternalFilesDir(Environment.DIRECTORY_MOVIES), "KwaiHelper");
    }

    private long localBytes() {
        File folder = videoFolder();
        if (!folder.exists()) return 0;
        File[] files = folder.listFiles();
        if (files == null) return 0;
        long total = 0;
        for (File file : files) if (file.isFile()) total += file.length();
        return total;
    }

    private String formatBytes(long bytes) {
        double mb = bytes / (1024.0 * 1024.0);
        if (mb < 1024) return String.format(Locale.getDefault(), "%.1f MB", mb);
        return String.format(Locale.getDefault(), "%.2f GB", mb / 1024.0);
    }

    private void updateSummary() {
        summaryLabel.setText(
                "Pendentes: " + pending.size()
                        + "   •   Publicados: " + getPostedIds().size()
                        + "   •   Local: " + formatBytes(localBytes())
        );
    }

    private void setStatus(String text) {
        status.setText(text);
    }

    private void setChip(String text) {
        statusChip.setText(text);
    }

    private String shortMessage(Exception exc) {
        String message = exc.getMessage();
        if (message == null || message.trim().isEmpty()) return exc.getClass().getSimpleName();
        return message.length() > 160 ? message.substring(0, 160) : message;
    }

    private String safeFileName(String value) {
        return value.replaceAll("[^A-Za-z0-9._-]", "_");
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        executor.shutdownNow();
        imageExecutor.shutdownNow();
    }

    private static class QueueItem {
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

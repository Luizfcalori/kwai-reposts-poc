package com.luizcalori.kwaihelper;

import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.os.Environment;
import android.view.Gravity;
import android.widget.Button;
import android.widget.EditText;
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
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends Activity {
    private static final String QUEUE_URL =
            "https://raw.githubusercontent.com/Luizfcalori/kwai-reposts-poc/main/data/kwai_queue.json";

    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private final List<QueueItem> pending = new ArrayList<>();

    private TextView status;
    private TextView sourceLabel;
    private TextView queueLabel;
    private EditText caption;
    private Button syncButton;
    private Button downloadButton;
    private Button shareButton;
    private Button postedButton;

    private QueueItem current;
    private File downloadedFile;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        int pad = dp(18);
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setPadding(pad, pad, pad, pad);

        TextView title = new TextView(this);
        title.setText("Kwai Phone Helper — fila manual v6");
        title.setTextSize(24);
        title.setTextColor(Color.BLACK);
        title.setPadding(0, 0, 0, dp(8));
        box.addView(title);

        TextView info = new TextView(this);
        info.setText("O app sincroniza a fila autorizada, baixa um vídeo por vez, prepara legenda e hashtags e deixa a publicação final sob seu controle no Kwai. Depois de postar, você pode excluir o arquivo local com um toque.");
        info.setTextSize(15);
        info.setTextColor(Color.DKGRAY);
        info.setPadding(0, 0, 0, dp(14));
        box.addView(info);

        syncButton = button("1. Sincronizar fila e baixar próximo");
        syncButton.setOnClickListener(v -> syncQueue(true));
        box.addView(syncButton);

        queueLabel = new TextView(this);
        queueLabel.setText("Fila ainda não sincronizada");
        queueLabel.setTextColor(Color.DKGRAY);
        queueLabel.setPadding(0, dp(7), 0, dp(7));
        box.addView(queueLabel);

        sourceLabel = new TextView(this);
        sourceLabel.setText("Nenhum vídeo carregado");
        sourceLabel.setTextSize(17);
        sourceLabel.setTextColor(Color.BLACK);
        sourceLabel.setPadding(0, dp(5), 0, dp(7));
        box.addView(sourceLabel);

        caption = new EditText(this);
        caption.setHint("Legenda + hashtags");
        caption.setMinLines(5);
        caption.setGravity(Gravity.TOP);
        box.addView(caption, new LinearLayout.LayoutParams(-1, -2));

        downloadButton = button("2. Baixar novamente este vídeo");
        downloadButton.setEnabled(false);
        downloadButton.setOnClickListener(v -> downloadCurrent());
        box.addView(downloadButton);

        shareButton = button("3. Enviar para o Kwai");
        shareButton.setEnabled(false);
        shareButton.setOnClickListener(v -> shareCurrent());
        box.addView(shareButton);

        postedButton = button("4. Postado — excluir e preparar próximo");
        postedButton.setEnabled(false);
        postedButton.setOnClickListener(v -> markPostedAndDelete());
        box.addView(postedButton);

        status = new TextView(this);
        status.setText("Pronto para sincronizar.");
        status.setTextColor(Color.rgb(70, 70, 70));
        status.setPadding(0, dp(12), 0, 0);
        box.addView(status);

        ScrollView scroll = new ScrollView(this);
        scroll.addView(box);
        setContentView(scroll);
    }

    private Button button(String text) {
        Button b = new Button(this);
        b.setText(text);
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(-1, -2);
        p.setMargins(0, dp(5), 0, dp(5));
        b.setLayoutParams(p);
        return b;
    }

    private void syncQueue(boolean downloadAfterSync) {
        setStatus("Sincronizando fila...");
        syncButton.setEnabled(false);

        executor.execute(() -> {
            HttpURLConnection connection = null;
            try {
                URL url = new URL(QUEUE_URL + "?t=" + System.currentTimeMillis());
                connection = (HttpURLConnection) url.openConnection();
                connection.setConnectTimeout(20000);
                connection.setReadTimeout(30000);
                connection.setRequestProperty("User-Agent", "KwaiPhoneHelper/0.2 Android");
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
                        if (obj == null || !obj.optBoolean("rights_confirmed", false)) {
                            continue;
                        }
                        if (!"ready_for_phone".equals(obj.optString("status"))) {
                            continue;
                        }
                        String mediaUrl = obj.optString("media_url", "");
                        if (!mediaUrl.startsWith("http")) {
                            continue;
                        }

                        QueueItem item = new QueueItem();
                        item.sourceId = obj.optString("source_id", "source");
                        item.sourceName = obj.optString("source_display_name", obj.optString("source_handle", "Kwai"));
                        item.videoId = obj.optString("video_id", "");
                        item.videoUrl = obj.optString("video_url", "");
                        item.mediaUrl = mediaUrl;
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
                                if (tagText.length() > 0) {
                                    item.postText = item.postText + "\n\n" + tagText;
                                }
                            }
                        }

                        if (!item.videoId.isEmpty() && !postedIds.contains(item.key())) {
                            fresh.add(item);
                        }
                    }
                }

                runOnUiThread(() -> {
                    pending.clear();
                    pending.addAll(fresh);
                    syncButton.setEnabled(true);
                    selectFirstPending();
                    if (current == null) {
                        setStatus("Nenhum vídeo novo pronto para o celular.");
                    } else if (downloadAfterSync) {
                        downloadCurrent();
                    }
                });
            } catch (Exception exc) {
                runOnUiThread(() -> {
                    syncButton.setEnabled(true);
                    setStatus("Falha ao sincronizar: " + shortMessage(exc));
                });
            } finally {
                if (connection != null) {
                    connection.disconnect();
                }
            }
        });
    }

    private void selectFirstPending() {
        downloadedFile = null;
        shareButton.setEnabled(false);
        postedButton.setEnabled(false);

        if (pending.isEmpty()) {
            current = null;
            sourceLabel.setText("Nenhum vídeo pendente");
            queueLabel.setText("Fila: 0 pendentes neste aparelho");
            caption.setText("");
            downloadButton.setEnabled(false);
            return;
        }

        current = pending.get(0);
        sourceLabel.setText(current.sourceName + " • vídeo " + current.videoId);
        queueLabel.setText("Fila: " + pending.size() + " pendente(s) neste aparelho");
        caption.setText(current.postText);
        downloadButton.setEnabled(true);
    }

    private void downloadCurrent() {
        QueueItem item = current;
        if (item == null) {
            Toast.makeText(this, "Sincronize a fila primeiro.", Toast.LENGTH_LONG).show();
            return;
        }

        setStatus("Baixando vídeo " + item.videoId + "...");
        downloadButton.setEnabled(false);
        shareButton.setEnabled(false);
        postedButton.setEnabled(false);

        executor.execute(() -> {
            HttpURLConnection connection = null;
            File partial = null;
            try {
                File base = new File(getExternalFilesDir(Environment.DIRECTORY_MOVIES), "KwaiHelper");
                if (!base.exists() && !base.mkdirs()) {
                    throw new IllegalStateException("Não foi possível criar a pasta local.");
                }

                File target = new File(base, safeFileName(item.sourceId + "_" + item.videoId) + ".mp4");
                partial = new File(base, target.getName() + ".part");
                if (partial.exists()) partial.delete();

                URL url = new URL(item.mediaUrl);
                connection = (HttpURLConnection) url.openConnection();
                connection.setConnectTimeout(25000);
                connection.setReadTimeout(90000);
                connection.setRequestProperty("User-Agent", "Mozilla/5.0 (Linux; Android) KwaiPhoneHelper/0.2");
                connection.setInstanceFollowRedirects(true);

                int response = connection.getResponseCode();
                if (response < 200 || response >= 300) {
                    throw new IllegalStateException("Servidor respondeu HTTP " + response + ". Sincronize a fila novamente.");
                }

                try (InputStream input = new BufferedInputStream(connection.getInputStream());
                     FileOutputStream output = new FileOutputStream(partial)) {
                    byte[] buffer = new byte[64 * 1024];
                    int read;
                    long total = 0;
                    while ((read = input.read(buffer)) != -1) {
                        output.write(buffer, 0, read);
                        total += read;
                    }
                    output.flush();
                    if (total < 1024) {
                        throw new IllegalStateException("O arquivo recebido parece inválido.");
                    }
                }

                if (target.exists()) target.delete();
                if (!partial.renameTo(target)) {
                    throw new IllegalStateException("Não foi possível finalizar o arquivo baixado.");
                }

                downloadedFile = target;
                runOnUiThread(() -> {
                    downloadButton.setEnabled(true);
                    shareButton.setEnabled(true);
                    postedButton.setEnabled(true);
                    setStatus("Vídeo baixado no celular. Revise a legenda e toque em Enviar para o Kwai.");
                });
            } catch (Exception exc) {
                if (partial != null && partial.exists()) partial.delete();
                runOnUiThread(() -> {
                    downloadButton.setEnabled(true);
                    setStatus("Falha no download: " + shortMessage(exc));
                });
            } finally {
                if (connection != null) connection.disconnect();
            }
        });
    }

    private void shareCurrent() {
        if (current == null || downloadedFile == null || !downloadedFile.exists()) {
            Toast.makeText(this, "Baixe o vídeo antes de enviar.", Toast.LENGTH_LONG).show();
            return;
        }

        String text = caption.getText().toString().trim();
        if (!text.isEmpty()) {
            ClipboardManager clipboard = (ClipboardManager) getSystemService(CLIPBOARD_SERVICE);
            clipboard.setPrimaryClip(ClipData.newPlainText("Legenda Kwai", text));
        }

        Uri videoUri = FileProvider.getUriForFile(
                this,
                getPackageName() + ".files",
                downloadedFile
        );

        Intent share = new Intent(Intent.ACTION_SEND);
        share.setType("video/mp4");
        share.putExtra(Intent.EXTRA_STREAM, videoUri);
        if (!text.isEmpty()) {
            share.putExtra(Intent.EXTRA_TEXT, text);
        }
        share.setClipData(ClipData.newUri(getContentResolver(), "video", videoUri));
        share.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);

        try {
            startActivity(Intent.createChooser(share, "Escolha o Kwai"));
            setStatus("Vídeo enviado ao compartilhamento. A legenda também está copiada para você colar no Kwai, se necessário.");
        } catch (ActivityNotFoundException ex) {
            Toast.makeText(this, "Nenhum aplicativo compatível foi encontrado.", Toast.LENGTH_LONG).show();
        }
    }

    private void markPostedAndDelete() {
        if (current == null) return;

        if (downloadedFile != null && downloadedFile.exists() && !downloadedFile.delete()) {
            Toast.makeText(this, "Não consegui excluir o arquivo local agora.", Toast.LENGTH_LONG).show();
        }

        Set<String> posted = getPostedIds();
        posted.add(current.key());
        getSharedPreferences("kwai_queue_state", MODE_PRIVATE)
                .edit()
                .putStringSet("posted_ids", new HashSet<>(posted))
                .apply();

        if (!pending.isEmpty()) pending.remove(0);
        downloadedFile = null;
        selectFirstPending();

        if (current != null) {
            setStatus("Postagem marcada como concluída. Baixando o próximo vídeo...");
            downloadCurrent();
        } else {
            setStatus("Tudo concluído nesta fila. Sincronize novamente quando quiser verificar novos vídeos.");
        }
    }

    private Set<String> getPostedIds() {
        SharedPreferences prefs = getSharedPreferences("kwai_queue_state", MODE_PRIVATE);
        Set<String> stored = prefs.getStringSet("posted_ids", null);
        return stored == null ? new HashSet<>() : new HashSet<>(stored);
    }

    private void setStatus(String text) {
        status.setText(text);
    }

    private String shortMessage(Exception exc) {
        String message = exc.getMessage();
        if (message == null || message.trim().isEmpty()) {
            return exc.getClass().getSimpleName();
        }
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
    }

    private static class QueueItem {
        String sourceId;
        String sourceName;
        String videoId;
        String videoUrl;
        String mediaUrl;
        String postText;

        String key() {
            return sourceId + ":" + videoId;
        }
    }
}

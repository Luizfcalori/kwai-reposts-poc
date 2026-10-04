package com.luizcalori.kwaihelper;

import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.ClipData;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.view.Gravity;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

public class MainActivity extends Activity {
    private static final int PICK_VIDEO = 1001;
    private static final String KWAI_PACKAGE = "com.kwai.kuaishou.video.live";

    private Uri selectedVideo;
    private TextView selectedLabel;
    private EditText caption;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        int pad = dp(18);
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setPadding(pad, pad, pad, pad);

        TextView title = new TextView(this);
        title.setText("Kwai Phone Helper — modo seguro");
        title.setTextSize(24);
        title.setTextColor(Color.BLACK);
        title.setPadding(0, 0, 0, dp(10));
        box.addView(title);

        TextView info = new TextView(this);
        info.setText("Esta versão não usa Acessibilidade nem permissões sensíveis. Ela apenas entrega ao Kwai um vídeo escolhido por você e uma legenda opcional usando o compartilhamento normal do Android.");
        info.setTextSize(16);
        info.setTextColor(Color.DKGRAY);
        info.setPadding(0, 0, 0, dp(16));
        box.addView(info);

        Button choose = button("1. Escolher vídeo");
        choose.setOnClickListener(v -> chooseVideo());
        box.addView(choose);

        selectedLabel = new TextView(this);
        selectedLabel.setText("Nenhum vídeo selecionado");
        selectedLabel.setTextColor(Color.DKGRAY);
        selectedLabel.setPadding(0, dp(6), 0, dp(12));
        box.addView(selectedLabel);

        caption = new EditText(this);
        caption.setHint("Legenda da postagem (opcional)");
        caption.setMinLines(3);
        caption.setGravity(Gravity.TOP);
        box.addView(caption, new LinearLayout.LayoutParams(-1, -2));

        TextView note = new TextView(this);
        note.setText("No primeiro teste queremos confirmar duas coisas: se o APK instala normalmente e se o Kwai recebe o vídeo por compartilhamento direto. O botão final de publicar continuará sob seu controle.");
        note.setTextColor(Color.rgb(90, 90, 90));
        note.setPadding(0, dp(10), 0, dp(12));
        box.addView(note);

        Button send = button("2. Enviar para o Kwai");
        send.setOnClickListener(v -> shareToKwai());
        box.addView(send);

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

    private void chooseVideo() {
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.setType("video/*");
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
        startActivityForResult(intent, PICK_VIDEO);
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == PICK_VIDEO && resultCode == RESULT_OK && data != null && data.getData() != null) {
            selectedVideo = data.getData();
            try {
                getContentResolver().takePersistableUriPermission(
                        selectedVideo,
                        data.getFlags() & (Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_WRITE_URI_PERMISSION));
            } catch (Exception ignored) {
            }
            selectedLabel.setText("Vídeo selecionado: " + selectedVideo.getLastPathSegment());
        }
    }

    private void shareToKwai() {
        if (selectedVideo == null) {
            Toast.makeText(this, "Escolha um vídeo primeiro.", Toast.LENGTH_LONG).show();
            return;
        }

        Intent share = new Intent(Intent.ACTION_SEND);
        share.setType("video/*");
        share.putExtra(Intent.EXTRA_STREAM, selectedVideo);
        share.setClipData(ClipData.newUri(getContentResolver(), "video", selectedVideo));
        String text = caption.getText().toString().trim();
        if (!text.isEmpty()) {
            share.putExtra(Intent.EXTRA_TEXT, text);
        }
        share.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
        share.setPackage(KWAI_PACKAGE);

        try {
            startActivity(share);
        } catch (ActivityNotFoundException ex) {
            Intent launch = getPackageManager().getLaunchIntentForPackage(KWAI_PACKAGE);
            if (launch != null) {
                startActivity(launch);
                Toast.makeText(this, "O Kwai não aceitou o compartilhamento direto. Abri o app para verificarmos essa tela.", Toast.LENGTH_LONG).show();
            } else {
                Toast.makeText(this, "Kwai não encontrado neste aparelho.", Toast.LENGTH_LONG).show();
            }
        }
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }
}

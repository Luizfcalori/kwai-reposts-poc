package com.luizcalori.kwaihelper;

import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.provider.Settings;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.CheckBox;
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
    private CheckBox autoPost;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        int pad = dp(18);
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setPadding(pad, pad, pad, pad);

        TextView title = new TextView(this);
        title.setText("Kwai Phone Helper");
        title.setTextSize(24);
        title.setTextColor(Color.BLACK);
        title.setPadding(0, 0, 0, dp(10));
        box.addView(title);

        TextView info = new TextView(this);
        info.setText("Primeiro teste: escolha um vídeo, escreva a legenda, ative a Acessibilidade e abra a postagem no Kwai. O app não lê senha, SMS ou dados da sua conta.");
        info.setTextSize(16);
        info.setTextColor(Color.DKGRAY);
        info.setPadding(0, 0, 0, dp(16));
        box.addView(info);

        Button accessibility = button("1. Ativar Acessibilidade");
        accessibility.setOnClickListener(v -> startActivity(new Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)));
        box.addView(accessibility);

        Button choose = button("2. Escolher vídeo");
        choose.setOnClickListener(v -> chooseVideo());
        box.addView(choose);

        selectedLabel = new TextView(this);
        selectedLabel.setText("Nenhum vídeo selecionado");
        selectedLabel.setTextColor(Color.DKGRAY);
        selectedLabel.setPadding(0, dp(6), 0, dp(12));
        box.addView(selectedLabel);

        caption = new EditText(this);
        caption.setHint("Legenda da postagem");
        caption.setMinLines(3);
        caption.setGravity(Gravity.TOP);
        box.addView(caption, new LinearLayout.LayoutParams(-1, -2));

        autoPost = new CheckBox(this);
        autoPost.setText("Publicar automaticamente quando o botão final for encontrado");
        autoPost.setChecked(false);
        autoPost.setPadding(0, dp(8), 0, dp(8));
        box.addView(autoPost);

        TextView warning = new TextView(this);
        warning.setText("No primeiro teste, deixe a opção acima desmarcada para confirmar se vídeo e legenda chegaram corretamente. Depois podemos ativar o clique final.");
        warning.setTextColor(Color.rgb(140, 80, 0));
        warning.setPadding(0, 0, 0, dp(12));
        box.addView(warning);

        Button start = button("3. Preparar no Kwai");
        start.setOnClickListener(v -> beginPost());
        box.addView(start);

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

    private void beginPost() {
        if (selectedVideo == null) {
            Toast.makeText(this, "Escolha um vídeo primeiro.", Toast.LENGTH_LONG).show();
            return;
        }

        SharedPreferences prefs = getSharedPreferences("kwai_job", MODE_PRIVATE);
        prefs.edit()
                .putBoolean("active", true)
                .putBoolean("caption_done", false)
                .putBoolean("auto_post", autoPost.isChecked())
                .putString("caption", caption.getText().toString())
                .apply();

        Intent share = new Intent(Intent.ACTION_SEND);
        share.setType("video/*");
        share.putExtra(Intent.EXTRA_STREAM, selectedVideo);
        if (!caption.getText().toString().isEmpty()) {
            share.putExtra(Intent.EXTRA_TEXT, caption.getText().toString());
        }
        share.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
        share.setPackage(KWAI_PACKAGE);

        try {
            startActivity(share);
        } catch (ActivityNotFoundException ex) {
            prefs.edit().putBoolean("active", false).apply();
            Intent launch = getPackageManager().getLaunchIntentForPackage(KWAI_PACKAGE);
            if (launch != null) {
                startActivity(launch);
                Toast.makeText(this, "O Kwai não aceitou o compartilhamento direto. Abri o app para o próximo ajuste.", Toast.LENGTH_LONG).show();
            } else {
                Toast.makeText(this, "Kwai não encontrado neste aparelho.", Toast.LENGTH_LONG).show();
            }
        }
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }
}

#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JAVA = ROOT / "mobile-app/src/main/java/com/luizcalori/kwaihelper/MainActivity.java"
GRADLE = ROOT / "mobile-app/build.gradle"


def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f"missing patch anchor: {label}")
    return text.replace(old, new, 1)

text = JAVA.read_text(encoding="utf-8")
text = text.replace('Kwai Phone Helper v9', 'Kwai Phone Helper v10')
text = text.replace('KwaiPhoneHelper/0.9 Android', 'KwaiPhoneHelper/1.0 Android')
text = text.replace('KwaiPhoneHelper/0.9', 'KwaiPhoneHelper/1.0')

old = '''        TextView cardTitle = new TextView(this);
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
'''

new = '''        TextView quickTitle = new TextView(this);
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
        thumbnail.setScaleType(ImageView.ScaleType.CENTER_CROP);
        LinearLayout.LayoutParams imageParams = new LinearLayout.LayoutParams(-1, dp(150));
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
'''

text = replace_once(text, old, new, "main content ordering")

helper_anchor = '''    private Button button(String text) {
        Button b = new Button(this);
        b.setText(text);
        b.setAllCaps(false);
        b.setTextSize(15);
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(-1, -2);
        p.setMargins(0, dp(5), 0, dp(5));
        b.setLayoutParams(p);
        return b;
    }
'''

helper_new = helper_anchor + '''
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
'''
text = replace_once(text, helper_anchor, helper_new, "actionRow helper")

JAVA.write_text(text, encoding="utf-8")

gradle = GRADLE.read_text(encoding="utf-8")
gradle = replace_once(gradle, "versionCode 9", "versionCode 10", "version code")
gradle = replace_once(gradle, "versionName '0.9.0'", "versionName '1.0.0'", "version name")
GRADLE.write_text(gradle, encoding="utf-8")
print("v10 quick actions patch applied")

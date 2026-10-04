#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import html
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUEUE_PATH = ROOT / "data" / "kwai_queue.json"

GENERIC_PHRASES = [
    "este vlogger compartilhou muitos vídeos legais venha conferir",
    "este vlogger compartilhou muitos videos legais venha conferir",
    "venha conferir",
]

GENERAL_TAGS = ["#KwaiBrasil", "#ParaVoce"]

SOURCE_CATEGORY_OVERRIDES = {
    "cvqjx483": "motivacao",
    "lideranca00dojob": "motivacao",
    "gatas_do_mundo": "lifestyle",
    "princesasdainternet1": "lifestyle",
    "larissagatinha335": "lifestyle",
    "colirios01": "lifestyle",
    "battyboop": "lifestyle",
}

CATEGORIES = {
    "motivacao": {
        "keywords": ["motivacao", "lideranca", "reflexao", "superacao", "frase", "inspiracao"],
        "tags": ["#Motivacao", "#Reflexao", "#Inspiracao"],
        "templates": [
            "Uma mensagem que vale levar para o dia 💭\nO que você achou dessa reflexão?",
            "Tem coisa que a gente precisa ouvir na hora certa ✨\nEssa mensagem fez sentido para você?",
            "Uma pausa rápida para pensar um pouco 💡\nConcorda com essa ideia?",
        ],
    },
    "lifestyle": {
        "keywords": ["lifestyle", "estilo", "look", "moda", "beleza", "princesa", "gata", "gatinha", "colirio", "modelo"],
        "tags": ["#Lifestyle", "#Estilo", "#Momentos"],
        "templates": [
            "Equilíbrio, atitude e uma cena que chama atenção 👀\nO que você achou desse momento?",
            "Um registro diferente que prende a atenção logo de cara ✨\nCurtiu essa cena?",
            "Estilo e energia em poucos segundos 👀\nO que mais chamou sua atenção?",
            "Uma cena marcante para passar na sua timeline ✨\nVocê assistiria de novo?",
        ],
    },
    "danca": {
        "keywords": ["danca", "dance", "coreografia", "ritmo", "rebolando", "musica"],
        "tags": ["#Danca", "#Musica", "#Ritmo"],
        "templates": [
            "Energia e ritmo do começo ao fim 🔥\nCurtiu essa sequência?",
            "Quando a música bate e o vídeo flui 🎶\nO que achou dessa vibe?",
            "Esse ritmo ficou difícil de ignorar 👀\nVocê assistiria de novo?",
        ],
    },
    "humor": {
        "keywords": ["humor", "engracado", "comedia", "meme", "risada", "pegadinha", "zoeira"],
        "tags": ["#Humor", "#Comedia", "#Risadas"],
        "templates": [
            "Essa cena merece replay 😂\nVocê conseguiu segurar a risada?",
            "Do nada uma cena dessas 😅\nVocê esperava por esse final?",
            "Tem vídeo que melhora quando você assiste de novo 😂\nQual foi sua reação?",
        ],
    },
    "fitness": {
        "keywords": ["treino", "academia", "fitness", "musculacao", "exercicio", "equilibrio", "alongamento"],
        "tags": ["#Fitness", "#Movimento", "#Treino"],
        "templates": [
            "Controle e movimento em uma cena que chama atenção 💪\nVocê tentaria algo assim?",
            "Equilíbrio e concentração aparecendo na prática 👀\nCurtiu esse movimento?",
            "Uma dose de movimento para a timeline 🔥\nO que você achou?",
        ],
    },
    "viagem": {
        "keywords": ["praia", "viagem", "natureza", "paisagem", "ferias", "turismo", "mar"],
        "tags": ["#Viagem", "#Natureza", "#Paisagem"],
        "templates": [
            "Um cenário desses já muda o dia 🌴\nVocê iria para esse lugar?",
            "Aquele tipo de paisagem que dá vontade de ficar por horas ✨\nCurtiu?",
            "Só pela vista já vale assistir até o final 🌊\nVocê conhece um lugar assim?",
        ],
    },
    "comida": {
        "keywords": ["receita", "comida", "cozinha", "gastronomia", "lanche", "sobremesa", "bolo"],
        "tags": ["#Receita", "#Comida", "#Gastronomia"],
        "templates": [
            "Isso aqui abriu o apetite 😋\nVocê provaria?",
            "Receita que merece ficar salva 👀\nVocê faria em casa?",
            "Tem coisa que a gente já assiste com fome 😅\nCurtiu a ideia?",
        ],
    },
    "animais": {
        "keywords": ["cachorro", "gato", "pet", "animal", "dog", "cat"],
        "tags": ["#Pets", "#Animais", "#Fofura"],
        "templates": [
            "Difícil não assistir até o final 🐾\nVocê também ama esse tipo de vídeo?",
            "Momento fofura passando na sua tela 🐾\nQual foi sua reação?",
            "Esses vídeos sempre melhoram o dia 😄\nVocê teria um desses?",
        ],
    },
    "carros": {
        "keywords": ["carro", "moto", "motor", "automotivo", "automovel"],
        "tags": ["#Carros", "#Automotivo", "#Motores"],
        "templates": [
            "Para quem gosta de máquina, esse vídeo chama atenção 🔥\nO que você achou?",
            "Detalhes que fazem diferença para quem curte automotivo 👀\nAprovado?",
            "Esse aqui merece uma olhada com calma 🚗\nQual detalhe chamou mais atenção?",
        ],
    },
    "futebol": {
        "keywords": ["futebol", "gol", "jogador", "torcida", "campeonato", "partida"],
        "tags": ["#Futebol", "#Gol", "#Torcida"],
        "templates": [
            "Cena para quem gosta de futebol ⚽\nO que você achou desse lance?",
            "Esse momento merece replay ⚽🔥\nVocê faria diferente?",
            "Futebol sempre rende assunto 😄\nQual sua opinião sobre esse lance?",
        ],
    },
    "geral": {
        "keywords": [],
        "tags": ["#Entretenimento", "#Momentos"],
        "templates": [
            "Esse vídeo chamou atenção por aqui 👀\nO que você achou dessa cena?",
            "Vale assistir até o final 👀\nQual foi a sua reação?",
            "Mais um daqueles vídeos que prendem a atenção ✨\nVocê curtiu?",
        ],
    },
}


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.lower()


def clean_caption(text: str) -> str:
    text = html.unescape(text or "")
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"\d+[,.]?\d*\s*Like\(s\),?\s*\d+[,.]?\d*\s*Comment\(s\)\.\s*", " ", text, flags=re.I)
    text = re.sub(r"Kwai video from .*?\(@[^)]+\):\s*", " ", text, flags=re.I)
    text = re.sub(r"\b\d{1,2}:\d{2}\b", " ", text)
    text = re.sub(r"[\"'“”‘’]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" -–—|:;,.")

    lowered = norm(text)
    for phrase in GENERIC_PHRASES:
        if norm(phrase) in lowered:
            text = re.sub(re.escape(phrase), " ", text, flags=re.I)
            lowered = norm(text)

    text = re.sub(r"\s+", " ", text).strip(" -–—|:;,.")
    parts = [p.strip() for p in re.split(r"[,.|]+", text) if p.strip()]
    if len(parts) == 2 and norm(parts[0]) == norm(parts[1]):
        text = parts[0]
    if re.fullmatch(r"[@A-Za-z0-9_.-]{2,40}", text or ""):
        text = ""
    if not re.search(r"[A-Za-zÀ-ÿ]{3}", text or ""):
        text = ""
    return text[:220]


def choose_category(item: dict, cleaned: str) -> str:
    source_id = str(item.get("source_id", ""))
    if source_id in SOURCE_CATEGORY_OVERRIDES:
        return SOURCE_CATEGORY_OVERRIDES[source_id]

    haystack = " ".join([
        cleaned,
        str(item.get("source_caption", "")),
        str(item.get("page_title", "")),
        str(item.get("source_display_name", "")),
        str(item.get("source_handle", "")),
        source_id,
    ])
    n = norm(haystack)
    best = "geral"
    best_score = 0
    for name, cfg in CATEGORIES.items():
        if name == "geral":
            continue
        score = sum(1 for kw in cfg["keywords"] if norm(kw) in n)
        if score > best_score:
            best = name
            best_score = score
    return best


def existing_tags(text: str) -> list[str]:
    out = []
    seen = set()
    blocked = {"#kwai", "#fyp", "#viral", "#paravoce", "#pravc", "#emalta", "#videododia"}
    for tag in re.findall(r"#[\wÀ-ÿ]+", text or ""):
        key = norm(tag)
        if key in blocked:
            continue
        if key not in seen:
            seen.add(key)
            out.append(tag)
        if len(out) == 2:
            break
    return out


def dedupe_tags(tags: list[str], limit: int = 5) -> list[str]:
    out = []
    seen = set()
    for tag in tags:
        tag = re.sub(r"[^#A-Za-zÀ-ÿ0-9_]", "", tag)
        if not tag.startswith("#"):
            tag = "#" + tag
        key = norm(tag)
        if len(tag) > 1 and key not in seen:
            seen.add(key)
            out.append(tag)
        if len(out) >= limit:
            break
    return out


def improve(item: dict) -> tuple[str, list[str], str, str]:
    video_id = str(item.get("video_id", "0"))
    seed = int(hashlib.sha256(video_id.encode()).hexdigest()[:8], 16)
    raw = str(item.get("source_caption", ""))
    cleaned = clean_caption(raw)
    category = choose_category(item, cleaned)
    cfg = CATEGORIES[category]

    if cleaned and len(cleaned) >= 12:
        openers = [
            "Olha essa 👀",
            "Essa chamou atenção por aqui ✨",
            "Vale dar uma olhada até o final 👇",
            "Mais um vídeo que merece replay 👀",
        ]
        caption = f"{openers[seed % len(openers)]}\n{cleaned}"
    else:
        caption = cfg["templates"][seed % len(cfg["templates"])]

    tags = dedupe_tags(existing_tags(raw) + cfg["tags"] + GENERAL_TAGS)
    post_text = caption + "\n\n" + " ".join(tags)
    return caption, tags, post_text, category


def main() -> int:
    if not QUEUE_PATH.exists():
        return 0
    data = json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
    changed = 0
    for item in data.get("items", []):
        if not item.get("rights_confirmed"):
            continue
        if item.get("status") not in {"ready_for_phone", "ready_for_media_refresh"}:
            continue
        caption, tags, post_text, category = improve(item)
        updates = {
            "generated_caption": caption,
            "hashtags": tags,
            "post_text": post_text,
            "caption_category": category,
            "caption_strategy": "source_aware_v2",
        }
        if any(item.get(k) != v for k, v in updates.items()):
            item.update(updates)
            changed += 1
    if changed:
        QUEUE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"captions_improved": changed, "strategy": "source_aware_v2"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

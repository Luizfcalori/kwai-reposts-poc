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

GENERAL_TAGS = [
    ["#KwaiBrasil", "#ParaVoce"],
    ["#VideoDoDia", "#KwaiBrasil"],
    ["#EmAlta", "#ParaVoce"],
    ["#KwaiBrasil", "#Confira"],
]

CATEGORIES = {
    "motivacao": {
        "keywords": ["motivacao", "motivação", "lideranca", "liderança", "reflexao", "reflexão", "superacao", "superação", "frase", "inspiracao", "inspiração"],
        "tags": ["#Motivacao", "#Reflexao", "#Inspiracao"],
        "templates": [
            "Uma mensagem que vale levar para o dia 💭\nO que você achou dessa reflexão?",
            "Tem coisa que a gente precisa ouvir na hora certa ✨\nEssa mensagem fez sentido para você?",
            "Uma pausa rápida para pensar um pouco 💡\nConcorda com essa ideia?",
        ],
    },
    "beleza": {
        "keywords": ["beleza", "maquiagem", "make", "look", "moda", "fashion", "estilo", "princesa", "gata", "gatinha", "colirio", "colírio", "modelo", "biquini", "biquíni"],
        "tags": ["#Beleza", "#Estilo", "#Lifestyle"],
        "templates": [
            "Um visual que chama atenção logo de cara ✨\nQual detalhe você curtiu mais?",
            "Estilo e presença em poucos segundos 👀\nO que você achou desse visual?",
            "Aquele tipo de vídeo que prende a atenção ✨\nVocê curtiu o estilo?",
        ],
    },
    "danca": {
        "keywords": ["danca", "dança", "dance", "coreografia", "ritmo", "rebolando", "musica", "música"],
        "tags": ["#Danca", "#Musica", "#Ritmo"],
        "templates": [
            "Energia e ritmo do começo ao fim 🔥\nCurtiu essa sequência?",
            "Quando a música bate e o vídeo flui 🎶\nO que achou dessa vibe?",
            "Esse ritmo ficou difícil de ignorar 👀\nVocê assistiria de novo?",
        ],
    },
    "humor": {
        "keywords": ["humor", "engracado", "engraçado", "comedia", "comédia", "meme", "risada", "pegadinha", "zoeira"],
        "tags": ["#Humor", "#Comedia", "#Risadas"],
        "templates": [
            "Essa cena merece replay 😂\nVocê conseguiu segurar a risada?",
            "Tem vídeo que melhora quando você assiste de novo 😂\nQual foi sua reação?",
            "Do nada uma cena dessas 😅\nVocê esperava por esse final?",
        ],
    },
    "fitness": {
        "keywords": ["treino", "academia", "fitness", "musculacao", "musculação", "exercicio", "exercício"],
        "tags": ["#Fitness", "#Treino", "#Academia"],
        "templates": [
            "Foco no treino e consistência 💪\nVocê também está nessa rotina?",
            "Mais uma dose de motivação para treinar 🔥\nQual seu treino de hoje?",
            "Disciplina aparecendo na prática 💪\nCurtiu essa rotina?",
        ],
    },
    "viagem": {
        "keywords": ["praia", "viagem", "natureza", "paisagem", "ferias", "férias", "turismo", "mar"],
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
        "keywords": ["carro", "moto", "motor", "automotivo", "automovel", "automóvel"],
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
        "tags": ["#Video", "#Entretenimento", "#Confira"],
        "templates": [
            "Esse vídeo chamou atenção por aqui 👀\nO que você achou dessa cena?",
            "Vale assistir até o final 👀\nQual foi a sua reação?",
            "Mais um daqueles vídeos que prendem a atenção ✨\nVocê curtiu?",
            "Passando na sua timeline com uma cena que chama atenção 👇\nO que você achou?",
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
        lowered_phrase = norm(phrase)
        if lowered_phrase in lowered:
            pattern = re.compile(re.escape(phrase), re.I)
            text = pattern.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip(" -–—|:;,.")

    # remove obvious duplicated one-word/handle-like captions
    parts = [p.strip() for p in re.split(r"[,.|]+", text) if p.strip()]
    if len(parts) == 2 and norm(parts[0]) == norm(parts[1]):
        text = parts[0]
    if re.fullmatch(r"[@A-Za-z0-9_.-]{2,40}", text or ""):
        text = ""
    return text[:220]


def choose_category(item: dict, cleaned: str) -> str:
    haystack = " ".join([
        cleaned,
        str(item.get("source_caption", "")),
        str(item.get("page_title", "")),
        str(item.get("source_display_name", "")),
        str(item.get("source_handle", "")),
        str(item.get("source_id", "")),
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
    for tag in re.findall(r"#[\wÀ-ÿ]+", text or ""):
        key = norm(tag)
        if key in {"#kwai", "#fyp", "#viral", "#paravoce", "#pravc", "#emalta"}:
            continue
        if key not in seen:
            seen.add(key)
            out.append(tag)
        if len(out) == 2:
            break
    return out


def dedupe_tags(tags: list[str], limit: int = 6) -> list[str]:
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


def improve(item: dict) -> tuple[str, list[str], str]:
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

    tags = dedupe_tags(
        existing_tags(raw)
        + cfg["tags"]
        + GENERAL_TAGS[(seed // 7) % len(GENERAL_TAGS)]
    )
    post_text = caption + "\n\n" + " ".join(tags)
    return caption, tags, post_text


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
        caption, tags, post_text = improve(item)
        if item.get("generated_caption") != caption or item.get("hashtags") != tags or item.get("post_text") != post_text:
            item["generated_caption"] = caption
            item["hashtags"] = tags
            item["post_text"] = post_text
            changed += 1
    if changed:
        QUEUE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"captions_improved": changed}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

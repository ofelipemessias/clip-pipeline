"""Selecao dos melhores momentos: LLM (Anthropic) ou heuristica local."""
import json
import os
import re

from .models import Moment, Segment

DEFAULT_MODEL = os.environ.get("CLIP_PIPELINE_MODEL", "claude-haiku-4-5-20251001")

KEYWORDS = [
    # pt
    "uau", "nossa", "inacreditavel", "incrivel", "absurdo", "cara", "gente",
    "olha", "juro", "melhor", "pior", "nunca", "sempre", "finalmente",
    # en
    "wow", "amazing", "insane", "crazy", "unbelievable", "incredible",
    "best", "worst", "never", "finally", "look",
]


def _norm(text: str) -> str:
    text = text.lower()
    return re.sub(r"[^a-z0-9à-ÿ\s!?]", " ", text)


def build_windows(segments: list[Segment], min_len: float, max_len: float) -> list[Moment]:
    """Gera janelas candidatas com duracao entre min_len e max_len."""
    windows: list[Moment] = []
    n = len(segments)
    for i in range(n):
        start = segments[i].start
        text_parts = []
        for j in range(i, n):
            text_parts.append(segments[j].text)
            end = segments[j].end
            duration = end - start
            if duration < min_len:
                continue
            if duration > max_len:
                break
            windows.append(Moment(start=start, end=end, reason=" ".join(text_parts)))
    return windows


def score_window(moment: Moment) -> float:
    """Pontua uma janela: palavras-chave, pontuacao enfatica e ritmo de fala."""
    text = _norm(moment.reason)
    words = text.split()
    duration = max(moment.end - moment.start, 0.1)
    score = sum(1.0 for kw in KEYWORDS if re.search(rf"\b{kw}\b", text))
    score += 0.5 * (text.count("!") + text.count("?"))
    words_per_sec = len(words) / duration
    score += min(words_per_sec, 4.0) * 0.5  # fala densa tende a ser momento forte
    return score


def select_heuristic(
    segments: list[Segment], count: int = 3, min_len: float = 10.0, max_len: float = 20.0
) -> list[Moment]:
    """Seleciona os top N momentos sem sobreposicao, sem depender de API externa."""
    windows = build_windows(segments, min_len, max_len)
    for w in windows:
        w.score = score_window(w)
    windows.sort(key=lambda w: w.score, reverse=True)
    chosen: list[Moment] = []
    for w in windows:
        if len(chosen) >= count:
            break
        if all(w.end <= c.start or w.start >= c.end for c in chosen):
            chosen.append(w)
    chosen.sort(key=lambda w: w.start)
    return chosen


PROMPT_TEMPLATE = """Abaixo esta a transcricao de um video, com tempos em segundos.

{transcript}

Escolha os {count} melhores momentos para clipes curtos ({min_len}-{max_len} segundos cada):
momentos que funcionam sozinhos, com frase completa e um gancho claro.
Responda APENAS com JSON valido, uma lista de objetos com as chaves
"start" (segundos, numero), "end" (segundos, numero) e "reason" (por que o momento rende, em pt-BR, uma frase).
Sem texto fora do JSON."""


def format_transcript(segments: list[Segment]) -> str:
    return "\n".join(f"[{s.start:.1f} -> {s.end:.1f}] {s.text}" for s in segments)


def parse_moments(text: str, max_len: float | None = None) -> list[Moment]:
    """Extrai a lista JSON da resposta do modelo, tolerando texto ao redor."""
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        raise ValueError("resposta do modelo sem lista JSON")
    data = json.loads(match.group(0))
    moments = []
    for item in data:
        start = float(item["start"])
        end = float(item["end"])
        if end <= start:
            continue
        if max_len and end - start > max_len:
            end = start + max_len
        moments.append(Moment(start=start, end=end, reason=str(item.get("reason", ""))))
    if not moments:
        raise ValueError("resposta do modelo sem momentos validos")
    return moments


def select_with_llm(
    segments: list[Segment],
    count: int = 3,
    min_len: float = 10.0,
    max_len: float = 20.0,
    client=None,
    model: str | None = None,
) -> list[Moment]:
    """Pede ao Claude os melhores momentos. Requer ANTHROPIC_API_KEY."""
    if client is None:
        import anthropic

        client = anthropic.Anthropic()
    prompt = PROMPT_TEMPLATE.format(
        transcript=format_transcript(segments), count=count, min_len=min_len, max_len=max_len
    )
    response = client.messages.create(
        model=model or DEFAULT_MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(block.text for block in response.content if getattr(block, "type", "") == "text")
    moments = parse_moments(text, max_len=max_len)
    return moments[:count]


def select_moments(
    segments: list[Segment],
    count: int = 3,
    min_len: float = 10.0,
    max_len: float = 20.0,
    use_llm: bool = True,
) -> tuple[list[Moment], str]:
    """Escolhe os momentos. Retorna (momentos, metodo usado).

    Usa o Claude quando use_llm e ha ANTHROPIC_API_KEY; senao, heuristica.
    """
    if use_llm and os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return select_with_llm(segments, count, min_len, max_len), "llm"
        except Exception:
            pass  # cai para a heuristica
    return select_heuristic(segments, count, min_len, max_len), "heuristic"

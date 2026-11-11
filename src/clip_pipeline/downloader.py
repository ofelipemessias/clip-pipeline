"""Resolve a entrada: arquivo local ou URL (baixada com yt-dlp)."""
import os
import re

import yt_dlp

_URL_RE = re.compile(r"^https?://", re.IGNORECASE)


def is_url(value: str) -> bool:
    return bool(_URL_RE.match(value.strip()))


def resolve_input(source: str, workdir: str) -> str:
    """Retorna o caminho local do video.

    Arquivo local: valida e retorna. URL: baixa com yt-dlp para workdir.
    Use apenas com conteudo proprio ou autorizado; baixar de plataformas
    pode violar os termos de servico delas.
    """
    if not is_url(source):
        if not os.path.isfile(source):
            raise FileNotFoundError(f"arquivo nao encontrado: {source}")
        return os.path.abspath(source)

    os.makedirs(workdir, exist_ok=True)
    out_tmpl = os.path.join(workdir, "source.%(ext)s")
    opts = {
        "outtmpl": out_tmpl,
        "format": "bv*+ba/b",
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(source, download=True)
        path = ydl.prepare_filename(info)
        if not path.endswith(".mp4"):
            path = os.path.splitext(path)[0] + ".mp4"
    if not os.path.isfile(path):
        raise RuntimeError("download concluido, mas o arquivo nao foi encontrado")
    return path

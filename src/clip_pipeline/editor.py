"""Corte vertical (9:16) com legenda queimada, via ffmpeg."""
import os
import subprocess

from .models import ClipResult, Moment, Segment

WIDTH, HEIGHT = 1080, 1920


def _ass_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def write_captions(segments: list[Segment], moment: Moment, path: str) -> str:
    """Gera um .ass com as falas dentro da janela do clipe, rebaseadas em zero."""
    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {WIDTH}",
        f"PlayResY: {HEIGHT}",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, "
        "Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, "
        "MarginL, MarginR, MarginV, Encoding",
        "Style: Default,Arial,64,&H00FFFFFF,&H00000000,&H64000000,"
        "1,0,0,0,100,100,0,0,1,4,0,2,60,60,120,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    count = 0
    for seg in segments:
        start = max(seg.start, moment.start)
        end = min(seg.end, moment.end)
        if end <= start:
            continue
        text = seg.text.replace("\n", " ").strip()
        if not text:
            continue
        lines.append(
            f"Dialogue: 0,{_ass_time(start - moment.start)},{_ass_time(end - moment.start)},"
            f"Default,,0,0,0,,{text}"
        )
        count += 1
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    if count == 0:
        raise ValueError("nenhuma fala dentro da janela do clipe")
    return path


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg falhou ({proc.returncode}): {proc.stderr[-800:]}")


def cut_clip(
    video_path: str,
    moment: Moment,
    segments: list[Segment],
    outdir: str,
    index: int = 1,
    burn_captions: bool = True,
) -> ClipResult:
    """Corta o momento em 9:16 (1080x1920) e queima a legenda.

    O enquadramento e um corte central: sem rastreamento de rosto.
    """
    os.makedirs(outdir, exist_ok=True)
    ass_path = os.path.join(outdir, f"clip{index}.ass")
    write_captions(segments, moment, ass_path)

    out_path = os.path.join(outdir, f"clip{index}.mp4")
    vf = (
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={WIDTH}:{HEIGHT}"
    )
    if burn_captions:
        safe_ass = ass_path.replace("\\", "/").replace(":", "\\:")
        vf += f",subtitles='{safe_ass}'"
    _run([
        "ffmpeg", "-y",
        "-ss", f"{moment.start:.3f}",
        "-to", f"{moment.end:.3f}",
        "-i", video_path,
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        out_path,
    ])
    if not os.path.isfile(out_path):
        raise RuntimeError("ffmpeg terminou sem gerar o clipe")
    return ClipResult(path=out_path, moment=moment, captions_path=ass_path)

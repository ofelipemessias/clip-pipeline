"""CLI: python -m clip_pipeline <video-ou-url> [opcoes]"""
import argparse
import json
import os
import tempfile

from .downloader import resolve_input
from .editor import cut_clip
from .highlights import select_moments
from .transcribe import transcribe


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="clip-pipeline",
        description="Corta os melhores momentos de um video em clipes verticais (9:16) com legenda.",
    )
    parser.add_argument("source", help="caminho do video local ou URL")
    parser.add_argument("--count", type=int, default=3, help="quantidade de clipes (padrao: 3)")
    parser.add_argument("--min-len", type=float, default=10.0, help="duracao minima do clipe em s")
    parser.add_argument("--max-len", type=float, default=20.0, help="duracao maxima do clipe em s")
    parser.add_argument("--model", default="tiny", help="modelo whisper: tiny, base, small... (padrao: tiny)")
    parser.add_argument("--language", default=None, help="codigo do idioma, ex.: pt (padrao: auto)")
    parser.add_argument("--no-llm", action="store_true", help="ignora o Claude e usa so a heuristica")
    parser.add_argument("--outdir", default="clips", help="pasta de saida (padrao: clips/)")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        video = resolve_input(args.source, tmp)
        print(f"[1/3] video: {video}")
        segments = transcribe(video, model_size=args.model, language=args.language)
        print(f"[2/3] transcricao: {len(segments)} segmentos")
        moments, method = select_moments(
            segments, args.count, args.min_len, args.max_len, use_llm=not args.no_llm
        )
        if not moments:
            print("nenhum momento encontrado; tente --min-len menor")
            return 1
        origem = "Claude" if method == "llm" else "heuristica local"
        print(f"[3/3] {len(moments)} momentos ({origem}):")
        results = []
        for i, moment in enumerate(moments, start=1):
            result = cut_clip(video, moment, segments, args.outdir, index=i)
            results.append(result)
            print(f"  clip{i}: {moment.start:.1f}s-{moment.end:.1f}s -> {result.path}")
            if moment.reason:
                print(f"        {moment.reason}")

    meta_path = os.path.join(args.outdir, "metadata.json")
    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump(
            [
                {
                    "clip": r.path,
                    "start": r.moment.start,
                    "end": r.moment.end,
                    "reason": r.moment.reason,
                    "method": method,
                }
                for r in results
            ],
            fh,
            ensure_ascii=False,
            indent=2,
        )
    print(f"metadados: {meta_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

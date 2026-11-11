import os
import subprocess

import pytest

from clip_pipeline.editor import cut_clip, write_captions
from clip_pipeline.models import Moment, Segment

ffmpeg = pytest.mark.skipif(
    subprocess.run(["which", "ffmpeg"], capture_output=True).returncode != 0,
    reason="ffmpeg nao instalado",
)


@pytest.fixture
def sample_video(tmp_path):
    """Video sintetico de 6s com audio, gerado pelo proprio ffmpeg."""
    path = tmp_path / "sample.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "testsrc=duration=6:size=1280x720:rate=30",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=6",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
            str(path),
        ],
        check=True,
        capture_output=True,
    )
    return str(path)


def _probe(path, *args):
    return subprocess.run(
        ["ffprobe", "-v", "error", *args, path], capture_output=True, text=True, check=True
    ).stdout.strip()


@ffmpeg
def test_cut_clip_produces_vertical_video(sample_video, tmp_path):
    moment = Moment(start=1.0, end=4.0)
    segments = [Segment(start=1.2, end=2.5, text="primeira fala"), Segment(start=2.6, end=3.9, text="segunda fala")]
    result = cut_clip(sample_video, moment, segments, str(tmp_path / "out"), index=1)

    assert os.path.isfile(result.path)
    duration = float(_probe(result.path, "-show_entries", "format=duration", "-of", "csv=p=0"))
    assert duration == pytest.approx(3.0, abs=0.5)
    dims = _probe(result.path, "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0")
    assert dims == "1080,1920"


@ffmpeg
def test_cut_clip_rebases_captions(sample_video, tmp_path):
    moment = Moment(start=1.0, end=4.0)
    segments = [Segment(start=1.2, end=2.5, text="fala de teste")]
    outdir = str(tmp_path / "out")
    result = cut_clip(sample_video, moment, segments, outdir, index=2)

    with open(result.captions_path, encoding="utf-8") as fh:
        ass = fh.read()
    assert "fala de teste" in ass
    # janela comeca em 1.0s, entao a fala (1.2-2.5) vira 0.2-1.5 no clipe
    assert "0:00:00.20,0:00:01.50" in ass


def test_write_captions_rejects_empty_window(tmp_path):
    with pytest.raises(ValueError):
        write_captions(
            [Segment(start=10, end=12, text="fora da janela")],
            Moment(start=0, end=5),
            str(tmp_path / "x.ass"),
        )

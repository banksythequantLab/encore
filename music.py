"""Instrumental music beds, generated on the local GPU with ACE-Step 3.5B.

Same Genblaze pipeline as stills/clips/voice — the bed is a provenance-tracked
asset on B2 (comfyui/assets/...), then pulled to a temp file for ffmpeg.
"""
import os
import tempfile

BED_TAGS = ("cinematic film score, dark ambient, tension, orchestral hybrid, "
            "pulsing low percussion, atmospheric, instrumental, no vocals")


def generate_music_bed(tags: str = BED_TAGS, seconds: float = 32.0) -> str:
    """Generate an instrumental bed; returns a local temp file path (caller deletes)."""
    import pipeline
    from comfyui_provider import ComfyUIProvider, _b2
    from genblaze_core import Modality, Pipeline

    res = (Pipeline("music")
           .step(ComfyUIProvider(), model="ace-step-music", prompt=tags,
                 modality=Modality.AUDIO, params={"length": float(seconds)})
           .run(timeout=900, raise_on_failure=False))
    run, _m = pipeline._unpack(res)
    step = run.steps[-1]
    if not step.assets:
        raise RuntimeError(getattr(step, "error", None) or "music generation produced no audio")
    key = (step.assets[0].metadata or {}).get("b2_key")
    ext = key.rsplit(".", 1)[-1] if "." in key else "flac"
    fd, path = tempfile.mkstemp(suffix="." + ext)
    os.close(fd)
    with open(path, "wb") as f:
        f.write(_b2().get(key))
    return path

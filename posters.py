"""Episode key-art posters: generated on the local GPU, stored on B2 under posters/.

Poster key convention: posters/<show>/<episode-stem>.png where <episode-stem>
matches the episode mp4 filename (e.g. flooded-pursuit-b29fa1f3).
"""
import json


def poster_key(show: str, stem: str) -> str:
    return f"posters/{show}/{stem}.png"


def _show_style(show: str) -> str:
    from comfyui_provider import _b2
    try:
        doc = json.loads(_b2().get(f"vault/{show}/season.json").decode())
        return doc.get("style", "")
    except Exception:
        return ""


def generate_poster(show: str, title: str, stem: str, premise: str = "") -> str:
    """Generate 2:3 key art with z-image-turbo, upload to posters/. Returns the B2 key."""
    import pipeline
    from comfyui_provider import ComfyUIProvider, _b2
    from genblaze_core import Modality, Pipeline

    style = _show_style(show)
    prompt = (
        f"Cinematic streaming-service key art poster for the episode '{title}'. "
        + (f"Story: {premise}. " if premise else "")
        + (f"Visual style: {style}. " if style else "")
        + "Dramatic film-poster composition, moody high-contrast lighting, "
          "vertical one-sheet framing, epic scale. No text, no letters, no typography, no logos."
    )
    res = (Pipeline("poster")
           .step(ComfyUIProvider(), model=pipeline.IMAGE_MODEL, prompt=prompt,
                 modality=Modality.IMAGE, params={"width": 768, "height": 1152})
           .run(timeout=600, raise_on_failure=False))
    run, _m = pipeline._unpack(res)
    step = run.steps[-1]
    if not step.assets:
        raise RuntimeError(getattr(step, "error", None) or "poster generation produced no image")
    src_key = (step.assets[0].metadata or {}).get("b2_key")
    data = _b2().get(src_key)
    pkey = poster_key(show, stem)
    _b2().put(pkey, data)
    return pkey

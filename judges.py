"""
Vision judges for the self-correction loop.

Each judge takes an image URL (an asset already stored on B2) and returns a
genblaze EvaluationResult(passed, score, feedback). The loop feeds `feedback`
back into the next render as a correction hint.

Strategies (env JUDGE_STRATEGY):
  gmicloud    -> GMICloud vision chat model, on hackathon credits (default).
  dashscope   -> Qwen-VL via Derek's existing QWEN_API_KEY (eval step only;
                 this is what Filmwriter uses today — a guaranteed fallback).
  passthrough -> accept first render (dev only; no vision).

STATUS: FIRST DRAFT. The GMICloud vision model slug must be confirmed at
console.gmicloud.ai (marked VERIFY). dashscope path mirrors Filmwriter's
proven qwen-vl call.
"""
import json
import os
import re

import httpx

from genblaze_core import EvaluationResult

PASS_THRESHOLD = float(os.environ.get("JUDGE_PASS_THRESHOLD", "0.8"))
JUDGE_STRATEGY = os.environ.get("JUDGE_STRATEGY", "gmicloud")
GMI_VISION_MODEL = os.environ.get("GMI_VISION_MODEL", "Qwen2.5-VL-72B-Instruct")  # VERIFY slug
DASHSCOPE_VL_MODEL = os.environ.get("DASHSCOPE_VL_MODEL", "qwen-vl-max")
DASHSCOPE_URL = os.environ.get(
    "DASHSCOPE_URL",
    "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions",
)
QWEN_API_KEY = os.environ.get("QWEN_API_KEY")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434/api/chat")
OLLAMA_VISION_MODEL = os.environ.get("OLLAMA_VISION_MODEL", "qwen3-vl:8b-instruct")

RUBRIC = (
    "You are a strict film Visual-QA supervisor reviewing a single generated frame. "
    "Judge: (1) match to the shot intent, (2) correct spelling of any visible text, "
    "(3) anatomy (hands, faces, limb count), (4) cinematic quality. "
    'Return ONLY compact JSON: {"score": <0.0-1.0>, "passed": <bool>, '
    '"feedback": "<one concrete fix, or empty if passed>"}.'
)


def _parse(text: str) -> EvaluationResult:
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return EvaluationResult(passed=False, score=0.0,
                                feedback="judge returned no JSON")
    d = json.loads(m.group(0))
    score = float(d.get("score", 0) or 0)
    passed = bool(d.get("passed", score >= PASS_THRESHOLD))
    fb = (d.get("feedback") or "").strip() or None
    return EvaluationResult(passed=passed, score=score,
                            feedback=None if passed else fb)


def _messages(image_url: str, ctx: str):
    return [{
        "role": "user",
        "content": [
            {"type": "text", "text": f"{RUBRIC}\nShot intent: {ctx}"},
            {"type": "image_url", "image_url": {"url": image_url}},
        ],
    }]


def _gmicloud_judge(image_url: str, ctx: str) -> EvaluationResult:
    from genblaze_gmicloud import chat
    resp = chat(GMI_VISION_MODEL, messages=_messages(image_url, ctx), temperature=0)
    return _parse(resp.text)


def _dashscope_judge(image_url: str, ctx: str) -> EvaluationResult:
    body = {"model": DASHSCOPE_VL_MODEL, "temperature": 0,
            "messages": _messages(image_url, ctx)}
    r = httpx.post(DASHSCOPE_URL, json=body,
                   headers={"Authorization": f"Bearer {QWEN_API_KEY}"}, timeout=90)
    r.raise_for_status()
    return _parse(r.json()["choices"][0]["message"]["content"])


def make_judge(prompt_ctx: str = ""):
    """Return judge(image_ref) -> EvaluationResult for the given shot intent.
    image_ref may be an https URL or a data: URI (base64) — vision APIs accept both."""
    if JUDGE_STRATEGY == "mock":
        # Deterministic: fail the first take (forces one retry + lineage), pass the next.
        state = {"n": 0}

        def judge(image_ref: str) -> EvaluationResult:
            i = state["n"]
            state["n"] += 1
            if i == 0:
                return EvaluationResult(passed=False, score=0.55,
                                        feedback="stronger neon reflections, sharper rain, deeper contrast")
            return EvaluationResult(passed=True, score=0.9, feedback=None)
        return judge

    def judge(image_url: str) -> EvaluationResult:
        try:
            if JUDGE_STRATEGY == "gmicloud":
                return _gmicloud_judge(image_url, prompt_ctx)
            if JUDGE_STRATEGY == "dashscope":
                return _dashscope_judge(image_url, prompt_ctx)
        except Exception:  # noqa: BLE001
            # Fail open: keep the render, flag medium confidence, no retry loop stall.
            return EvaluationResult(passed=True, score=0.5, feedback=None)
        return EvaluationResult(passed=True, score=1.0, feedback=None)  # passthrough
    return judge


def _b64(ref: str) -> str:
    """Strip a data: URI prefix -> raw base64 (Ollama's images[] wants raw base64)."""
    return ref.split(",", 1)[1] if isinstance(ref, str) and ref.startswith("data:") else ref


def _sidebyside(a_ref: str, b_ref: str) -> str:
    """Composite two images into one side-by-side PNG (base64) so a single-image VLM
    reliably compares LEFT vs RIGHT."""
    import base64 as _b
    import io
    from PIL import Image
    def load(r):
        return Image.open(io.BytesIO(_b.b64decode(_b64(r)))).convert("RGB")
    a, bb = load(a_ref), load(b_ref)
    h = min(a.height, bb.height, 512) or 512
    a = a.resize((max(1, int(a.width * h / a.height)), h))
    bb = bb.resize((max(1, int(bb.width * h / bb.height)), h))
    canvas = Image.new("RGB", (a.width + bb.width + 16, h), (18, 18, 18))
    canvas.paste(a, (0, 0))
    canvas.paste(bb, (a.width + 16, 0))
    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    return _b.b64encode(buf.getvalue()).decode()


def make_identity_judge(anchor_ref: str, character: str = ""):
    """judge(candidate_ref) -> is the candidate the SAME character as the anchor? Sends BOTH
    images to a vision model (dashscope/gmicloud); falls through to accept for mock/dev."""
    rubric = ("Compare the two images. The FIRST is the reference character; the SECOND is a new "
              "shot. Return ONLY JSON {\"score\":0-1,\"passed\":bool,\"feedback\":\"one fix if not "
              "the same\"} where score = how strongly the SECOND is the SAME person/character "
              "(face, identity, wardrobe) as the FIRST.")

    def _msgs(candidate):
        return [{"role": "user", "content": [
            {"type": "text", "text": rubric + (f" Character: {character}." if character else "")},
            {"type": "image_url", "image_url": {"url": anchor_ref}},
            {"type": "image_url", "image_url": {"url": candidate}},
        ]}]

    def judge(candidate_ref: str) -> EvaluationResult:
        try:
            if JUDGE_STRATEGY in ("ollama", "local"):
                combined = _sidebyside(anchor_ref, candidate_ref)
                prompt = ("The image has TWO panels side by side. LEFT = the reference character; "
                          "RIGHT = a new shot. Return ONLY JSON {\"score\":0-1,\"passed\":bool,"
                          "\"feedback\":\"one concrete fix if not the same\"} where score = how strongly "
                          "the RIGHT character is the SAME identity (face, body, wardrobe, colors) as the "
                          "LEFT. Be strict: a different person or robot scores below 0.4."
                          + (f" Character: {character}." if character else ""))
                b = {"model": OLLAMA_VISION_MODEL, "stream": False, "format": "json",
                     "options": {"temperature": 0},
                     "messages": [{"role": "user", "content": prompt, "images": [combined]}]}
                rr = httpx.post(OLLAMA_URL, json=b, timeout=180)
                rr.raise_for_status()
                return _parse(rr.json()["message"]["content"])
            if JUDGE_STRATEGY == "dashscope":
                r = httpx.post(DASHSCOPE_URL,
                               json={"model": DASHSCOPE_VL_MODEL, "temperature": 0, "messages": _msgs(candidate_ref)},
                               headers={"Authorization": f"Bearer {QWEN_API_KEY}"}, timeout=90)
                r.raise_for_status()
                return _parse(r.json()["choices"][0]["message"]["content"])
            if JUDGE_STRATEGY == "gmicloud":
                from genblaze_gmicloud import chat
                return _parse(chat(GMI_VISION_MODEL, messages=_msgs(candidate_ref), temperature=0).text)
        except Exception:  # noqa: BLE001
            return EvaluationResult(passed=True, score=0.5, feedback=None)
        return EvaluationResult(passed=True, score=1.0, feedback=None)
    return judge

"""
Filmwriter / TrueSeal generation pipelines on Genblaze, backed by local ComfyUI (free) + B2.

- Generation runs on ComfyUI via ComfyUIProvider (uploads raw output to B2, sets SHA-256).
- Pipelines run SINK-LESS (Genblaze's sink mis-parses Windows file:// paths); we persist manifests to B2.
- seal_and_lock(): after generation, the manifest is embedded INTO the file (self-verifying) and the
  sealed copy is stored on B2; the manifest is also stored IMMUTABLY (Object Lock) in the sealed bucket.
- gen_still runs the agentic self-correction loop: render -> judge -> retry with from_result lineage.
"""
import base64
import datetime
import os
import tempfile

from genblaze_core import Modality, ObjectLockConfig, Pipeline

from comfyui_provider import ComfyUIProvider, _b2

IMAGE_MODEL = os.environ.get("COMFY_IMAGE_MODEL", "z-image-turbo")
EDIT_MODEL = os.environ.get("COMFY_EDIT_MODEL", "qwen-image-edit")
VIDEO_I2V_MODEL = os.environ.get("COMFY_VIDEO_I2V_MODEL", "wan22-i2v")
VIDEO_T2V_MODEL = os.environ.get("COMFY_VIDEO_T2V_MODEL", "wan22-t2v")
VOICE_MODEL = os.environ.get("COMFY_VOICE_MODEL", "tts-custom-voice")
B2_REGION = os.environ.get("B2_REGION", "us-east-005")
B2_SEALED_BUCKET = os.environ.get("B2_SEALED_BUCKET", "filmwriter-sealed")
LOCK_DAYS = int(os.environ.get("B2_LOCK_DAYS", "365"))

_ASPECT = {"16:9": (1024, 576), "9:16": (576, 1024), "1:1": (1024, 1024), "4:3": (1024, 768)}


def _unpack(result):
    run = getattr(result, "run", None)
    manifest = getattr(result, "manifest", None)
    if run is not None and manifest is not None:
        return run, manifest
    return result[0], result[1]


def persist_manifest(manifest, run) -> str:
    key = f"comfyui/manifests/{run.run_id}.json"
    _b2().put(key, manifest.to_canonical_json().encode())
    return key


_SEALED_B2 = None


def _sealed_b2():
    global _SEALED_B2
    if _SEALED_B2 is None:
        from genblaze_s3 import S3StorageBackend
        _SEALED_B2 = S3StorageBackend.for_backblaze(B2_SEALED_BUCKET, region=B2_REGION)
    return _SEALED_B2


def seal_and_lock(rec: dict, manifest) -> dict:
    """Seal the manifest INTO the generated file (self-verifying), store the sealed copy on
    B2, and store the manifest IMMUTABLY (Object Lock, GOVERNANCE) in the sealed bucket."""
    import mimetypes
    from pathlib import Path
    from genblaze_core.media import get_handler
    try:
        raw = _b2().get(rec["b2_key"])
        ext = os.path.splitext(rec["b2_key"])[1]
        tmp = Path(tempfile.gettempdir()) / f"seal_{rec['sha256'][:12]}{ext}"
        tmp.write_bytes(raw)
        mime = rec.get("media_type") or mimetypes.guess_type(str(tmp))[0] or "application/octet-stream"
        get_handler(mime).embed(tmp, manifest)          # seal manifest into the file
        skey = f"sealed/{rec['sha256'][:2]}/{rec['sha256']}{ext}"
        _b2().put(skey, tmp.read_bytes())
        rec["sealed_key"] = skey
        rec["sealed_url"] = _b2().get_durable_url(skey)
        rec["sealed"] = True
        tmp.unlink()
    except Exception as e:  # noqa: BLE001
        rec["sealed"] = False
        rec["seal_error"] = repr(e)
    try:
        until = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=LOCK_DAYS)
        _sealed_b2().put(f"manifests/{rec['run_id']}.json",
                         manifest.to_canonical_json().encode(),
                         object_lock=ObjectLockConfig(retain_until=until, mode="GOVERNANCE"))
        rec["locked"] = True
    except Exception as e:  # noqa: BLE001
        rec["locked"] = False
        rec["lock_error"] = repr(e)
    return rec


def _asset_record(run, manifest) -> dict:
    step = run.steps[-1]
    assets = getattr(step, "assets", None) or []
    if not assets:
        err = getattr(step, "error", None) or getattr(step, "error_code", None) or "no asset"
        raise RuntimeError(f"generation failed ({getattr(step, 'model', '?')}): {err}")
    a = assets[0]
    return {
        "url": a.url, "sha256": a.sha256, "size": a.size_bytes,
        "b2_key": (a.metadata or {}).get("b2_key"),
        "media_type": a.media_type, "run_id": run.run_id,
        "manifest_uri": getattr(manifest, "manifest_uri", None),
        "canonical_hash": getattr(manifest, "canonical_hash", None),
    }


def _image_data_uri(rec) -> str:
    data = _b2().get(rec["b2_key"])
    b64 = base64.b64encode(data).decode()
    return f"data:{rec.get('media_type', 'image/png')};base64,{b64}"


def _b2_key_to_tempfile(key: str) -> str:
    data = _b2().get(key)
    ext = os.path.splitext(key)[1] or ".png"
    fd, path = tempfile.mkstemp(suffix=ext)
    os.close(fd)
    with open(path, "wb") as f:
        f.write(data)
    return path


def gen_still(prompt, judge, *, aspect_ratio="16:9", run_name="shot", max_iter=3, timeout=900):
    """Agentic self-correction loop on ComfyUI + B2, then seal + lock the chosen still."""
    w, h = _ASPECT.get(aspect_ratio, (1024, 576))
    prev = None
    iterations = []
    best = None
    best_manifest = None
    for i in range(max_iter):
        p = prompt
        if iterations and iterations[-1].get("feedback"):
            p = f"{prompt} -- correction: {iterations[-1]['feedback']}"
        pipe = Pipeline(f"{run_name}-still")
        if prev is not None:
            pipe = pipe.from_result(prev)  # lineage: parent_run_id
        pipe = pipe.step(ComfyUIProvider(), model=IMAGE_MODEL, prompt=p,
                         modality=Modality.IMAGE, params={"width": w, "height": h})
        result = pipe.run(timeout=timeout, raise_on_failure=False)
        run, manifest = _unpack(result)
        rec = _asset_record(run, manifest)
        persist_manifest(manifest, run)

        ev = judge(_image_data_uri(rec))
        rec.update({"iteration": i, "score": ev.score, "passed": ev.passed, "feedback": ev.feedback})
        iterations.append(rec)
        if best is None or (ev.score or 0) > (best.get("score") or 0):
            best = rec
            best_manifest = manifest
        prev = result
        if ev.passed:
            break

    if best and best_manifest is not None:
        seal_and_lock(best, best_manifest)

    return {
        "kind": "still", "passed": any(it["passed"] for it in iterations),
        "chosen": best, "iterations": iterations, "retakes": max(0, len(iterations) - 1),
    }


def gen_video(*, prompt, image_b2_key=None, image_path=None, aspect_ratio="16:9",
              run_name="shot", duration=None, timeout=900):
    model = VIDEO_I2V_MODEL if (image_b2_key or image_path) else VIDEO_T2V_MODEL
    params = {}
    if duration:
        params["length"] = duration
    if image_b2_key:
        params["image"] = _b2_key_to_tempfile(image_b2_key)
    elif image_path:
        params["image"] = image_path
    result = (
        Pipeline(f"{run_name}-video")
        .step(ComfyUIProvider(), model=model, prompt=prompt, modality=Modality.VIDEO, params=params)
        .run(timeout=timeout, raise_on_failure=False)
    )
    run, manifest = _unpack(result)
    rec = _asset_record(run, manifest)
    persist_manifest(manifest, run)
    seal_and_lock(rec, manifest)
    rec.update({"kind": "video", "model": model})
    return rec


def gen_voice(*, text, model=None, voice=None, run_name="shot", timeout=600):
    params = {}
    if voice:
        params["voice"] = voice
    result = (
        Pipeline(f"{run_name}-voice")
        .step(ComfyUIProvider(), model=model or VOICE_MODEL, prompt=text,
              modality=Modality.AUDIO, params=params)
        .run(timeout=timeout, raise_on_failure=False)
    )
    run, manifest = _unpack(result)
    rec = _asset_record(run, manifest)
    persist_manifest(manifest, run)
    seal_and_lock(rec, manifest)
    rec["kind"] = "audio"
    return rec


def read_provenance(run_id: str) -> dict:
    key = f"comfyui/manifests/{run_id}.json"
    raw = _b2().get(key)
    text = raw.decode() if isinstance(raw, (bytes, bytearray)) else str(raw)
    out = {"run_id": run_id, "key": key, "manifest": text, "verified": None}
    try:
        from genblaze_core import Manifest
        m = Manifest.from_json(text)
        out["verified"] = bool(m.verify())
        out["canonical_hash"] = m.canonical_hash
    except Exception as e:  # noqa: BLE001
        out["verify_error"] = repr(e)
    return out

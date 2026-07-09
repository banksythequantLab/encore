"""
ComfyUI -> Genblaze provider.

Drives a local ComfyUI (127.0.0.1:8188) through Genblaze's BaseProvider
submit/poll/fetch_output lifecycle, using the existing workflow templates in the
{id,type,inputs,outputs,workflow} wrapper format under B:\\MaiVid\\workflows.

Free local generation (no API credits) flowing through the same Genblaze
Pipeline + AgentLoop + B2 provenance as any cloud provider — and a feedback-prize
contribution (a new self-hosted provider).

STATUS: first draft. Validate with a live ComfyUI run (free) before trusting.
Open items marked VERIFY.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import random
import tempfile
import urllib.parse
import uuid
from typing import Any

import httpx

from genblaze_core.exceptions import ProviderError
from genblaze_core.models.asset import Asset, AudioMetadata, VideoMetadata
from genblaze_core.models.enums import Modality, ProviderErrorCode
from genblaze_core.models.step import Step
from genblaze_core.providers import BaseProvider

COMFY_SERVER = os.environ.get("COMFY_SERVER", "127.0.0.1:8188")
COMFY_WORKFLOWS = os.environ.get("COMFY_WORKFLOWS", r"B:\MaiVid\workflows")
COMFY_STAGE = os.environ.get("COMFY_STAGE") or os.path.join(tempfile.gettempdir(), "genblaze_comfy")

# friendly model aliases -> workflow file stem (any real workflow stem also works)
MODEL_ALIASES = {
    "still": "z-image-turbo", "image": "z-image-turbo", "edit": "qwen-image-edit",
    "video": "wan22-i2v-fixed", "i2v": "wan22-i2v-fixed", "wan22-i2v": "wan22-i2v-fixed",
    "t2v": "wan22-t2v", "ltx": "ltx23-i2v",
}
_MIME = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp",
         "mp4": "video/mp4", "webm": "video/webm", "gif": "image/gif",
         "wav": "audio/wav", "mp3": "audio/mpeg", "flac": "audio/flac"}


def _http() -> httpx.Client:
    return httpx.Client(base_url=f"http://{COMFY_SERVER}", timeout=120)


_B2 = None


def _b2():
    """Lazy B2 backend. The provider stores its own outputs: Genblaze's sink
    mis-parses Windows file:// paths, and a private bucket can't be re-fetched
    from a durable URL, so we upload the bytes here."""
    global _B2
    if _B2 is None:
        from genblaze_s3 import S3StorageBackend
        _B2 = S3StorageBackend.for_backblaze(
            os.environ["B2_BUCKET"], region=os.environ.get("B2_REGION"))
    return _B2


def _load_template(model: str) -> dict:
    stem = MODEL_ALIASES.get(model, model)
    path = os.path.join(COMFY_WORKFLOWS, stem + ".json")
    if not os.path.exists(path):
        raise ProviderError(f"ComfyUI workflow not found for model '{model}' ({path})",
                            error_code=ProviderErrorCode.MODEL_ERROR)
    with open(path, encoding="utf-8-sig") as f:  # utf-8-sig tolerates a BOM (some workflows have one)
        return json.load(f)


def _set_input(graph: dict, inputs_map: dict, key: str, value: Any) -> bool:
    spec = inputs_map.get(key)
    if not spec:
        return False
    graph[spec["nodeId"]]["inputs"][spec["field"]] = value
    return True


def _map_status(code: int) -> ProviderErrorCode:
    if code in (401, 403):
        return ProviderErrorCode.AUTH_FAILURE
    if code == 404:
        return ProviderErrorCode.MODEL_ERROR
    if code == 429:
        return ProviderErrorCode.RATE_LIMIT
    if 500 <= code < 600:
        return ProviderErrorCode.SERVER_ERROR
    return ProviderErrorCode.INVALID_INPUT


class ComfyUIProvider(BaseProvider):
    name = "comfyui"

    def __init__(self, *, image_ref=None, models=None, retry_policy=None):
        super().__init__(models=models, retry_policy=retry_policy)
        self._image_ref = image_ref

    def submit(self, step: Step, config=None):
        tpl = _load_template(step.model)
        graph = tpl["workflow"]
        imap = tpl.get("inputs", {})
        params = step.params or {}

        _set_input(graph, imap, "prompt", step.prompt or "")
        if step.negative_prompt:
            _set_input(graph, imap, "negative_prompt", step.negative_prompt)
        seed = step.seed if step.seed not in (None, -1) else random.randint(1, 2**31 - 1)
        _set_input(graph, imap, "seed", seed)
        for k in ("width", "height", "length", "fps", "steps", "cfg"):
            if k in params:
                _set_input(graph, imap, k, params[k])

        # image-to-video / edit: stage an input image into ComfyUI
        img = params.get("image_url") or params.get("image") or self._image_ref
        if not img and step.inputs:
            img = step.inputs[0].url
        if img and "image" in imap:
            _set_input(graph, imap, "image", self._stage_input_image(img))

        _set_input(graph, imap, "filename_prefix", f"gb_{uuid.uuid4().hex[:10]}")

        try:
            with _http() as c:
                r = c.post("/prompt", json={"prompt": graph, "client_id": uuid.uuid4().hex})
            if r.status_code >= 400:
                raise ProviderError(f"ComfyUI /prompt {r.status_code}: {r.text[:300]}",
                                    error_code=_map_status(r.status_code))
            data = r.json()
            if data.get("node_errors"):
                raise ProviderError(f"ComfyUI node_errors: {json.dumps(data['node_errors'])[:300]}",
                                    error_code=ProviderErrorCode.INVALID_INPUT)
            return data["prompt_id"]
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(f"ComfyUI submit failed: {exc}",
                                error_code=ProviderErrorCode.SERVER_ERROR) from exc

    def poll(self, prediction_id, config=None) -> bool:
        try:
            with _http() as c:
                hist = c.get(f"/history/{prediction_id}").json()
        except Exception:
            return False
        rec = hist.get(prediction_id)
        if not rec:
            return False
        status = (rec.get("status") or {}).get("status_str", "")
        if status in ("success", "error") or rec.get("outputs"):
            self._cache_poll_result(prediction_id, rec)
            return True
        return False

    def fetch_output(self, prediction_id, step: Step) -> Step:
        rec = self._get_cached_poll_result(prediction_id)
        if rec is None:
            with _http() as c:
                rec = c.get(f"/history/{prediction_id}").json().get(prediction_id, {})
        if (rec.get("status") or {}).get("status_str", "") == "error":
            raise ProviderError(f"ComfyUI run errored: {json.dumps(rec.get('status'))[:300]}",
                                error_code=ProviderErrorCode.SERVER_ERROR)
        files = self._collect_outputs(rec.get("outputs", {}))
        if not files:
            raise ProviderError("ComfyUI produced no output files",
                                error_code=ProviderErrorCode.SERVER_ERROR)
        for filename, subfolder, ftype, kind in files:
            data = self._download_bytes(filename, subfolder, ftype)
            ext = filename.rsplit(".", 1)[-1].lower()
            sha = hashlib.sha256(data).hexdigest()
            key = f"comfyui/assets/{sha[:2]}/{sha[2:4]}/{sha}.{ext}"
            _b2().put(key, data)
            asset = Asset(url=_b2().get_durable_url(key),
                          media_type=_MIME.get(ext, "application/octet-stream"),
                          sha256=sha, size_bytes=len(data))
            asset.metadata = {"b2_key": key, "provider": "comfyui"}
            if kind == "video":
                asset.video = VideoMetadata(has_audio=False, codec="h264")  # VERIFY codec
            elif kind == "audio":
                asset.audio = AudioMetadata(channels=2, codec=ext)
            step.assets.append(asset)
        return step

    def _collect_outputs(self, outputs: dict):
        found = []
        for _nid, no in outputs.items():
            for i in no.get("images", []):
                found.append((i["filename"], i.get("subfolder", ""), i.get("type", "output"), "image"))
            for v in no.get("gifs", []) + no.get("videos", []):
                found.append((v["filename"], v.get("subfolder", ""), v.get("type", "output"), "video"))
            for a in no.get("audio", []):
                found.append((a["filename"], a.get("subfolder", ""), a.get("type", "output"), "audio"))
        return found

    def _download_bytes(self, filename, subfolder, ftype) -> bytes:
        q = urllib.parse.urlencode({"filename": filename, "subfolder": subfolder, "type": ftype})
        with _http() as c:
            r = c.get(f"/view?{q}")
            r.raise_for_status()
            return r.content

    def _stage_input_image(self, url_or_path: str) -> str:
        if url_or_path.startswith("http"):
            data = httpx.get(url_or_path, timeout=120).content
        else:
            p = url_or_path[7:] if url_or_path.startswith("file://") else url_or_path
            p = p.lstrip("/") if os.name == "nt" and p.startswith("/") else p
            with open(p, "rb") as f:
                data = f.read()
        name = f"gbin_{uuid.uuid4().hex[:8]}.png"
        with _http() as c:
            r = c.post("/upload/image", files={"image": (name, data, "image/png")},
                       data={"overwrite": "true"})
            r.raise_for_status()
            return r.json().get("name", name)

    def get_capabilities(self):
        from genblaze_core.providers import ProviderCapabilities
        return ProviderCapabilities(
            supported_modalities=[Modality.IMAGE, Modality.VIDEO, Modality.AUDIO],
            supported_inputs=["text", "image"],
            models=list(MODEL_ALIASES.keys()),
            output_formats=["image/png", "video/mp4", "audio/wav"],
        )

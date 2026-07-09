"""
Identity-anchored episode generation — the moat.

Bring a character from the B2 Series Vault into a NEW scene, keeping the SAME identity.
Uses ComfyUI qwen-image-edit conditioned on the vault anchor, with a self-correction loop
that re-takes until the character matches the anchor. Each chosen shot is sealed and its
manifest Object-Locked, linked to the vault (lineage).

UNVERIFIED against a live render (needs GPU) — the pieces underneath are all proven:
vault.anchor_tempfile (B2), ComfyUIProvider image-edit, AgentLoop lineage, seal_and_lock.
"""
import os

import httpx
from genblaze_core import Modality, Pipeline

import pipeline
import vault
from comfyui_provider import ComfyUIProvider

EDIT_MODEL = os.environ.get("COMFY_EDIT_MODEL", "qwen-image-edit")


def _free_comfy():
    """Release ComfyUI VRAM so the local vision judge (Ollama) can load without OOM.
    Without this, the edit model + Qwen3-VL contend for the GPU and the judge errors
    out (degrading self-correction to a passthrough accept)."""
    try:
        httpx.post("http://127.0.0.1:8188/free",
                   json={"unload_models": True, "free_memory": True}, timeout=15)
    except Exception:
        pass


def gen_episode_shot(show, character, scene_prompt, judge, *, run_name="ep", max_iter=3, timeout=900):
    """Generate a shot of `character` (from the B2 vault) in a new scene, self-correcting
    until identity matches the anchor. Returns a sealed record linked to the vault."""
    anchor_path = vault.anchor_tempfile(show, character)   # pull the anchor from B2
    try:
        prev = None
        iterations = []
        best = None
        best_manifest = None
        for i in range(max_iter):
            instruction = (f"Keep this exact character identical (same face, same wardrobe). "
                           f"New scene: {scene_prompt}")
            if iterations and iterations[-1].get("feedback"):
                instruction += f" -- fix: {iterations[-1]['feedback']}"
            pipe = Pipeline(f"{run_name}-{show}-{character}")
            if prev is not None:
                pipe = pipe.from_result(prev)          # lineage across retakes
            pipe = pipe.step(ComfyUIProvider(image_ref=anchor_path), model=EDIT_MODEL,
                             prompt=instruction, modality=Modality.IMAGE)
            result = pipe.run(timeout=timeout, raise_on_failure=False)
            run, manifest = pipeline._unpack(result)
            rec = pipeline._asset_record(run, manifest)
            pipeline.persist_manifest(manifest, run)

            _free_comfy()  # free the edit model so the local vision judge has VRAM
            ev = judge(pipeline._image_data_uri(rec))  # identity check vs the anchor
            rec.update({"iteration": i, "score": ev.score, "passed": ev.passed, "feedback": ev.feedback})
            iterations.append(rec)
            if best is None or (ev.score or 0) > (best.get("score") or 0):
                best = rec
                best_manifest = manifest
            prev = result
            if ev.passed:
                break

        if best and best_manifest is not None:
            pipeline.seal_and_lock(best, best_manifest)
            best["show"] = show
            best["character"] = character
        return {
            "show": show, "character": character,
            "passed": any(it["passed"] for it in iterations),
            "chosen": best, "iterations": iterations,
            "retakes": max(0, len(iterations) - 1),
        }
    finally:
        try:
            os.remove(anchor_path)
        except OSError:
            pass

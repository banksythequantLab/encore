"""
produce_episode — the whole studio, top to bottom, 100% local + B2.

  plan (Ollama)  ->  for each scene:
      pull cast anchor from B2 Series Vault
      qwen-image-edit keyframe, self-correcting vs the anchor (local Qwen3-VL judge)
      Wan 2.2 image-to-video (aspect-matched)  ->  scene clip on B2
      narrate the line in a cloned voice (FreeClone)
  compose (ffmpeg): title card + captioned scenes + end card
  seal: embed manifest -> B2 episode + Object-Locked canon

Every stage is a Genblaze run through our local ComfyUI provider; nothing leaves the box
except the durable artifacts we write to Backblaze B2.
"""
from __future__ import annotations

import base64
import json
import os
import sys
import tempfile
import time

import httpx
from genblaze_core import Modality, Pipeline

import composer
import episode
import pipeline
import vault
from comfyui_provider import ComfyUIProvider, _b2
from judges import make_identity_judge
from planner import plan_episode

try:
    from PIL import Image
except Exception:
    Image = None

VOICE_URL = os.environ.get("VOICE_URL", "http://127.0.0.1:8300/api/clone")
VOICE_REF = os.environ.get("VOICE_REF", r"B:\freeclone-backend\derek-voice.wav")
COMFY = "http://127.0.0.1:8188"
OLLAMA = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")


PROGRESS = None  # optional callback(msg) so a UI can stream build progress


def set_progress(cb):
    global PROGRESS
    PROGRESS = cb


def _log(*a):
    msg = " ".join(str(x) for x in a)
    print(msg, flush=True)
    if PROGRESS:
        try:
            PROGRESS(msg)
        except Exception:
            pass


def _free_gpu(stop_models=("qwen3-vl:8b-instruct", "qwen3:8b")):
    """Give the next heavy model room: unload ComfyUI models + stop Ollama models."""
    try:
        httpx.post(f"{COMFY}/free", json={"unload_models": True, "free_memory": True}, timeout=15)
    except Exception:
        pass
    for m in stop_models:
        try:
            httpx.post(f"{OLLAMA}/api/generate", json={"model": m, "keep_alive": 0, "prompt": ""}, timeout=15)
        except Exception:
            pass


def _keyframe_png(chosen: dict) -> str:
    uri = pipeline._image_data_uri(chosen)
    data = base64.b64decode(uri.split(",", 1)[1])
    fd, p = tempfile.mkstemp(suffix="_kf.png")
    os.close(fd)
    with open(p, "wb") as f:
        f.write(data)
    return p


def _i2v_dims(kf: str, long_side: int = 832):
    if Image is None:
        return 832, 480
    w, h = Image.open(kf).size
    s = long_side / max(w, h)
    tw = max(320, int(round(w * s / 16)) * 16)
    th = max(320, int(round(h * s / 16)) * 16)
    return tw, th


def _i2v_clip(kf: str, motion_prompt: str, length: int = 49, timeout: int = 1500):
    tw, th = _i2v_dims(kf)
    result = (Pipeline("encore")
              .step(ComfyUIProvider(image_ref=kf), model="wan22-i2v",
                    prompt=motion_prompt, modality=Modality.VIDEO,
                    params={"width": tw, "height": th, "length": length})
              .run(timeout=timeout, raise_on_failure=False))
    run, _m = pipeline._unpack(result)
    step = run.steps[-1]
    if not step.assets:
        raise RuntimeError(f"i2v produced no asset: {getattr(step, 'error', None)}")
    a = step.assets[0]
    key = (a.metadata or {}).get("b2_key")
    data = _b2().get(key)
    fd, p = tempfile.mkstemp(suffix="_clip.mp4")
    os.close(fd)
    with open(p, "wb") as f:
        f.write(data)
    return p, {"url": a.url, "sha256": a.sha256, "b2_key": key, "size": a.size_bytes, "dims": [tw, th]}


def _extract_last_frame(mp4: str) -> str:
    """Grab the final frame of a clip as a PNG (the next segment's start image)."""
    fd, p = tempfile.mkstemp(suffix="_last.png")
    os.close(fd)
    composer._run([composer.FFMPEG, "-y", "-sseof", "-0.25", "-i", mp4,
                   "-update", "1", "-frames:v", "1", p])
    return p


def _i2v_clip_chained(kf: str, motion_prompt: str, length: int | None = None,
                      segments: int | None = None, timeout: int = 1500):
    """Long take: chain Wan 2.2 segments — each segment starts from the previous
    segment's last frame — then concat into one continuous shot.
    Defaults: I2V_LENGTH=49 frames/segment (~3s, proven fast on this card),
    I2V_SEGMENTS=3 (~9s continuous shot per scene). 81f/832px thrashes 24GB VRAM."""
    length = length or int(os.environ.get("I2V_LENGTH", "49"))
    segments = segments or int(os.environ.get("I2V_SEGMENTS", "3"))
    clips, infos = [], []
    start = kf
    for i in range(segments):
        seg_prompt = motion_prompt if i == 0 else (
            motion_prompt + ", continuing the same continuous shot without a cut")
        _log(f"  i2v segment {i + 1}/{segments} ({length} frames)")
        clip, cinfo = _i2v_clip(start, seg_prompt, length=length, timeout=timeout)
        clips.append(clip)
        infos.append(cinfo)
        if i < segments - 1:
            start = _extract_last_frame(clip)
    if len(clips) == 1:
        return clips[0], infos[0]
    fd, joined = tempfile.mkstemp(suffix="_long.mp4")
    os.close(fd)
    n = len(clips)
    inputs = []
    for c in clips:
        inputs += ["-i", c]
    filt = "".join(f"[{i}:v]" for i in range(n)) + f"concat=n={n}:v=1:a=0[v]"
    composer._run([composer.FFMPEG, "-y", *inputs, "-filter_complex", filt,
                   "-map", "[v]", "-c:v", "libx264", "-crf", "18",
                   "-pix_fmt", "yuv420p", joined])
    info = dict(infos[-1])
    info["dims"] = infos[0]["dims"]
    info["segments"] = infos
    return joined, info


def _synth_vo(text: str):
    if not text:
        return None
    try:
        with open(VOICE_REF, "rb") as f:
            r = httpx.post(VOICE_URL, files={"prompt_audio": ("ref.wav", f, "audio/wav")},
                           data={"text": text, "lang": "en"}, timeout=1800)
        if r.status_code == 200 and len(r.content) > 4000:
            fd, p = tempfile.mkstemp(suffix="_vo.wav")
            os.close(fd)
            with open(p, "wb") as fh:
                fh.write(r.content)
            return p
        _log("  VO_ERR", r.status_code, r.text[:120])
    except Exception as e:  # noqa: BLE001
        _log("  VO_EXC", type(e).__name__, str(e)[:120])
    return None


def produce_episode(show: str, character: str, premise: str, n_scenes: int = 2,
                    max_iter: int = 2, music_path: str | None = None,
                    out_dir: str | None = None) -> dict:
    t_start = time.time()
    out_dir = out_dir or tempfile.mkdtemp(prefix="encore_ep_")
    style = ""
    try:
        style = vault.load_cast_from_b2(show).get("style", "")
    except Exception:
        pass

    _log("== PLAN (local Ollama) ==")
    import season
    mem = season.load_memory(show)
    prev = season.previously_text(mem, k=2)
    prev_line = season.previously_line(mem)
    if prev:
        _log(f"  season memory: {len(mem['episodes'])} prior episode(s) recalled from B2")
    _free_gpu()
    spec = plan_episode(show, character, premise, n_scenes, style, previously=prev)
    _log("  title:", spec.episode_title)
    for s in spec.scenes:
        _log(f"  scene {s.scene_id}: {s.location} | {s.caption}")

    anchor_uri = None
    try:
        cast = {c["name"].lower(): c for c in vault.load_cast_from_b2(show)["cast"]}
        anchor_uri = cast[character.lower()].get("dataUri")
    except Exception as e:  # noqa: BLE001
        _log("  anchor load warn:", e)
    judge = make_identity_judge(anchor_uri, character) if anchor_uri else (lambda ref: _passthru())

    scenes_out = []
    for s in spec.scenes:
        _log(f"== SCENE {s.scene_id}: keyframe (self-correct) ==")
        _free_gpu()
        shot = episode.gen_episode_shot(show, character, s.keyframe_prompt, judge,
                                        run_name="ep", max_iter=max_iter, timeout=1200)
        chosen = shot.get("chosen")
        if not chosen:
            _log("  scene skipped (no keyframe)")
            continue
        _log(f"  keyframe score={chosen.get('score')} passed={shot.get('passed')} retakes={shot.get('retakes')}")
        kf = _keyframe_png(chosen)

        _log(f"== SCENE {s.scene_id}: i2v (Wan 2.2) ==")
        _free_gpu()  # drop qwen-edit + vision so Wan has VRAM
        clip, cinfo = _i2v_clip_chained(kf, s.motion_prompt)
        nseg = len(cinfo.get("segments", [1]))
        _log(f"  long take: {nseg} chained segment(s)")
        _log(f"  clip {cinfo['dims']} sha={cinfo['sha256'][:12]} size={cinfo['size']}")

        _log(f"== SCENE {s.scene_id}: narration (cloned voice) ==")
        vo = _synth_vo(s.narration)
        _log("  vo:", os.path.basename(vo) if vo else "(none)")

        scenes_out.append({"clip": clip, "vo": vo, "scene_no": s.scene_id,
                           "location": s.location, "caption": s.caption,
                           "narration": s.narration, "keyframe": chosen, "clip_info": cinfo})

    if not scenes_out:
        raise RuntimeError("no scenes produced")

    _log("== COMPOSE (ffmpeg) ==")
    _free_gpu()
    ep_mp4 = os.path.join(out_dir, "episode.mp4")
    composer.compose_episode(spec, scenes_out, ep_mp4, music_path=music_path,
                             previously=prev_line or None)
    dur = composer._dur(ep_mp4)
    _log(f"  composed {ep_mp4} dur={dur:.1f}s size={os.path.getsize(ep_mp4)}")

    _log("== STORE -> Backblaze B2 (episode library) ==")
    stored = composer.store_episode_to_b2(spec, ep_mp4)
    _log("  B2", stored["b2_key"], "size", stored["size"])
    try:
        season.record_episode(show, spec, stored)
        _log("  season memory updated on B2 (episode", len(mem["episodes"]) + 1, ")")
    except Exception as se:  # noqa: BLE001
        _log("  season memory write warn:", se)

    summary = {
        "show": show, "character": character, "episode_title": spec.episode_title,
        "logline": spec.logline, "scenes": len(scenes_out),
        "local_mp4": ep_mp4, "duration_s": round(dur, 2),
        "episode": stored,
        "scene_clips": [x["clip_info"] for x in scenes_out],
        "seconds_elapsed": round(time.time() - t_start, 1),
    }
    with open(os.path.join(os.path.dirname(__file__), "_episode_proof.json"), "w") as f:
        json.dump(summary, f, indent=2)
    _log("== DONE ==", round(summary["seconds_elapsed"], 1), "s")
    return summary


class _passthru:
    passed, score, feedback = True, 0.5, None


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    show = sys.argv[1] if len(sys.argv) > 1 else "warlords-sniper"
    character = sys.argv[2] if len(sys.argv) > 2 else "Lena"
    premise = (sys.argv[3] if len(sys.argv) > 3 else
               "A lone sniper hunts a warlord across a rain-soaked city over one long night.")
    n = int(sys.argv[4]) if len(sys.argv) > 4 else 2
    produce_episode(show, character, premise, n_scenes=n,
                    out_dir=os.path.dirname(os.path.abspath(__file__)))

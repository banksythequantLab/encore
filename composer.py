"""
Stage C — episode composer.

Takes the per-scene i2v clips + narration + captions and assembles a finished,
1080p episode: cinematic title card, each scene normalized and captioned with its
voiceover baked in, an end card, optional ducked music bed. The result is sealed
with an embedded Genblaze manifest (Mp4Handler) and pushed to B2, with an
Object-Locked canon copy — the episode is provenance-carrying and immutable.

Everything here is local ffmpeg + PIL; no cloud.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import textwrap
from typing import List, Optional

from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1920, 1080, 16
FONTS = r"C:\Windows\Fonts"
FFMPEG = os.environ.get("FFMPEG", "ffmpeg")
FFPROBE = os.environ.get("FFPROBE", "ffprobe")


def _font(name, size):
    try:
        return ImageFont.truetype(os.path.join(FONTS, name), size)
    except Exception:
        return ImageFont.load_default()


def _run(args):
    p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        raise RuntimeError("ffmpeg failed: " + p.stderr.decode("utf-8", "ignore")[-800:])


def _dur(path) -> float:
    out = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=nk=1:nw=1", path], stdout=subprocess.PIPE).stdout
    try:
        return float(out.strip() or 0)
    except ValueError:
        return 0.0


# ---------- PIL cards / overlays ----------
BG = (7, 9, 14)
INK = (243, 247, 255)
ACC = (95, 214, 255)
DIM = (150, 165, 195)


def _grad_base():
    img = Image.new("RGB", (W, H), BG)
    px = img.load()
    for y in range(H):
        t = y / H
        for x in range(0, W, 4):
            tx = x / W
            r = int(10 + 30 * (1 - t) * (0.4 + 0.6 * tx))
            g = int(14 + 44 * (1 - t) * (0.3 + 0.7 * tx))
            b = int(22 + 70 * (1 - t))
            for dx in range(4):
                if x + dx < W:
                    px[x + dx, y] = (min(r, 255), min(g, 255), min(b, 255))
    return img


def _title_card(kicker, title, sub, tick_l="", tick_r="") -> str:
    img = _grad_base()
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 66], fill=(0, 0, 0))
    d.rectangle([0, H - 66, W, H], fill=(0, 0, 0))
    d.text((132, 150), tick_l, font=_font("consola.ttf", 24), fill=ACC)
    d.text((W - 132, 150), tick_r, font=_font("consola.ttf", 24), fill=DIM, anchor="ra")
    d.text((134, 430), kicker.upper(), font=_font("arialbd.ttf", 30), fill=ACC)
    y = 490
    for ln in textwrap.wrap(title, width=22):
        d.text((132, y), ln, font=_font("arialbd.ttf", 118), fill=INK)
        y += 128
    d.rectangle([136, y + 8, 232, y + 12], fill=ACC)
    d.text((136, y + 40), sub, font=_font("arial.ttf", 40), fill=DIM)
    p = os.path.join(tempfile.gettempdir(), f"card_{abs(hash((title, sub))) % 10**8}.png")
    img.save(p)
    return p


def _caption_overlay(scene_no, location, caption) -> str:
    """Transparent 1080p overlay: top scene tick + lower-third caption."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # top tick
    d.text((132, 92), f"SCENE {scene_no:02d}", font=_font("consola.ttf", 26), fill=(95, 214, 255, 255))
    d.text((132, 128), location.upper(), font=_font("consola.ttf", 22), fill=(200, 214, 240, 210))
    # lower-third gradient
    for i in range(240):
        a = int(150 * (i / 240))
        d.line([(0, H - 240 + i), (W, H - 240 + i)], fill=(4, 6, 11, a))
    d.rectangle([132, H - 150, 140, H - 96], fill=(95, 214, 255, 255))
    d.text((166, H - 156), caption, font=_font("arialbd.ttf", 54), fill=(243, 247, 255, 255))
    p = os.path.join(tempfile.gettempdir(), f"ov_{scene_no}_{abs(hash(caption)) % 10**6}.png")
    img.save(p)
    return p


# ---------- segment builders ----------
def _still_segment(png, dur, out):
    _run([FFMPEG, "-y", "-loop", "1", "-t", f"{dur:.3f}", "-i", png,
          "-f", "lavfi", "-t", f"{dur:.3f}", "-i", "anullsrc=r=48000:cl=stereo",
          "-vf", f"scale={W}:{H},fps={FPS},format=yuv420p", "-r", str(FPS),
          "-c:v", "libx264", "-preset", "medium", "-crf", "18",
          "-c:a", "aac", "-ar", "48000", "-ac", "2", "-shortest", out])


def _scene_segment(clip, vo, overlay_png, out):
    cdur = _dur(clip)
    vdur = _dur(vo) if vo else 0.0
    dur = max(cdur, vdur, 3.0)
    freeze = max(0.0, dur - cdur)
    inputs = ["-i", clip, "-i", overlay_png]
    if vo:
        inputs += ["-i", vo]
    vf = (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=decrease,"
          f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={FPS},"
          f"tpad=stop_mode=clone:stop_duration={freeze:.3f}[bg];"
          f"[bg][1:v]overlay=0:0:format=auto,format=yuv420p[v]")
    if vo:
        af = f"[2:a]apad,atrim=0:{dur:.3f},aformat=sample_rates=48000:channel_layouts=stereo[a]"
        amap = ["-map", "[v]", "-map", "[a]"]
        filt = vf + ";" + af
    else:
        filt = vf + f";anullsrc=r=48000:cl=stereo,atrim=0:{dur:.3f}[a]"
        amap = ["-map", "[v]", "-map", "[a]"]
    _run([FFMPEG, "-y", *inputs, "-filter_complex", filt, *amap,
          "-t", f"{dur:.3f}", "-r", str(FPS),
          "-c:v", "libx264", "-preset", "medium", "-crf", "18",
          "-c:a", "aac", "-ar", "48000", "-ac", "2", out])


def compose_episode(spec, scenes: List[dict], out_path: str,
                    music_path: Optional[str] = None,
                    previously: Optional[str] = None) -> str:
    """spec: EpisodeSpec; scenes: [{clip, vo, scene_no, location, caption}] -> out_path mp4."""
    tmp = tempfile.mkdtemp(prefix="episode_")
    segs = []

    if previously:
        prev_png = _title_card("PREVIOUSLY", "on Encore", previously[:70],
                               tick_l=f"{spec.show} // season memory",
                               tick_r="recalled from Backblaze B2")
        p0 = os.path.join(tmp, "s00_prev.mp4")
        _still_segment(prev_png, 2.6, p0)
        segs.append(p0)

    title_png = _title_card(spec.show, spec.episode_title, spec.logline[:70],
                            tick_l=f"{spec.show} // S01",
                            tick_r="local i2v · sealed on B2")
    t0 = os.path.join(tmp, "s00_title.mp4")
    _still_segment(title_png, 3.2, t0)
    segs.append(t0)

    for i, sc in enumerate(scenes, start=1):
        ov = _caption_overlay(sc["scene_no"], sc["location"], sc["caption"])
        seg = os.path.join(tmp, f"s{i:02d}.mp4")
        _scene_segment(sc["clip"], sc.get("vo"), ov, seg)
        segs.append(seg)

    end_png = _title_card("ENCORE", spec.show, "seasons, not clips — sealed on Backblaze B2",
                          tick_l="a local-first AI studio", tick_r="Genblaze · ComfyUI · B2")
    tE = os.path.join(tmp, "s99_end.mp4")
    _still_segment(end_png, 2.8, tE)
    segs.append(tE)

    listfile = os.path.join(tmp, "concat.txt")
    with open(listfile, "w") as f:
        for s in segs:
            f.write(f"file '{s.replace(os.sep, '/')}'\n")
    raw = os.path.join(tmp, "episode_raw.mp4")
    _run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", listfile,
          "-c:v", "libx264", "-preset", "medium", "-crf", "18",
          "-c:a", "aac", "-ar", "48000", "-ac", "2", raw])

    if music_path and os.path.exists(music_path):
        total = _dur(raw)
        _run([FFMPEG, "-y", "-i", raw, "-stream_loop", "-1", "-i", music_path,
              "-filter_complex",
              f"[1:a]volume=0.14,atrim=0:{total:.3f},afade=t=out:st={max(0,total-2):.3f}:d=2[m];"
              f"[0:a][m]amix=inputs=2:duration=first:dropout_transition=0[a]",
              "-map", "0:v", "-map", "[a]", "-c:v", "copy",
              "-c:a", "aac", "-ar", "48000", "-ac", "2", out_path])
    else:
        shutil.move(raw, out_path)  # cross-drive safe (temp is on C:, out on B:)
    return out_path


def store_episode_to_b2(spec, mp4_path: str) -> dict:
    """Plain store: push the finished episode to the B2 library so it shows up in the gallery.
    No provenance manifest, no Object Lock — just the durable episode file."""
    import hashlib
    from comfyui_provider import _b2
    with open(mp4_path, "rb") as f:
        raw = f.read()
    sha = hashlib.sha256(raw).hexdigest()
    import re
    slug = re.sub(r"[^a-z0-9]+", "-", spec.episode_title.lower()).strip("-")[:40] or "episode"
    key = f"episodes/{spec.show}/{slug}-{sha[:8]}.mp4"
    _b2().put(key, raw)
    return {"b2_key": key, "url": f"/media/{key}", "sha256": sha, "size": len(raw)}


def seal_episode_to_b2(spec, mp4_path: str, scene_infos=None) -> dict:
    """Embed a Genblaze manifest into the finished episode, verify the roundtrip, and push to
    B2 with an Object-Locked canon + immutable manifest sidecar. The manifest carries the
    provenance of every scene clip (sha256 lineage) so the episode is self-describing."""
    import datetime
    import hashlib
    from pathlib import Path
    from genblaze_core import Manifest, ObjectLockConfig
    from genblaze_core.media import Mp4Handler
    from genblaze_core.models.run import Run
    import pipeline
    from comfyui_provider import _b2

    with open(mp4_path, "rb") as f:
        raw = f.read()
    sha = hashlib.sha256(raw).hexdigest()
    run = Run(
        run_id=f"episode-{spec.show}-{sha[:8]}", name=spec.episode_title, status="completed",
        metadata={"show": spec.show, "character": spec.character,
                  "episode_title": spec.episode_title, "logline": spec.logline,
                  "kind": "composed-episode", "scenes": len(spec.scenes), "source_sha256": sha,
                  "scene_assets": [{"sha256": s.get("sha256"), "b2_key": s.get("b2_key"),
                                    "dims": s.get("dims")} for s in (scene_infos or [])]},
    )
    manifest = Manifest(run=run)

    sealed_path = mp4_path.replace(".mp4", ".sealed.mp4")
    embedded, seal_err = True, None
    try:
        Mp4Handler().embed(Path(mp4_path), manifest, Path(sealed_path))
    except Exception as e:  # noqa: BLE001
        sealed_path, embedded, seal_err = mp4_path, False, repr(e)
    verified = None
    if embedded:
        try:
            verified = bool(Mp4Handler().verify(Path(sealed_path)))
        except Exception:  # noqa: BLE001
            verified = None

    with open(sealed_path, "rb") as f:
        sealed = f.read()
    sealed_sha = hashlib.sha256(sealed).hexdigest()
    slug = spec.episode_title.lower().replace(" ", "-").replace("/", "-")[:40] or "episode"
    key = f"episodes/{spec.show}/{slug}-{sealed_sha[:8]}.mp4"
    _b2().put(key, sealed)

    until = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365)
    lock = ObjectLockConfig(retain_until=until, mode="GOVERNANCE")
    canon_key = f"episodes/{spec.show}/canon/{slug}-{sealed_sha[:8]}.mp4"
    pipeline._sealed_b2().put(canon_key, sealed, object_lock=lock)
    manifest_key = f"episodes/{spec.show}/canon/{slug}-{sealed_sha[:8]}.manifest.json"
    try:
        pipeline._sealed_b2().put(manifest_key, manifest.to_canonical_json().encode(), object_lock=lock)
    except Exception:  # noqa: BLE001
        manifest_key = None

    return {"b2_key": key, "canon_key": canon_key, "manifest_key": manifest_key,
            "sha256": sealed_sha, "url": _b2().get_durable_url(key), "size": len(sealed),
            "embedded": embedded, "verified": verified, "seal_error": seal_err}

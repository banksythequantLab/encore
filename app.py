"""
Filmwriter x Genblaze generation service (FastAPI).

Thin HTTP layer Filmwriter's Node conductor calls instead of DashScope.
Runs GPU-free (GMICloud + B2 are both cloud) — deploy next to Filmwriter on ECS.

Run:
  python -m venv .venv && . .venv/bin/activate   # (Windows: .venv\\Scripts\\activate)
  pip install -r requirements.txt
  cp .env.example .env   # fill in B2_* and GMI_API_KEY
  uvicorn app:app --host 127.0.0.1 --port 8090
"""
import os

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, File, UploadFile  # noqa: E402
from fastapi.responses import HTMLResponse  # noqa: E402
from pydantic import BaseModel  # noqa: E402

import judges  # noqa: E402
import pipeline  # noqa: E402

app = FastAPI(title="Encore — an AI studio on Backblaze B2", version="0.3.0")

from fastapi import HTTPException  # noqa: E402


def _guard_gen():
    """On the public demo, don't let strangers trigger GPU generation on the host box."""
    if os.environ.get("PUBLIC_DEMO"):
        raise HTTPException(status_code=403,
                            detail="Generation is disabled on the public demo — run Encore locally to generate.")


@app.get("/", response_class=HTMLResponse)
def index():
    from pathlib import Path
    return (Path(__file__).parent / "studio.html").read_text(encoding="utf-8")


@app.get("/verify-page", response_class=HTMLResponse)
def verify_page():
    from pathlib import Path
    return (Path(__file__).parent / "verify.html").read_text(encoding="utf-8")


class StillReq(BaseModel):
    prompt: str
    aspect_ratio: str = "16:9"
    run_name: str = "shot"
    max_iter: int = 3


class VideoReq(BaseModel):
    prompt: str
    image_url: str | None = None
    duration: int = 5
    aspect_ratio: str = "16:9"
    run_name: str = "shot"


class VoiceReq(BaseModel):
    text: str
    voice: str | None = None
    run_name: str = "shot"


@app.get("/health")
def health():
    return {
        "ok": True,
        "bucket": os.environ.get("B2_BUCKET"),
        "judge": os.environ.get("JUDGE_STRATEGY", "gmicloud"),
        "image_model": pipeline.IMAGE_MODEL,
        "video_i2v": pipeline.VIDEO_I2V_MODEL,
        "voice_model": pipeline.VOICE_MODEL,
    }


@app.post("/gen/still")
def gen_still(req: StillReq):
    _guard_gen()
    judge = judges.make_judge(req.prompt)
    return pipeline.gen_still(
        req.prompt, judge,
        aspect_ratio=req.aspect_ratio, run_name=req.run_name, max_iter=req.max_iter,
    )


@app.post("/gen/video")
def gen_video(req: VideoReq):
    _guard_gen()
    return pipeline.gen_video(
        prompt=req.prompt, image_b2_key=req.image_url,
        duration=req.duration, aspect_ratio=req.aspect_ratio, run_name=req.run_name,
    )


@app.post("/gen/voice")
def gen_voice(req: VoiceReq):
    _guard_gen()
    return pipeline.gen_voice(text=req.text, voice=req.voice, run_name=req.run_name)


@app.get("/provenance/{run_id}")
def provenance(run_id: str):
    return pipeline.read_provenance(run_id)


def _prov_fields(doc: dict) -> dict:
    """Best-effort pull of display fields from a canonical manifest dict."""
    out = {"provider": None, "model": None, "prompt": None, "created": None, "run_id": None}

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                lk = k.lower()
                if isinstance(v, str):
                    if lk == "provider" and not out["provider"]:
                        out["provider"] = v
                    elif lk == "model" and not out["model"]:
                        out["model"] = v
                    elif lk == "prompt" and not out["prompt"]:
                        out["prompt"] = v
                    elif lk in ("created_at", "created", "timestamp", "started_at") and not out["created"]:
                        out["created"] = v
                    elif lk in ("run_id", "runid") and not out["run_id"]:
                        out["run_id"] = v
                walk(v)
        elif isinstance(o, list):
            for x in o:
                walk(x)

    walk(doc)
    return out


@app.post("/verify")
async def verify_file(file: UploadFile = File(...)):
    """The hero surface: a user drops a media file; we report whether it carries
    a valid, untampered provenance seal, and surface who/what generated it."""
    import json
    import mimetypes
    import os
    import tempfile
    from pathlib import Path

    from genblaze_core.media import get_handler

    data = await file.read()
    name = file.filename or "upload"
    ext = os.path.splitext(name)[1]
    tmp = Path(tempfile.gettempdir()) / f"verify_{os.urandom(6).hex()}{ext}"
    tmp.write_bytes(data)
    result = {"filename": name, "size": len(data), "sealed": False,
              "verified": False, "provenance": None}
    try:
        mime = mimetypes.guess_type(name)[0] or "application/octet-stream"
        try:
            handler = get_handler(mime)
        except Exception:
            handler = None
        if handler is not None:
            m = None
            try:
                m = handler.extract(tmp)
            except Exception:
                m = None
            result["sealed"] = m is not None
            try:
                result["verified"] = bool(handler.verify(tmp))
            except Exception:
                result["verified"] = False
            if m is not None:
                try:
                    prov = _prov_fields(json.loads(m.to_canonical_json()))
                    prov["canonical_hash"] = getattr(m, "canonical_hash", None)
                    result["provenance"] = prov
                except Exception:
                    pass
    finally:
        try:
            tmp.unlink()
        except Exception:
            pass
    return result


# ---------------------------------------------------------------------------
# Studio surface: the B2 Series Vault + episode library, served straight from B2
# ---------------------------------------------------------------------------
from fastapi import Request  # noqa: E402
from fastapi.responses import Response  # noqa: E402

_MEDIA_MIME = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp",
               "mp4": "video/mp4", "webm": "video/webm", "wav": "audio/wav", "mp3": "audio/mpeg",
               "json": "application/json"}
_ALLOW_PREFIX = ("vault/", "episodes/", "comfyui/assets/", "posters/")


def _b2b():
    from comfyui_provider import _b2
    return _b2()


def _b2_list(prefix: str):
    b = _b2b()
    keys, tok = [], None
    while True:
        page = b.list(prefix, continuation_token=tok)
        for e in page.entries:
            k = getattr(e, "key", None) or getattr(e, "name", None) or (e.get("key") if isinstance(e, dict) else None)
            if k:
                keys.append(k)
        tok = getattr(page, "next_token", None)
        if not tok:
            break
    return keys


@app.get("/api/vault")
def api_vault():
    """Every show's cast identity anchors, read from the B2 Series Vault (season.json)."""
    import json
    out = []
    for sk in [k for k in _b2_list("vault/") if k.endswith("season.json")]:
        show = sk.split("/")[1]
        try:
            doc = json.loads(_b2b().get(sk).decode())
        except Exception:
            continue
        cast = [{"name": c.get("name"), "anchor_url": f"/media/{c.get('anchor_key')}",
                 "sha256": c.get("sha256"), "appearance": c.get("appearance", ""),
                 "locked": c.get("locked", [])}
                for c in doc.get("cast", []) if c.get("anchor_key")]
        out.append({"show": show, "style": doc.get("style", ""),
                    "updated": doc.get("updated", ""), "cast": cast})
    return {"shows": out}


@app.get("/api/episodes")
def api_episodes():
    """Sealed episodes in the B2 library (skips the Object-Locked canon copies)."""
    eps = []
    posters = set(_b2_list("posters/"))
    for k in _b2_list("episodes/"):
        if not k.endswith(".mp4") or "/canon/" in k:
            continue
        parts = k.split("/")
        show = parts[1] if len(parts) > 1 else "?"
        stem = parts[-1].rsplit(".", 1)[0]
        title = stem.rsplit("-", 1)[0].replace("-", " ").title()
        sha = stem.rsplit("-", 1)[-1] if "-" in stem else ""
        pk = f"posters/{show}/{stem}.png"
        eps.append({"show": show, "key": k, "url": f"/media/{k}", "title": title, "sha": sha,
                    "poster_url": f"/media/{pk}" if pk in posters else None})
    return {"episodes": eps}


_COMMUNITY_KEY = "community/shots.json"


def _community_add(entry: dict):
    """Append a visitor-made shot to the public strip (keeps the newest 48)."""
    import json
    b = _b2b()
    try:
        doc = json.loads(b.get(_COMMUNITY_KEY).decode())
    except Exception:
        doc = {"shots": []}
    doc["shots"] = ([entry] + doc.get("shots", []))[:48]
    b.put(_COMMUNITY_KEY, json.dumps(doc).encode())


@app.get("/api/community")
def api_community():
    """Shots visitors made through the public maker."""
    import json
    try:
        return json.loads(_b2b().get(_COMMUNITY_KEY).decode())
    except Exception:
        return {"shots": []}


def _canon_s3():
    import boto3
    region = os.environ.get("B2_REGION", "us-east-005")
    return boto3.client("s3", endpoint_url=f"https://s3.{region}.backblazeb2.com",
                        aws_access_key_id=os.environ["B2_KEY_ID"],
                        aws_secret_access_key=os.environ["B2_APP_KEY"], region_name=region)


_SEALED_BUCKET = os.environ.get("B2_SEALED_BUCKET", "filmwriter-sealed")


@app.get("/api/canon/status")
def canon_status(show: str = "warlords-sniper"):
    from botocore.exceptions import ClientError
    key = f"vault/{show}/season.canon.json"
    s3 = _canon_s3()
    try:
        vs = s3.list_object_versions(Bucket=_SEALED_BUCKET, Prefix=key).get("Versions", [])
        v = next((x for x in vs if x["IsLatest"]), None)
        if not v:
            return {"locked": False, "error": "no canon copy found"}
        ret = s3.get_object_retention(Bucket=_SEALED_BUCKET, Key=key,
                                      VersionId=v["VersionId"])["Retention"]
        return {"locked": True, "key": key, "version": v["VersionId"],
                "mode": ret["Mode"], "retain_until": str(ret["RetainUntilDate"])[:19]}
    except ClientError as e:
        return {"locked": False, "error": e.response["Error"].get("Code", "unknown")}


@app.post("/api/canon/attack")
def canon_attack(show: str = "warlords-sniper"):
    """The stunt: really try to delete the Object-Locked canon (no bypass). B2 refuses."""
    from botocore.exceptions import ClientError
    key = f"vault/{show}/season.canon.json"
    s3 = _canon_s3()
    vs = s3.list_object_versions(Bucket=_SEALED_BUCKET, Prefix=key).get("Versions", [])
    v = next((x for x in vs if x["IsLatest"]), None)
    if not v:
        raise HTTPException(status_code=404, detail="no canon copy to attack")
    # Safety: only attempt the delete if retention is verifiably in force.
    try:
        ret = s3.get_object_retention(Bucket=_SEALED_BUCKET, Key=key,
                                      VersionId=v["VersionId"])["Retention"]
    except ClientError:
        raise HTTPException(status_code=409, detail="canon retention not verifiable; not attacking")
    try:
        s3.delete_object(Bucket=_SEALED_BUCKET, Key=key, VersionId=v["VersionId"])
        return {"deleted": True, "warning": "LOCK NOT ENFORCED — investigate immediately"}
    except ClientError as e:
        err = e.response["Error"]
        return {"deleted": False, "refused": True,
                "code": err.get("Code"), "message": err.get("Message", "")[:200],
                "version": v["VersionId"], "mode": ret["Mode"],
                "retain_until": str(ret["RetainUntilDate"])[:19]}


@app.get("/api/metrics")
def api_metrics():
    """Network vitals for the credibility strip."""
    import json
    eps = [k for k in _b2_list("episodes/") if k.endswith(".mp4") and "/canon/" not in k]
    posters = [k for k in _b2_list("posters/") if k.endswith(".png")]
    try:
        shots = len(json.loads(_b2b().get(_COMMUNITY_KEY).decode()).get("shots", []))
    except Exception:
        shots = 0
    return {"episodes_aired": len(eps), "posters": len(posters), "visitor_shots": shots,
            "uptime_s": round(time.time() - _APP_STARTED),
            "cloud_cost_estimate_usd": round(len(eps) * 6.0, 2),
            "local_cost_usd": round(len(eps) * 0.12, 2)}


@app.get("/media/{key:path}")
def media(key: str, request: Request):
    """Range-aware proxy so the browser can stream objects from the (private) B2 bucket."""
    if not key.startswith(_ALLOW_PREFIX):
        return Response(status_code=403)
    try:
        data = _b2b().get(key)
    except Exception:
        return Response(status_code=404)
    mime = _MEDIA_MIME.get(key.rsplit(".", 1)[-1].lower(), "application/octet-stream")
    rng = request.headers.get("range")
    if rng and rng.startswith("bytes="):
        try:
            s, e = rng[6:].split("-")
            start = int(s) if s else 0
            end = int(e) if e else len(data) - 1
            end = min(end, len(data) - 1)
            chunk = data[start:end + 1]
            return Response(chunk, status_code=206, media_type=mime,
                            headers={"Content-Range": f"bytes {start}-{end}/{len(data)}",
                                     "Accept-Ranges": "bytes", "Content-Length": str(len(chunk))})
        except Exception:
            pass
    return Response(data, media_type=mime,
                    headers={"Accept-Ranges": "bytes", "Content-Length": str(len(data))})


# ---------------------------------------------------------------------------
# The maker: bring a cast member from the vault into a NEW scene, then animate it.
# Runs as a background job so the UI can stream progress. Local-only (guarded).
# ---------------------------------------------------------------------------
import queue as _qmod  # noqa: E402
import threading  # noqa: E402
import time  # noqa: E402
import uuid as _uuid  # noqa: E402

_JOBS: dict = {}
_QUEUE: "_qmod.Queue" = _qmod.Queue()


def _gpu_worker():
    """Single worker: generation jobs run strictly one at a time (no VRAM contention)."""
    while True:
        jid, fn, args = _QUEUE.get()
        job = _JOBS.get(jid)
        if job is None:
            _QUEUE.task_done()
            continue
        job["status"] = "running"
        try:
            fn(jid, *args)
        except Exception as e:  # noqa: BLE001
            job["status"] = "error"
            job["error"] = str(e)
            job["log"].append("Error: " + str(e))
        finally:
            _QUEUE.task_done()


threading.Thread(target=_gpu_worker, daemon=True).start()


def _enqueue(jid: str, fn, args: tuple):
    pos = _QUEUE.qsize() + 1
    _JOBS[jid]["log"].append(f"Queued (position {pos})…" if pos > 1 else "Queued…")
    _QUEUE.put((jid, fn, args))


class ShotReq(BaseModel):
    show: str
    character: str
    scene: str
    animate: bool = True


def _free_comfy():
    try:
        import httpx
        httpx.post("http://127.0.0.1:8188/free", json={"unload_models": True, "free_memory": True}, timeout=15)
    except Exception:
        pass


def _run_shot(jid: str, show: str, character: str, scene: str, animate: bool):
    job = _JOBS[jid]

    def log(m):
        job["log"].append(m)
        job["stage"] = m

    try:
        import os
        import tempfile
        import vault
        import pipeline
        from comfyui_provider import ComfyUIProvider, _b2
        from genblaze_core import Modality, Pipeline

        log(f"Pulling {character} from the Backblaze B2 vault…")
        anchor = vault.anchor_tempfile(show, character)
        try:
            _free_comfy()
            log(f"Placing {character} in a new scene (qwen-image-edit)…")
            res = (Pipeline("make")
                   .step(ComfyUIProvider(image_ref=anchor), model="qwen-image-edit",
                         prompt=f"Keep this exact character identical (same face, same wardrobe). New scene: {scene}",
                         modality=Modality.IMAGE)
                   .run(timeout=600, raise_on_failure=False))
            run, _m = pipeline._unpack(res)
            step = run.steps[-1]
            if not step.assets:
                raise RuntimeError(getattr(step, "error", None) or "keyframe generation produced no image")
            a = step.assets[0]
            kf_key = (a.metadata or {}).get("b2_key")
            job["result"] = {"keyframe_url": f"/media/{kf_key}", "character": character, "scene": scene}
            log("Keyframe ready — same identity, new scene.")

            clip_key = None
            if animate:
                kf = tempfile.mktemp(suffix=".png")
                with open(kf, "wb") as f:
                    f.write(_b2().get(kf_key))
                _free_comfy()
                log("Animating with Wan 2.2 image-to-video… (~2 min)")
                res2 = (Pipeline("make")
                        .step(ComfyUIProvider(image_ref=kf), model="wan22-i2v",
                              prompt=f"{scene}, subtle cinematic motion", modality=Modality.VIDEO)
                        .run(timeout=1200, raise_on_failure=False))
                run2, _m2 = pipeline._unpack(res2)
                s2 = run2.steps[-1]
                if s2.assets:
                    a2 = s2.assets[0]
                    clip_key = (a2.metadata or {}).get("b2_key")
                    job["result"]["clip_url"] = f"/media/{clip_key}"
                    log("Clip ready.")
                else:
                    log("Keyframe done; animation step skipped (" + str(getattr(s2, "error", "")) + ")")
            try:
                _community_add({"character": character, "show": show, "scene": scene[:140],
                                "keyframe_key": kf_key, "clip_key": clip_key,
                                "ts": time.time()})
            except Exception:
                pass
            job["status"] = "done"
        finally:
            try:
                os.remove(anchor)
            except OSError:
                pass
    except Exception as e:  # noqa: BLE001
        job["status"] = "error"
        job["error"] = str(e)
        job["log"].append("Error: " + str(e))


_RATE: dict = {}  # ip -> list[timestamps]


def _rate_check(request: Request, kind: str):
    """Per-IP caps: shots 4/hour, episodes 1/6 hours. Local box is uncapped."""
    ip = request.headers.get("cf-connecting-ip") or (request.client.host if request.client else "?")
    if ip in ("127.0.0.1", "::1"):
        return
    window, limit = ((3600, 4) if kind == "shot" else (21600, 1))
    now = time.time()
    hist = [t for t in _RATE.get((ip, kind), []) if now - t < window]
    if len(hist) >= limit:
        raise HTTPException(status_code=429, detail=(
            "The one GPU is popular today — you've hit the per-visitor limit for "
            f"{kind}s ({limit} per {window // 3600}h). Come back soon, or clone the repo "
            "and run Encore on your own card."))
    hist.append(now)
    _RATE[(ip, kind)] = hist


@app.post("/make/shot")
def make_shot(req: ShotReq, request: Request):
    # Public generation is OPEN (judging window). Set PUBLIC_DEMO_FORCE=1 to re-lock
    # generation to the local box only.
    if os.environ.get("PUBLIC_DEMO_FORCE"):
        raise HTTPException(status_code=403, detail="Generation runs on the local studio box only.")
    _rate_check(request, "shot")
    jid = _uuid.uuid4().hex[:12]
    _JOBS[jid] = {"status": "queued", "stage": "queued", "log": [], "result": None,
                  "error": None, "created": time.time()}
    _enqueue(jid, _run_shot, (req.show, req.character, req.scene, req.animate))
    return {"job_id": jid}


@app.get("/make/jobs/{jid}")
def make_job(jid: str):
    return _JOBS.get(jid, {"status": "unknown"})


_APP_STARTED = time.time()


@app.get("/api/studio")
def studio_state():
    """Live studio floor: what the GPU is doing, the queue, and identity scores."""
    import re
    jobs = []
    for jid, j in sorted(_JOBS.items(), key=lambda kv: kv[1].get("created", 0),
                         reverse=True)[:12]:
        scores = [float(m) for line in j.get("log", [])
                  for m in re.findall(r"score=([0-9.]+)", str(line))]
        jobs.append({"id": jid, "kind": j.get("kind", "shot"),
                     "status": j.get("status"), "stage": j.get("stage"),
                     "created": j.get("created"),
                     "score": max(scores) if scores else None})
    busy = any(x["status"] == "running" for x in jobs)
    on_air = next((x for x in jobs if x["status"] == "running" and x["kind"] == "episode"), None)
    return {"queue_depth": _QUEUE.qsize(), "gpu": "busy" if busy else "idle",
            "jobs": jobs, "on_air": on_air,
            "next_air": _next_air_ts(), "started": _APP_STARTED}


class EpisodeReq(BaseModel):
    show: str
    character: str
    premise: str
    n_scenes: int = 2


# ---------------------------------------------------------------------------
# The network airs itself: one new episode per night, premise written by the
# planner from the season memory on B2. ON AIR state + countdown feed the hero.
# ---------------------------------------------------------------------------
import datetime as _dt  # noqa: E402

AIR_SHOW = os.environ.get("AIR_SHOW", "warlords-sniper")
AIR_CHARACTER = os.environ.get("AIR_CHARACTER", "Lena")
AIR_HOUR = int(os.environ.get("AIR_HOUR", "21"))  # local time, minute 0


def _next_air_ts() -> float:
    now = _dt.datetime.now()
    target = now.replace(hour=AIR_HOUR, minute=0, second=0, microsecond=0)
    if target <= now:
        target += _dt.timedelta(days=1)
    return target.timestamp()


def _air_once() -> str:
    """Queue tonight's episode: next-chapter premise from the B2 season memory."""
    import season
    premise = season.next_premise(AIR_SHOW, AIR_CHARACTER)
    jid = _uuid.uuid4().hex[:12]
    _JOBS[jid] = {"status": "queued", "stage": "queued", "log": [f"Nightly premiere — premise: {premise}"],
                  "result": None, "error": None, "created": time.time(),
                  "kind": "episode", "nightly": True}
    _enqueue(jid, _run_episode, (AIR_SHOW, AIR_CHARACTER, premise, 2))
    return jid


def _air_scheduler():
    while True:
        wait = max(5.0, _next_air_ts() - time.time())
        time.sleep(wait)
        try:
            _air_once()
        except Exception:
            pass
        time.sleep(120)  # never double-fire within the same minute


if os.environ.get("AIR_ENABLED", "1") == "1":
    threading.Thread(target=_air_scheduler, daemon=True).start()


@app.post("/air/now")
def air_now(request: Request):
    """Manual premiere trigger — local box only."""
    if request.client.host not in ("127.0.0.1", "::1"):
        raise HTTPException(status_code=403, detail="local only")
    return {"job_id": _air_once()}


def _run_episode(jid: str, show: str, character: str, premise: str, n_scenes: int):
    job = _JOBS[jid]
    music_path = None
    try:
        import produce_episode

        def _prog(m):
            job["log"].append(m)
            job["stage"] = str(m)[:100]
        produce_episode.set_progress(_prog)
        # Score first: an instrumental bed from ACE-Step, on the same GPU.
        try:
            import music
            job["log"].append("Scoring the episode (ACE-Step, same GPU)…")
            job["stage"] = "music"
            _free_comfy()
            music_path = music.generate_music_bed()
            job["log"].append("Score ready — ducked under the narration.")
        except Exception as me:  # noqa: BLE001 — no bed must not kill the episode
            job["log"].append(f"Music bed skipped ({me})")
            music_path = None
        summary = produce_episode.produce_episode(show, character, premise,
                                                  n_scenes=n_scenes, max_iter=2,
                                                  music_path=music_path)
        ep = summary.get("episode", {})
        job["result"] = {"episode_url": ep.get("url"), "title": summary.get("episode_title"),
                         "duration_s": summary.get("duration_s"), "scenes": summary.get("scenes")}
        # Key art: generated on the same GPU, stored under posters/ on B2.
        try:
            ep_url = ep.get("url") or ""
            if "/episodes/" in ep_url and ep_url.endswith(".mp4"):
                import posters
                stem = ep_url.rsplit("/", 1)[-1][:-4]
                job["log"].append("Designing the episode poster (z-image-turbo)…")
                job["stage"] = "poster"
                _free_comfy()
                pk = posters.generate_poster(show, summary.get("episode_title") or stem,
                                             stem, premise)
                job["result"]["poster_url"] = f"/media/{pk}"
                job["log"].append("Poster on B2.")
        except Exception as pe:  # noqa: BLE001 — poster failure must not fail the episode
            job["log"].append(f"Poster skipped ({pe})")
        job["status"] = "done"
    except Exception as e:  # noqa: BLE001
        job["status"] = "error"
        job["error"] = str(e)
        job["log"].append("Error: " + str(e))
    finally:
        try:
            import produce_episode
            produce_episode.set_progress(None)
        except Exception:
            pass
        if music_path:
            try:
                os.remove(music_path)
            except OSError:
                pass


@app.post("/make/episode")
def make_episode(req: EpisodeReq, request: Request):
    # Public generation is OPEN (judging window). PUBLIC_DEMO_FORCE=1 re-locks.
    if os.environ.get("PUBLIC_DEMO_FORCE"):
        raise HTTPException(status_code=403, detail="Generation runs on the local studio box only.")
    _rate_check(request, "episode")
    n = max(1, min(4, req.n_scenes))
    jid = _uuid.uuid4().hex[:12]
    _JOBS[jid] = {"status": "queued", "stage": "queued", "log": [], "result": None,
                  "error": None, "created": time.time(), "kind": "episode"}
    _enqueue(jid, _run_episode, (req.show, req.character, req.premise, n))
    return {"job_id": jid}

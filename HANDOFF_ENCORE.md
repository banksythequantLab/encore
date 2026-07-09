# Encore — Continuation / Handoff Prompt (paste into a fresh session)

You are picking up **Encore**, Derek "Banksy AI" Soltis's entry for the **Backblaze Generative Media
Hackathon** (Devpost; deadline **Aug 3 2026, 5pm ET**). Read this whole doc, run the health check at the
bottom, then continue. Follow Derek's startup profile (MCP-first, verify every action, no fake results,
secrets only in `.env`, never write to `C:\`, ask before persistence scripts or destructive changes,
use Context7 before writing code — his repos contain post-2025-09 code you won't know).

---

## What Encore is (the pitch — do NOT drift from this)
**"Seasons, not clips."** A **local-first AI studio** that makes **episodic** content with a **returning,
identity-consistent cast**, produced entirely on Derek's own GPUs ($0 cloud generation), with
**Backblaze B2 as the studio's durable memory / asset library**.

**IMPORTANT — provenance/verify is DEAD.** Derek explicitly killed the "verify an AI video" + provenance +
Object-Lock/immutability angle ("it is dumb"). Do **not** re-introduce it. B2 is meaningful here as the
**production library** (cast vault + episode library streamed to the app), not a verifier. The pivot was to
an **active, usable video maker**.

---

## Current state — ALL BUILT & PROVEN on real runs (no mocks)
- **Custom ComfyUI→Genblaze provider** (local, free) — `comfyui_provider.py`. Uploads outputs to B2 directly.
- **B2 Series Vault** (cast identity anchors, content-addressable) — `vault.py`, surfaced at `/api/vault`.
- **Identity-anchored generation + self-correction** — `episode.py` (qwen-image-edit conditioned on the
  vault anchor) with a **local Qwen3-VL judge** (`judges.py`, `JUDGE_STRATEGY=ollama`, scores 0.95 same /
  0.10 different). `episode.py._free_comfy()` frees ComfyUI VRAM before each judge call (VRAM contention fix).
- **Wan 2.2 image-to-video** — via `B:\MaiVid\workflows\wan22-i2v-fixed.json` (the ORIGINAL `wan22-i2v.json`
  was schema-drifted; use the fixed copy — provider alias already points there).
- **EpisodeSpec planner** (local Ollama `qwen3:8b`) — `planner.py`.
- **Stage C composer** (ffmpeg: title + captioned scenes + end card, cloned-voice VO, ambient bed) —
  `composer.py`. Use `store_episode_to_b2()` (plain B2 store). `seal_episode_to_b2()` still exists but is
  UNUSED (provenance — leave it, don't call it).
- **Orchestrator** `produce_episode.py` — plan → per-scene anchored keyframe + Wan i2v + cloned-voice
  narration → compose → store on B2. Has `set_progress(cb)` hook for streaming to the UI.
- **Studio web app** — `app.py` (FastAPI) serving `studio.html` (single-page app). Sections: hero,
  **Maker** (Single-shot + Full-episode, live progress), **The Series Vault**, **Episodes** gallery.
  Endpoints: `/`, `/api/vault`, `/api/episodes`, `/media/{key}` (range-aware B2 proxy),
  `/make/shot`, `/make/episode`, `/make/jobs/{id}`. Legacy `/gen/*` + `/verify` still exist but the UI no
  longer uses them.
- **Public deploy**: **https://encore.tlz.us** via a **named Cloudflare tunnel** `encore`
  (id `f428440d-9e33-4624-82ed-6b2be5317d24`), config `B:\Filmwriter-Local\genblaze-service\config-encore.yml`.
  Generation is **local-only**: `/make/*` returns 403 to any request carrying Cloudflare `CF-*` headers, so
  the public can browse the vault + episodes but cannot touch the GPU.
- **Hero demo video**: `B:\Filmwriter-Local\video\encore_hero.mp4` (~98s, 1080p) — cinematic cards
  (Bebas Neue, grain, letterbox), **real Wan i2v footage** of the cast, Derek's **cloned voice** VO,
  prominent **Backblaze B2** branding, kinetic type. Built by `B:\Filmwriter-Local\video\make_hero.py`.
  (VO5/provenance beat already removed.)
- **The maker works end-to-end via the UI** (proven): a full 2-scene episode "Rain's Edge" was produced
  through `/make/episode` in ~7 min (plan → 2 self-correcting keyframes @0.95 → 2 Wan clips → 2 narrations →
  compose → B2) and auto-appeared in the Episodes gallery.

---

## Environment / infra
- **OS:** Windows. **Do not write to `C:\`.**
- **Backend + app:** `B:\Filmwriter-Local\genblaze-service\`  (venv: `.venv\Scripts\python.exe`)
- **Video build:** `B:\Filmwriter-Local\video\`
- **ComfyUI workflows:** `B:\MaiVid\workflows\`  (use `wan22-i2v-fixed.json`, `qwen-image-edit.json`, `z-image-turbo.json`)
- **`.env`** (in genblaze-service): `B2_*` keys, `B2_BUCKET=Filmwriter`, `B2_REGION`,
  `JUDGE_STRATEGY=ollama`, `OLLAMA_VISION_MODEL=qwen3-vl:8b-instruct`. Secrets ONLY here — never echo/commit.
- **Local services required for generation (all currently UP):**
  - ComfyUI @ `127.0.0.1:8188`
  - Ollama @ `127.0.0.1:11434` (models: `qwen3:8b` planner, `qwen3-vl:8b-instruct` judge)
  - FreeClone / VoxCPM voice @ `127.0.0.1:8300` (POST `/api/clone`; ref voice `B:\freeclone-backend\derek-voice.wav`)
- **App:** `uvicorn app:app --port 8090` (started with env var `PUBLIC_DEMO=1`)
- **Backblaze B2 bucket:** `Filmwriter` (us-east-005). Cast anchors under `vault/<show>/…`, episodes under
  `episodes/<show>/…`, provider assets under `comfyui/assets/…`.
- Two shows in the vault: `hero-ai` (A.I./Eva, Dr. Sarah Chen, Mayor Jameson) and `warlords-sniper`
  (Lena, Prince Arin).

## Restart everything (if the box rebooted / something is down)
```powershell
# 1) make sure ComfyUI (8188), Ollama (11434), FreeClone (8300) are running first
# 2) app:
$gs='B:\Filmwriter-Local\genblaze-service'
Get-Content "$gs\.env" | ? {$_ -match '^\s*[^#].+='} | % { $kv=$_ -split '=',2; [Environment]::SetEnvironmentVariable($kv[0].Trim(),$kv[1].Trim(),'Process') }
[Environment]::SetEnvironmentVariable('PUBLIC_DEMO','1','Process')
Start-Process "$gs\.venv\Scripts\python.exe" '-m','uvicorn','app:app','--port','8090' -WorkingDirectory $gs -WindowStyle Hidden
# 3) tunnel (public URL encore.tlz.us):
Start-Process cloudflared 'tunnel','--config',"$gs\config-encore.yml",'run' -WindowStyle Hidden
```

---

## What's LEFT to do (priority order)
1. **Devpost submission package** (`task 9`). `genblaze-service\DEVPOST_SUBMISSION.md` EXISTS but is STALE —
   it still pitches provenance/Object-Lock/verify. **Rewrite it** to the current story: local studio, returning
   cast, **interactive maker (shots + full episodes)**, **B2 as the library**. Include: problem, what it does,
   how it uses Genblaze (custom ComfyUI provider is the feedback-prize contribution), how it uses B2 (vault +
   episode library + media delivery), architecture, "what's real today," setup. Attach `encore_hero.mp4` and
   screenshots of `encore.tlz.us`.
2. **Persistence for the judging window** — the app (`uvicorn :8090`) + `cloudflared` run as loose processes;
   a reboot drops `encore.tlz.us`. Offer to make both **boot-persistent** (Windows service via nssm, or a
   Task Scheduler at-logon task). **ASK before creating any persistence script** (Derek's rule).
3. **Final end-to-end verification pass** (`task 10`): fresh episode via the UI, confirm it lands in the
   gallery and streams from B2; confirm public URL is read-only + generation 403s.
4. Optional polish: full-episode UI has no music bed yet; scene count 2–4; ~4–6 min/scene. Consider a
   "generating…" placeholder card in the Episodes grid while a build runs.

---

## Gotchas / lessons (so you don't rediscover them)
- **Wan i2v**: use `wan22-i2v-fixed.json` only. The original lacked `crop` on CLIPVisionEncode and
  `width/height/length/batch_size`+`start_image` on WanImageToVideo, and the samplers weren't wired to it.
- **Genblaze `.step(params=…)`** filters unknown keys; the ComfyUI provider takes the input image via its
  constructor `ComfyUIProvider(image_ref=…)`, not via params.
- **Windows `file://` sink bug** in Genblaze storage → the provider uploads bytes to B2 itself.
- **Cross-drive file moves**: use `shutil.move`, not `os.replace` (temp is on `C:`, outputs on `B:`).
- **JUDGE_STRATEGY must be `ollama`** (it defaults to a dead GMICloud path otherwise → judge returns 0.5).
- **VRAM**: free ComfyUI (`POST /free {unload_models,free_memory}`) before loading the Ollama vision judge,
  and before heavy Wan renders. `episode.py` and `produce_episode.py` already do this.
- **Cloudflare**: account-less *quick* tunnels (`trycloudflare.com`) 404'd from this network. Use the
  **named** tunnel with an **explicit local config** (`config-encore.yml`) — otherwise cloudflared inherits a
  dashboard-managed config that doesn't include `encore.tlz.us`.
- **Do not re-add verify/provenance.** If you see `seal_episode_to_b2`, `/verify`, `verify.html`,
  `Object-Lock`, "sealed" chrome — that's the old direction; leave it dormant or remove, don't feature it.

## Key files
`genblaze-service/`: `app.py` (FastAPI + maker jobs), `studio.html` (SPA), `comfyui_provider.py`,
`vault.py`, `episode.py`, `judges.py`, `planner.py`, `composer.py`, `produce_episode.py`,
`config-encore.yml`, `.env`, `DEVPOST_SUBMISSION.md` (STALE).
`video/`: `make_hero.py`, `make_vo.py`, `script.md` (Derek's VO), `encore_hero.mp4`, `clips/`, `vo/`, `hero/`.
`B:\MaiVid\workflows\wan22-i2v-fixed.json`.

## Health check to run first
```powershell
foreach($p in 8090,8188,11434,8300){ try{ iwr "http://127.0.0.1:$p/" -TimeoutSec 3 -UseBasicParsing|Out-Null;"$p UP"}catch{ if($_.Exception.Response){"$p UP"}else{"$p DOWN"} } }
(iwr 'http://127.0.0.1:8090/health' -UseBasicParsing).Content
(iwr 'https://encore.tlz.us/api/episodes' -UseBasicParsing).Content   # public read works
# local maker sanity (should start a job id):
# iwr http://127.0.0.1:8090/make/shot -Method Post -ContentType application/json -Body '{"show":"warlords-sniper","character":"Lena","scene":"in a neon alley at night","animate":false}'
```

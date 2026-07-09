# Encore — a streaming network run by one GPU

**Tagline:** Everyone else's AI video demo makes a clip. Encore runs a **network**: shows with a
returning cast, episodes with scores and key-art posters, a public maker anyone can use — all
produced by **one home GPU**, with **Backblaze B2** as the network's library and its memory.

**Live:** https://encore.tlz.us — the library, the cast, the studio floor, and the maker are all
real and public. Anything you generate renders on the actual GPU and lands in the actual library.

---

## The problem

Generative video is stuck at the *clip*. Real content is **episodic** — a show lives or dies on
continuity: episode 7 has to star the same character as episode 1, and regenerating a character
usually gets you a stranger. Meanwhile every pipeline burns metered cloud credits per frame, so
nobody can afford to iterate until it's right.

Encore's answer: run the whole studio **local-first** on hardware you own ($0 generation cost,
retakes are free), keep the cast in a **durable, versioned, content-addressable vault on B2**, and
let a local vision judge **grade every take against the anchor** until the right face comes back.

## What it does

- **A real streaming site.** Tonight's featured episode, poster rails, a theater player, cast
  pages — every byte of media streamed from B2 through a range-aware proxy.
- **Cast once, reuse forever.** Identity anchors live in the B2 Series Vault (SHA-256
  content-addressable, versioned `season.json` show bible). Every episode pulls the anchor, so
  the same character returns.
- **Self-correcting identity.** Local Qwen3-VL scores each take against the anchor
  (identity 0.95 badges on the live studio floor) and re-takes with feedback until it passes.
- **Full episodes, not clips.** Premise → plan → identity-anchored keyframes → chained Wan 2.2
  i2v segments (~9–12s per scene) → narration (local voice clone) → **ACE-Step music bed,
  generated on the same GPU, ducked under the VO** → title/end cards → composed MP4 → B2 library.
- **Generated key art.** Every episode gets a 2:3 poster (z-image-turbo) — generated on the same
  GPU, stored on B2, rendered as the network's poster rails.
- **The maker is open to the public.** Anyone on the internet can cast a vault character into a
  new scene or commission a whole episode. Jobs run through a strict FIFO GPU queue; the **Studio
  Floor** shows the GPU, the queue, and identity scores live. Visitor shots join the public
  **"Made On This Network"** strip — a growing community gallery on B2.

## How it uses Genblaze (meaningfully)

- **We built a Genblaze provider for self-hosted ComfyUI** (`submit`/`poll`/`fetch_output`,
  workflow-template driven) — so `Pipeline`/`Step` orchestrates stills, identity edits, video,
  voice **and music** on a local GPU with zero per-generation cost. Because it's just a provider,
  swapping in Sora/Veo/Runway is a one-line change.
- **`Pipeline.from_result`** links retakes into provenance lineage; **`Manifest`** carries the
  SHA-256 chain; media handlers seal manifests into the files.
- The self-correction loop (generate → local Qwen3-VL judge → retake with feedback) is all
  linked Genblaze runs.

## How it uses Backblaze B2 (the hero — data orchestration, not "store a file")

- **Series Vault:** cast identity anchors, content-addressable by SHA-256, versioned by a
  `season.json` bible. B2 is the studio's long-term memory — it's *why* the cast can return.
- **The library IS B2:** episodes, posters, visitor shots, music and manifests all live on B2 and
  stream to the public site through a range-aware `/media/` proxy. Nothing is served from disk.
- **Object-Locked canon:** the blessed cast/bible is immutable under B2 Object Lock (GOVERNANCE);
  versioned deletes are refused — continuity can't be silently rewritten.
- **Community index:** the public gallery is a rolling JSON index on B2, appended by the GPU
  worker as visitors create shots.

## Fully local stack

`z-image-turbo` (stills + posters) · `qwen-image-edit` (identity-anchored scenes) · `wan22-i2v`
chained segments (video) · **ACE-Step 3.5B** (music beds) · local voice clone (narration) ·
Ollama `qwen3-vl` (identity judge + episode planner) — all via ComfyUI/Ollama on one RTX-class
card. **No cloud generation keys are used anywhere.**

## Architecture

```
visitor ─▶ encore.tlz.us ─▶ FIFO GPU queue (one job at a time)
  Shot:    pull anchor from B2 vault ─▶ qwen-image-edit ─▶ Wan 2.2 i2v ─▶ B2 ─▶ community strip
  Episode: plan (Ollama) ─▶ keyframes ─▶ judge vs anchor (retake until pass)
           ─▶ chained i2v ─▶ voice clone VO ─▶ ACE-Step score (ducked) ─▶ compose
           ─▶ episode + generated poster ─▶ B2 library ─▶ poster rail + theater
Everything except B2 runs on-box, for free.
```

## What's real today (no fake results)

Everything above is live and was verified on real public runs — nothing is mocked:
- Public visitors have produced **complete episodes** through encore.tlz.us (e.g. *Flooded
  Pursuit*: 2 scenes, 24s, chained i2v, identity 0.95, built in ~12 min on the queue).
- The vault round-trips a real banked cast (two shows, five characters); the judge scores
  same-vs-different correctly (0.95 vs 0.0); Object Lock refuses deletion of sealed canon.
- Posters were generated for the entire back-catalog on the same GPU; the music bed path is
  verified end-to-end (31.9s ACE-Step flac, ffprobe-checked, ducked by the composer).

## SDK feedback (feedback prize)

- **Contributed a self-hosted ComfyUI provider** — the highest-leverage extension for teams
  already running local generation.
- **Bug (Windows):** `storage/transfer._read_local_file` mangles Windows drive letters
  (`file:///C:/…` → `C:Users\…`), so the sink can't upload local files on Windows; we work
  around it with provider-side B2 upload.
- **Papercut:** `Step.params` is filtered to an undocumented allow-list — non-listed keys are
  **silently dropped**. Confirmed twice: an `image` param (we inject via the provider
  constructor instead) and a `length` param for audio seconds (our 20s request rendered the
  template default 32s). Documenting the allowed set — or passing unknown params through to the
  provider — would save every provider author a debugging session.

## Setup

```bash
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env           # B2_* keys + JUDGE_STRATEGY=ollama
uvicorn app:app --port 8090
# Local backends: ComfyUI @127.0.0.1:8188 (workflow templates included),
# Ollama @11434 (qwen3-vl), optional local voice server @8300
```

Key modules: `vault.py` (B2 Series Vault) · `comfyui_provider.py` (the Genblaze provider) ·
`produce_episode.py` (planner → scenes → chained i2v) · `composer.py` (VO + music duck + cards) ·
`posters.py` (key art) · `music.py` (ACE-Step beds) · `judges.py` (identity judge) ·
`pipeline.py` (seal + Object Lock) · `app.py` + `studio.html` (the network).

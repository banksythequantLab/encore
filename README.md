# Encore — a streaming network run by one GPU

Live: **https://encore.tlz.us**

Encore is a Backblaze Generative Media Hackathon entry: a local-first AI studio
that produces **episodic** content — the same cast returning episode after
episode — on a single local GPU, with **Backblaze B2** as the studio's library
and its memory. See `DEVPOST_SUBMISSION.md` for the full story.

## The problem we solve

Most generative video starts from zero on every prompt: regenerate a character
and you get a stranger; generate scene 2 and it has forgotten scene 1. That's
fine for clips — it's fatal for *shows*, which live or die on continuity.

Encore builds a **persistent canon** instead. Characters are banked once as
identity anchors in a B2 vault and pulled into every subsequent generation.
A local vision judge scores every take against the anchor (pass ≥ 0.9, retake
with feedback otherwise), so drift is caught before it airs. Season memory on
B2 lets the planner write episode N as a continuation of episodes 1..N-1, and
every generation step is sealed as a Genblaze manifest — so the whole creative
process is auditable after the fact.

| | Typical clip generator | Encore |
|---|---|---|
| Character identity | new face per prompt | anchored to a versioned B2 vault |
| Between episodes | no memory | season memory + "Previously on…" recaps |
| Quality control | human eyeballs | judge scores every take, auto-retakes |
| Audit trail | none | sealed manifests w/ retake lineage (The Ledger) |
| Output | a clip | a composed episode: VO, score, cards, poster |

## What's in here

| Module | Role |
|---|---|
| `app.py` | FastAPI app: the public site, FIFO GPU queue, maker + episode jobs, B2 media proxy |
| `studio.html` | The network front page (library rails, theater, cast, maker, live studio floor) |
| `comfyui_provider.py` | Genblaze provider for self-hosted ComfyUI (submit/poll/fetch_output) |
| `pipeline.py` | gen_still/gen_video/gen_voice + self-correction loop + seal & Object Lock |
| `vault.py` | B2 Series Vault: content-addressable cast anchors + versioned season.json |
| `produce_episode.py` | premise → plan (Ollama) → keyframes → judged retakes → chained Wan i2v |
| `composer.py` | VO mix, ducked music bed, title/end cards, episode assembly (ffmpeg) |
| `posters.py` | 2:3 episode key art (z-image-turbo) → B2 posters/ |
| `music.py` | Instrumental beds via ACE-Step 3.5B on the same GPU |
| `judges.py` | Local identity judge (Ollama qwen3-vl): anchor vs. take, score + feedback |
| `workflows/` | ComfyUI workflow templates the provider loads (one JSON per model) |

## Requirements

- Windows or Linux box with an RTX-class GPU (24 GB tested)
- **ComfyUI** at `127.0.0.1:8188` with: `z-image-turbo`, `qwen-image-edit`,
  Wan 2.2 i2v, `ace_step_v1_3.5b.safetensors`, and a TTS voice node
- **Ollama** at `127.0.0.1:11434` with a `qwen3-vl` vision model
- A **Backblaze B2** bucket + scoped application key
- `ffmpeg`/`ffprobe` on PATH

## Setup

```bash
python -m venv .venv && .venv/Scripts/activate   # or source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                             # fill in B2_* etc.
set COMFY_WORKFLOWS=./workflows                  # or point at your own templates
uvicorn app:app --port 8090
```

Open `http://127.0.0.1:8090/` — the network page. Bank a cast into the vault
(`vault.py`), then make shots and episodes from the page.

`PUBLIC_DEMO_FORCE=1` re-locks generation to the local box (gallery stays public).

## Integration notes (Genblaze)

The generation path (stills, identity edits, video, voice, music) runs as Genblaze
`Pipeline`/`Step` calls through the custom ComfyUI provider, with manifests sealed to B2 and
`from_result` lineage linking retakes. The **identity judge** (Ollama Qwen3-VL) is currently
orchestrated in application code around those runs rather than as a Genblaze Step: the SDK's
step model doesn't yet have a first-class evaluator/conditional-retry primitive, so the loop
lives in `pipeline.gen_still` and records its scores in the run logs. Folding judges into the
SDK as a step type is the integration we'd most like to see upstream (see our filed issues).

## Safety notes

- `.env` is gitignored; use a **scoped** B2 application key, never the master key.
- Public episodes cost real GPU minutes (~12 min each) — put the maker behind
  caps or `PUBLIC_DEMO_FORCE=1` if you don't want strangers queueing your card.

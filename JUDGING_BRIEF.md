# ENCORE — Judging Brief (for an outside AI acting as hackathon judge)

You are a judge for the Backblaze Generative Media Hackathon (Devpost, deadline Aug 3 2026).
Grade this entry strictly against the criteria below. Everything you need is in this brief;
all claims here were verified on live runs (the team's rule: nothing claimed unless tested).

## Judging criteria
1. Meaningful use of Backblaze B2 (data orchestration, not just storage)
2. Meaningful use of the Genblaze SDK (Pipeline/Step/providers/manifests)
3. Creativity / wow / does it stand out
4. Demo quality — video "shows the project functioning" (~3 min guidance)
5. (Side prize) Quality of SDK feedback filed

## The entry
**Encore** — an AI streaming network with a persistent cast. One-sentence thesis: *the studio's
memory doesn't live in the model; it lives on Backblaze B2* — identity anchors, the season's
story, and every episode — and every new take is judged against that memory.

- Live: https://encore.tlz.us (library, cast, studio floor public)
- Code: https://github.com/banksythequantLab/encore
- Video: https://youtu.be/LXRHYu_BHig (v10, 70s) — cold open, thesis narration, live
  generation sequence (maker → Genblaze pipeline progress → finished take), Backblaze B2
  badge on every frame, Genblaze named in VO and captions.

## What it does (all verified live)
- **Series Vault on B2:** cast identity anchors, SHA-256 content-addressable, versioned
  season.json show bible. Anchors condition every new shot (qwen-image-edit).
- **Judged retakes:** local Qwen3-VL scores each episode keyframe against the anchor
  (0.95 scores observed); failures re-shoot with feedback. Retakes carry `parent_run_id`
  lineage in sealed Genblaze manifests on B2 (visible in the public "Ledger").
- **Serialized season memory:** produce_episode reads prior episode synopses from
  `season_memory.json` on B2 and plans the next chapter; episodes open with a
  "Previously on Encore…" card recalled from B2; each aired episode writes itself back.
  Verified: episode "Signal In The Shadows" continued "Submersion"'s plot autonomously.
- **Full episode pipeline:** premise → Ollama plan → judged keyframes → chained Wan 2.2 i2v
  (~9-12s/scene) → cloned-voice narration → ACE-Step music bed (generated in-pipeline,
  ducked) → title/end cards → composed MP4 → B2 library → auto-generated 2:3 poster.
- **The site streams everything from B2** via a range-aware /media proxy: 5 episodes,
  posters, community shots, manifests. Metrics, ledger, live studio floor.
- **Genblaze integration:** a custom self-hosted ComfyUI provider (submit/poll/fetch_output,
  workflow-template driven) drives stills, identity edits, video, voice AND music through
  Pipeline/Step; manifests sealed and persisted to B2; `from_result` lineage on retakes.
- **SDK feedback filed:** backblaze-labs/genblaze #132 (Windows file:// drive-letter bug,
  root-caused with suggested fix) and #133 (silent params allow-list, two concrete repros).
- Per-IP rate caps on generation endpoints (verified: 4 accepted, 5th → HTTP 429).

## Known limitations (disclose to be fair)
- Identity consistency is strong anchor→shot (single edit step) but drifts across episodes
  (hair/face vary between episodes despite judge passes). The demo shows the honest case.
- One show with 5 episodes + a second show with anchors only; library is small.
- Demo video is 70s against a ~3-minute guidance.
- Features cut during development (still in git history, not in the entry): nightly
  self-airing scheduler, public-maker invitations, an Object-Lock "try to delete" stunt.
- Site copy retains "runs on one home GPU" phrasing; the video does not emphasize it.

## Your task
Score each criterion 1-10 with justification, list the top 3 strengths and top 3 risks a
real judge would flag, and name the highest-impact improvements achievable before Aug 3.

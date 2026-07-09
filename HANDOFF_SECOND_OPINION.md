# ENCORE — Full Project Brief (for an outside AI second opinion)

You are being asked for a second opinion on a hackathon entry. This document is
self-contained: everything you need to evaluate the project is here. Please
critique the concept, the architecture, the prioritization, and the pitch — and
flag risks or better ideas the team may be missing.

## 1. Contest context

- **Event:** Backblaze Generative Media Hackathon (Devpost). Deadline **Aug 3, 2026, 5pm ET**.
- **Judging emphasis:** meaningful use of **Backblaze B2** (data orchestration, not
  "store a file"), meaningful use of the **Genblaze SDK** (Backblaze's new Python
  media-pipeline SDK: Pipeline/Step/providers/manifests/sinks), overall wow,
  plus a **feedback prize** for actionable SDK bug reports/contributions.
- **Required deliverables:** public repo, ~3-min demo video, Devpost write-up.

## 2. The one-sentence pitch

**Encore is a streaming network run by one GPU** — an AI studio that makes
*seasons, not clips*: shows with a returning cast, full episodes with scores and
key-art posters, a maker open to the public — produced entirely on a single home
RTX 3090, with Backblaze B2 as the network's library and its memory.

Live site: https://encore.tlz.us · Code: https://github.com/banksythequantLab/encore

## 3. Why this angle

Every AI-video demo makes one disposable clip. Real content is episodic, and
episodic lives or dies on **continuity** — episode 7 must star the same character
as episode 1. Regenerating a character normally produces a stranger. Encore's
thesis: (a) keep cast identity in a durable, content-addressable **vault on B2**;
(b) **judge every take** against the anchor with a local vision model and retake
until it passes; (c) run everything local-first so retakes cost $0.

## 4. Hardware / stack (all self-hosted, Windows)

- One RTX 3090 (24 GB) box ("Vesper"). No cloud generation anywhere.
- **ComfyUI** (127.0.0.1:8188): `z-image-turbo` (stills/posters), `qwen-image-edit`
  (identity-anchored scene placement), Wan 2.2 i2v (video), **ACE-Step 3.5B**
  (music), TTS voice node; separate local voice-clone server on :8300.
- **Ollama** (:11434): `qwen3-vl` = identity judge + episode planner.
- **FastAPI app** (:8090) behind a Cloudflare tunnel → encore.tlz.us.
- **Backblaze B2** private bucket, all media streamed to the public site through
  a range-aware `/media/` proxy in the app.

## 5. Architecture (as built and verified)

```
visitor → encore.tlz.us → FIFO GPU queue (strictly one job at a time)
 SHOT:    pull identity anchor from B2 vault → qwen-image-edit (same face, new
          scene) → optional Wan 2.2 i2v clip → B2 → public "community strip"
 EPISODE: ACE-Step music bed (same GPU) → Ollama plan (title/scenes/beats)
          → per scene: keyframe → Qwen3-VL judge vs anchor (score, feedback,
          retake until pass) → chained i2v segments (49f each, last-frame →
          start_image, ffmpeg concat ≈ 9-12s/scene) → voice-over → compose
          (title card, captions, ducked music, end card) → episode MP4 → B2
          → auto-generated 2:3 poster (z-image-turbo) → B2 posters/
```

**Genblaze's role:** we wrote a custom Genblaze *provider* for self-hosted ComfyUI
(submit/poll/fetch_output, workflow-template driven). Every generation is a
Genblaze Pipeline step; retakes are linked runs (`from_result` lineage); SHA-256
manifests are sealed into files; the blessed cast bible is under **B2 Object
Lock (GOVERNANCE)** — versioned deletes are refused, so canon can't be rewritten.

**B2's role (the part judges care about):**
- Series Vault: cast anchors, content-addressable by SHA-256, versioned
  `season.json` show bible per show. This is *why* a character can return.
- The library IS B2: episodes, posters, visitor shots, music, manifests — the
  public site streams everything from the bucket; nothing served from disk.
- Community index: rolling JSON on B2 appended by the GPU worker.
- Object-Locked canon (immutability demonstrated by a refused delete).

## 6. The public site (redesigned July 8-9 as a "streaming network")

Nav: Tonight / Library / Cast / Make Your Own / Studio Floor / The Vault.
- **Tonight:** hero with featured episode key art + Play (theater modal).
- **Library:** per-show poster rails; posters are GPU-generated key art.
- **Cast:** anchor cards, "under contract," click-to-cast prefills the maker.
- **Make Your Own:** PUBLIC — anyone can render a shot (~2.5 min) or commission
  a full episode (~20 min GPU) on the real hardware. FIFO queue, live progress.
- **Studio Floor:** live GPU state, queue depth, per-job stage, identity scores.
- **Made On This Network:** strip of visitor-created shots (from the B2 index).

## 7. Evidence discipline

House rule: nothing is claimed unless verified on a real run (no mocks).
Verified so far: public visitors produced complete episodes through the site
(latest, "Submersion": music bed present — measured RMS −23 dB on the no-VO title
card; identity 0.95; auto-poster appeared in the rail); judge scores
same-vs-different 0.95 vs 0.0; Object Lock refuses deletion; posters backfilled
for the whole catalog; community strip populated by a real public shot.

## 8. SDK feedback already filed (feedback prize)

- **#132:** Windows `file://` drive-letter bug in `storage/transfer._read_local_file`
  (`file:///C:/…` → `C:Users\…`), with root cause + suggested fix.
- **#133:** `Step.params` silently filtered against an undocumented allow-list
  (dropped `image`, and dropped `length` so a 20s audio request rendered the
  32s template default) — asks for docs, passthrough, or warnings.
- Drafted but not yet filed: an offer to contribute the ComfyUI provider upstream.

## 9. Approved next steps (this is what we want your opinion on)

Planned "showstopper" upgrades, in the team's current priority order:
1. **Self-airing network:** scheduler produces and premieres a new episode
   nightly, unattended, with an on-site countdown ("Tonight 9PM: Episode N").
   Reframe: not a demo — a channel that's been running for weeks.
2. **ON AIR mode:** when the GPU is producing, the hero flips to "● NOW
   FILMING" with live stage/identity-score/VRAM telemetry. (Serialized
   season-memory — Ollama reads the season so far from B2 and writes the next
   chapter, plus auto "Previously on…" recaps — was rated highly but is NOT in
   the approved batch; challenge this if you disagree.)
3. **Cast voices:** per-character voice clones (:8300 server) → real dialogue
   scenes, not narrator-only; character pages with a filmography assembled from
   B2 provenance manifests ("IMDb built from manifests").
4. **Immutability stunt:** a Canon page with a real "Delete the cast bible"
   button that shows B2's live `AccessDenied` refusal.
5. **Meta demo video:** the network produces its own ~3-min submission video
   (ident, cloned-voice narration, ACE-Step score).

Still open: per-IP rate caps on the public maker (an episode now costs ~20 min
GPU; judging-week griefing is a real risk), and the Devpost form submission.

## 10. Questions for you

1. Is "a streaming network run by one GPU" the strongest frame, or is there a
   sharper pitch hiding in this stack?
2. Does the priority order in §9 maximize judge impact for ~3 weeks of part-time
   work? What would you cut, reorder, or add? (Note the team skipped serialized
   season-continuity from the approved batch — mistake or right call?)
3. Where is this weakest against the two headline criteria (meaningful B2,
   meaningful Genblaze)? What would make either undeniable?
4. What demo-video structure would land hardest in 3 minutes?
5. What risks are underweighted (public GPU abuse, single-box uptime during
   judging, episode quality variance, anything else)?
6. Any cheap credibility upgrades we're missing (metrics page, uptime counter,
   cost-per-episode vs cloud comparison, etc.)?

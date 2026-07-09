# Encore — 3-minute demo script (series flow)

Keep under 3:00. Record 1080p. Narrate live or with your cloned voice (FreeClone).
You already have the hero assets: `ep_eva.png` (neon rooftop) and `ep_eva2.png` (cherry-blossom garden).

---

**0:00-0:18 - Hook**
> "Every AI video tool makes *one clip*. But a series needs the same cast, episode after episode - and that's the one thing generative video can't do. Encore can. On your own GPUs. With Backblaze B2 as the studio's memory."

**0:18-0:45 - The Series Vault (B2 is the memory)**
Show the B2 console at `vault/hero-ai/` - the cast anchors + `season.json`. (Or run `vault.load_cast_from_b2("hero-ai")` and show the three cast names print.)
> "This is the Series Vault, living on Backblaze B2. Three characters, each stored as a content-addressable *identity anchor*, with a versioned show bible. This is what lets a character come back."

**0:45-1:20 - Episode 1, then the cast returns in Episode 2**
Show `ep_eva.png`. Then run `episode.gen_episode_shot("hero-ai","A.I. (Eva)", "<new scene>")` (or show `ep_eva2.png`). Put the two side by side.
> "Episode 1 - Eva, on a neon rooftop at night. Episode 2 - different day, different world, a cherry-blossom garden. Same Eva. Not a lookalike - her actual identity, pulled from her vault anchor and edited into a brand-new scene."

**1:20-1:55 - It grades its own continuity (LOCAL judge)**
Show the identity-judge output: same -> `0.95 pass`; different castmate -> `0.0 fail` with the feedback line ("a human woman vs the AI robot Eva").
> "And it checks its own work. A local vision model - Qwen3-VL, running in Ollama on this machine, no cloud - compares every shot to the anchor and re-takes until the identity matches. Same character: 0.95. A different castmate: zero. All on-box."

**1:55-2:30 - Sealed + immutable on B2 (Object Lock)**
Open the verify page (`:8090`), drop an episode -> **Verified** (model, prompt, hash). Then in a terminal, try to delete the locked manifest version -> **AccessDenied**.
> "Every episode is sealed with a cryptographic manifest on B2 - and the show's canon is Object-Locked. Try to delete it: B2 refuses. Continuity you literally cannot rewrite."

**2:30-3:00 - Close (the story)**
> "Nothing here touched a cloud generation API. It all ran on local GPUs, for free. Backblaze B2 is the *one* external service - and that's the point: it's the durable, versioned, immutable memory that turns clips into a *series*. Genblaze orchestrates the whole thing, so you could swap in Sora or Veo with one line. Encore - an AI studio that makes seasons, not clips."
End card: name + tagline + verify URL.

---

## Capture checklist
- [ ] B2 console: `vault/hero-ai/` (anchors + `season.json`) - the memory
- [ ] Ep 1 -> Ep 2 returning cast: `ep_eva.png` + `ep_eva2.png` side by side (or a live `episode.gen_episode_shot` run)
- [ ] Identity judge: `JUDGE_STRATEGY=ollama` - same `0.95` vs different `0.0` + feedback (`_idjudgetest.py`)
- [ ] Verify page: a sealed episode -> Verified
- [ ] Terminal: Object Lock refuses a versioned delete (`_locktest.py` -> `AccessDenied`)
- [ ] "No cloud generation keys" - worth saying out loud; it's the differentiator
- [ ] Upload public to YouTube/Vimeo (not private), link on the Devpost submission

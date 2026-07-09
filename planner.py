"""
EpisodeSpec planner — local Ollama, zero cloud.

Turns a show premise into a structured, machine-usable episode plan: a list of
scenes, each with a keyframe prompt (put the SAME cast member in a new setting),
a motion prompt (for Wan i2v), a one-line narration, and a short on-screen
caption. Mirrors the sample app's structured-spec idiom (Pydantic) so the rest of
the pipeline consumes a validated object, not free text.
"""
from __future__ import annotations

import json
import os
from typing import List

import httpx
from pydantic import BaseModel, Field

OLLAMA = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
PLAN_MODEL = os.environ.get("OLLAMA_PLAN_MODEL", "qwen3:8b")


class Scene(BaseModel):
    scene_id: int
    location: str = Field(..., description="short setting label")
    keyframe_prompt: str = Field(..., description="image-edit prompt placing the character in this scene")
    motion_prompt: str = Field(..., description="camera + subject motion for image-to-video")
    narration: str = Field(..., description="one-sentence voiceover line")
    caption: str = Field(..., description="<=6 word on-screen caption")


class EpisodeSpec(BaseModel):
    show: str
    character: str
    episode_title: str
    logline: str
    scenes: List[Scene]


_SYS = """You are a TV series showrunner. You write tight, cinematic episode plans.
Return ONLY valid JSON matching this schema (no prose, no markdown):
{
  "episode_title": string,
  "logline": string (<=30 words),
  "scenes": [
    {
      "scene_id": integer starting at 1,
      "location": string,
      "keyframe_prompt": string,   // describe the SAME lead character in THIS new setting, action pose, wardrobe consistent; do NOT change the person's identity/face
      "motion_prompt": string,     // camera move + what the subject physically does, for image-to-video (e.g. 'slow push-in, she raises the rifle, rain falling')
      "narration": string,         // ONE spoken sentence of voiceover
      "caption": string            // <= 6 words, on-screen
    }
  ]
}
The lead character stays visually identical across every scene (same face/identity); only the world and action change."""


def plan_episode(show: str, character: str, premise: str, n_scenes: int = 3,
                 style: str = "") -> EpisodeSpec:
    user = (f"SHOW: {show}\nLEAD CHARACTER: {character}\nVISUAL STYLE: {style or 'cinematic, filmic'}\n"
            f"PREMISE: {premise}\n\nWrite exactly {n_scenes} scenes. "
            f"Each keyframe_prompt must keep {character} identical in face/identity while changing setting and action.")
    r = httpx.post(f"{OLLAMA}/api/chat", timeout=180, json={
        "model": PLAN_MODEL,
        "messages": [{"role": "system", "content": _SYS}, {"role": "user", "content": user}],
        "stream": False, "format": "json", "options": {"temperature": 0.7},
    })
    r.raise_for_status()
    raw = json.loads(r.json()["message"]["content"])
    scenes = []
    for i, s in enumerate(raw.get("scenes", [])[:n_scenes], start=1):
        scenes.append(Scene(
            scene_id=s.get("scene_id", i),
            location=s.get("location", f"scene {i}"),
            keyframe_prompt=s["keyframe_prompt"],
            motion_prompt=s.get("motion_prompt", "slow cinematic push-in, subtle motion"),
            narration=s.get("narration", ""),
            caption=(s.get("caption", "") or "")[:48],
        ))
    if not scenes:
        raise RuntimeError("planner produced no scenes")
    return EpisodeSpec(show=show, character=character,
                       episode_title=raw.get("episode_title", f"{show} — Episode"),
                       logline=raw.get("logline", premise[:120]), scenes=scenes)


if __name__ == "__main__":
    import sys
    spec = plan_episode(
        sys.argv[1] if len(sys.argv) > 1 else "warlords-sniper",
        sys.argv[2] if len(sys.argv) > 2 else "Lena",
        sys.argv[3] if len(sys.argv) > 3 else
        "A lone sniper hunts a warlord across a rain-soaked city over one long night.",
        int(sys.argv[4]) if len(sys.argv) > 4 else 3,
    )
    print(spec.model_dump_json(indent=2))

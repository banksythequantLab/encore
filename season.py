"""Season memory — the serialized-continuity engine.

B2 is the network's narrative memory: every aired episode writes a synopsis to
vault/<show>/season_memory.json, and the planner READS that memory to write the
next chapter. Continuity as infrastructure, not a prompt trick.
"""
import json
import os
import time

import httpx

OLLAMA = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
PLAN_MODEL = os.environ.get("OLLAMA_PLAN_MODEL", "qwen3:8b")


def _mem_key(show: str) -> str:
    return f"vault/{show}/season_memory.json"


def load_memory(show: str) -> dict:
    from comfyui_provider import _b2
    try:
        return json.loads(_b2().get(_mem_key(show)).decode())
    except Exception:
        return {"show": show, "episodes": []}


def record_episode(show: str, spec, stored: dict) -> None:
    """Write the aired episode into the season's memory on B2."""
    from comfyui_provider import _b2
    mem = load_memory(show)
    beats = "; ".join(f"{s.location}: {s.narration}" for s in spec.scenes if s.narration)
    mem["episodes"].append({
        "n": len(mem["episodes"]) + 1,
        "title": spec.episode_title,
        "logline": spec.logline,
        "beats": beats[:400],
        "b2_key": stored.get("b2_key"),
        "aired": time.strftime("%Y-%m-%dT%H:%M:%S"),
    })
    _b2().put(_mem_key(show), json.dumps(mem, indent=2).encode())


def previously_text(mem: dict, k: int = 2) -> str:
    """Compact 'the story so far' block for the planner (last k episodes)."""
    eps = mem.get("episodes", [])[-k:]
    if not eps:
        return ""
    return "\n".join(f"Ep{e['n']} \"{e['title']}\": {e['logline']} ({e['beats']})" for e in eps)


def previously_line(mem: dict) -> str:
    """One short 'Previously on…' line from the latest episode."""
    eps = mem.get("episodes", [])
    if not eps:
        return ""
    e = eps[-1]
    return f"Previously: {e['logline']}"[:90]


def next_premise(show: str, character: str) -> str:
    """Ask the local planner model for the next chapter, given the season so far."""
    mem = load_memory(show)
    prev = previously_text(mem, k=3)
    if not prev:
        return (f"A tense, cinematic opening chapter for {character}: establish the world, "
                f"the enemy, and what {character} is fighting for.")
    r = httpx.post(f"{OLLAMA}/api/chat", timeout=120, json={
        "model": PLAN_MODEL,
        "messages": [
            {"role": "system", "content":
             "You are a TV showrunner writing a serialized season. Given the story so far, "
             "pitch the NEXT episode. Return ONLY JSON: {\"premise\": string (<=35 words, "
             "continues directly from the last episode's events, raises the stakes)}"},
            {"role": "user", "content": f"SHOW: {show}\nLEAD: {character}\nSTORY SO FAR:\n{prev}"},
        ],
        "stream": False, "format": "json", "options": {"temperature": 0.8},
    })
    r.raise_for_status()
    p = json.loads(r.json()["message"]["content"]).get("premise", "")
    return p or f"The next chapter of {character}'s story — continue from the last episode."

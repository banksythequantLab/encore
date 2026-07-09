import json

from dotenv import load_dotenv

load_dotenv()

import season  # noqa: E402
from comfyui_provider import _b2  # noqa: E402

# Seed memory with the real Submersion episode (from its proof json), once.
proof = json.load(open("_episode_proof.json"))
mem = season.load_memory("warlords-sniper")
if not any(e["title"] == proof["episode_title"] for e in mem["episodes"]):
    mem["episodes"].append({
        "n": len(mem["episodes"]) + 1,
        "title": proof["episode_title"],
        "logline": proof["logline"],
        "beats": "",
        "b2_key": proof["episode"]["b2_key"],
        "aired": "2026-07-08T21:45:00",
    })
    _b2().put("vault/warlords-sniper/season_memory.json",
              json.dumps(mem, indent=2).encode())
    print("SEEDED", flush=True)

mem = season.load_memory("warlords-sniper")
print("MEMORY:", json.dumps(mem)[:300], flush=True)
print("PREV_LINE:", season.previously_line(mem), flush=True)
premise = season.next_premise("warlords-sniper", "Lena")
print("NEXT_PREMISE:", premise, flush=True)

from planner import plan_episode  # noqa: E402
spec = plan_episode("warlords-sniper", "Lena", premise, 2,
                    previously=season.previously_text(mem))
print("PLAN_TITLE:", spec.episode_title, flush=True)
print("PLAN_LOGLINE:", spec.logline, flush=True)
print("DONE", flush=True)

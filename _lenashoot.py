"""Migrate warlords-sniper to the B2 vault, then render Lena into two new episodes."""
import json, os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
os.environ["JUDGE_STRATEGY"] = "passthrough"
import vault, episode, judges
from comfyui_provider import _b2

OUT = Path(r"C:\Users\solti\AppData\Roaming\Claude\local-agent-mode-sessions"
           r"\052aebbf-870d-4145-83e8-ff7179b1782a\8e6f879d-68f7-44e0-8e92-2909603272a8"
           r"\local_1977794e-6a98-487b-a662-bdbf3f2d4791\outputs")
show = "warlords-sniper"
sd = Path(r"B:\QwenShowrunner\output\seasons") / show
sj = json.loads((sd / "season.json").read_text(encoding="utf-8"))

cast = []
for c in sj.get("cast", []):
    ref = sd / (c.get("ref") or "")
    if ref.exists():
        cast.append({"name": c.get("name", ""), "appearance": c.get("appearance", ""),
                     "locked": c.get("locked", []), "bytes": ref.read_bytes()})
vault.save_cast_to_b2(show, {"style": sj.get("style", ""), "cast": cast})
vault.lock_canon(show)
print("VAULT_MIGRATED", show, [c["name"] for c in cast], flush=True)

scenes = {
    "ep_lena.png": "on a rooftop at night overlooking a rain-slicked neon city skyline, moody cinematic lighting, 35mm",
    "ep_lena2.png": "crouched on a snowy mountain ridge at dawn, drifting snow and wind, cold pale light, cinematic",
}
judge = judges.make_judge("Lena")
for fn, scene in scenes.items():
    out = episode.gen_episode_shot(show, "Lena", scene, judge, run_name="lena", max_iter=1)
    ch = out.get("chosen") or {}
    if ch.get("b2_key"):
        (OUT / fn).write_bytes(_b2().get(ch["b2_key"]))
        print("RENDER", fn, "sealed=", ch.get("sealed"), "locked=", ch.get("locked"), flush=True)
    else:
        print("RENDER_FAIL", fn, str(out)[:200], flush=True)
print("LENA_DONE", flush=True)

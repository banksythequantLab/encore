"""Render one episode shot: Eva (from the B2 vault) into a new scene. The moat demo."""
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
os.environ["JUDGE_STRATEGY"] = "passthrough"  # accept first take; identity judge needs a vision key
import traceback
import episode, judges
from comfyui_provider import _b2

OUT = Path(r"C:\Users\solti\AppData\Roaming\Claude\local-agent-mode-sessions\052aebbf-870d-4145-83e8-ff7179b1782a\8e6f879d-68f7-44e0-8e92-2909603272a8\local_1977794e-6a98-487b-a662-bdbf3f2d4791\outputs")

judge = judges.make_judge("Eva")
try:
    out = episode.gen_episode_shot(
        "hero-ai", "A.I. (Eva)",
        "standing on a neon-lit rooftop at night, glowing city skyline behind her, cinematic 35mm",
        judge, run_name="ep", max_iter=1)
    ch = out.get("chosen") or {}
    print("PASSED=", out["passed"], "retakes=", out["retakes"], flush=True)
    print("B2_KEY=", ch.get("b2_key"), flush=True)
    print("SEALED_URL=", ch.get("sealed_url"), flush=True)
    print("LOCKED=", ch.get("locked"), flush=True)
    if ch.get("b2_key"):
        dst = OUT / "ep_eva.png"
        dst.write_bytes(_b2().get(ch["b2_key"]))
        print("SAVED=", str(dst), flush=True)
except Exception as e:
    traceback.print_exc()
    print("ERR:", type(e).__name__, str(e)[:300], flush=True)

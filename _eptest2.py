"""Second episode shot — same Eva, a very different scene. Proves cross-episode identity."""
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
os.environ["JUDGE_STRATEGY"] = "passthrough"
import traceback
import episode, judges
from comfyui_provider import _b2

OUT = Path(r"C:\Users\solti\AppData\Roaming\Claude\local-agent-mode-sessions\052aebbf-870d-4145-83e8-ff7179b1782a\8e6f879d-68f7-44e0-8e92-2909603272a8\local_1977794e-6a98-487b-a662-bdbf3f2d4791\outputs")
judge = judges.make_judge("Eva")
try:
    out = episode.gen_episode_shot(
        "hero-ai", "A.I. (Eva)",
        "sitting cross-legged in a sunlit Japanese garden, cherry blossoms falling, daytime, serene",
        judge, run_name="ep2", max_iter=1)
    ch = out.get("chosen") or {}
    print("PASSED=", out["passed"], flush=True)
    print("SEALED_URL=", ch.get("sealed_url"), "LOCKED=", ch.get("locked"), flush=True)
    if ch.get("b2_key"):
        (OUT / "ep_eva2.png").write_bytes(_b2().get(ch["b2_key"]))
        print("SAVED=", str(OUT / "ep_eva2.png"), flush=True)
except Exception as e:
    traceback.print_exc(); print("ERR:", type(e).__name__, str(e)[:300], flush=True)

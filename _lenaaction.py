"""Re-render Lena in clear ACTION poses so episodes read as new shots, not a paste."""
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
os.environ["JUDGE_STRATEGY"] = "passthrough"
import episode, judges
from comfyui_provider import _b2

OUT = Path(r"C:\Users\solti\AppData\Roaming\Claude\local-agent-mode-sessions"
           r"\052aebbf-870d-4145-83e8-ff7179b1782a\8e6f879d-68f7-44e0-8e92-2909603272a8"
           r"\local_1977794e-6a98-487b-a662-bdbf3f2d4791\outputs")
scenes = {
    "ep_lena.png": "cinematic action still: Lena kneeling on one knee, aiming a long scoped sniper "
                   "rifle, sharp side profile, on a rain-soaked neon rooftop at night, dramatic low angle, 35mm",
    "ep_lena2.png": "cinematic still: Lena crouched low and alert behind a rock on a snowy mountain "
                    "ridge at dawn, gripping a rifle, looking off-screen, wind and drifting snow, cold light",
    "ep_lena3.png": "cinematic still: Lena sprinting through a narrow rain-soaked neon alley at night, "
                    "dynamic motion, splashing puddles, dramatic side light, 35mm",
}
judge = judges.make_judge("Lena")
for fn, scene in scenes.items():
    out = episode.gen_episode_shot("warlords-sniper", "Lena", scene, judge, run_name="lenaA", max_iter=1)
    ch = out.get("chosen") or {}
    if ch.get("b2_key"):
        (OUT / fn).write_bytes(_b2().get(ch["b2_key"]))
        print("RENDER", fn, flush=True)
    else:
        print("FAIL", fn, str(out)[:150], flush=True)
print("ACTION_DONE", flush=True)

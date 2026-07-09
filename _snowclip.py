"""Generate the Episode-2 snow-ridge motion clip from the existing ep_lena2 still (Wan i2v)."""
import os
from dotenv import load_dotenv
load_dotenv()
from genblaze_core import Modality, Pipeline
from comfyui_provider import ComfyUIProvider, _b2
import pipeline

KF = (r"C:\Users\solti\AppData\Roaming\Claude\local-agent-mode-sessions"
      r"\052aebbf-870d-4145-83e8-ff7179b1782a\8e6f879d-68f7-44e0-8e92-2909603272a8"
      r"\local_1977794e-6a98-487b-a662-bdbf3f2d4791\outputs\ep_lena2.png")
OUT = r"B:\Filmwriter-Local\video\clips\snow_ep2.mp4"

result = (Pipeline("encore").step(
    ComfyUIProvider(image_ref=KF), model="wan22-i2v",
    prompt=("Lena on a snowy mountain ridge at dawn, slowly scanning the horizon, "
            "snow drifting in the wind, breath fogging, cold pale light, cinematic, subtle camera push-in"),
    modality=Modality.VIDEO).run(timeout=1500, raise_on_failure=False))
run, _m = pipeline._unpack(result)
step = run.steps[-1]
if step.assets:
    a = step.assets[0]
    data = _b2().get((a.metadata or {}).get("b2_key"))
    with open(OUT, "wb") as f:
        f.write(data)
    print("SNOW_OK", OUT, "sha", (a.sha256 or "")[:12], "size", len(data), flush=True)
else:
    print("SNOW_FAIL", getattr(step, "error", None), getattr(step, "error_code", None), flush=True)

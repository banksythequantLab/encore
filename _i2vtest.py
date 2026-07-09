"""Test image-to-video: animate a Lena keyframe via Wan 2.2 i2v through the provider."""
import os
from dotenv import load_dotenv
load_dotenv()
from genblaze_core import Modality, Pipeline
from comfyui_provider import ComfyUIProvider
import pipeline

KF = r"B:\Filmwriter-Local\video\_lena_kf.png"
try:
    result = (Pipeline("encore").step(
        ComfyUIProvider(image_ref=KF), model="wan22-i2v",
        prompt="Lena slowly steadies her sniper rifle, subtle breathing, rain falling, neon reflections, cinematic",
        modality=Modality.VIDEO).run(timeout=1200, raise_on_failure=False))
    run, manifest = pipeline._unpack(result)
    step = run.steps[-1]
    print("STATUS", getattr(step, "status", None), flush=True)
    assets = step.assets or []
    if assets:
        a = assets[0]
        print("URL", a.url, flush=True)
        print("MIME", a.media_type, "SHA", (a.sha256 or "")[:16], "SIZE", a.size_bytes, flush=True)
    else:
        print("NO_ASSET err=", getattr(step, "error", None), getattr(step, "error_code", None), flush=True)
except Exception as e:
    import traceback; traceback.print_exc(); print("ERR", type(e).__name__, str(e)[:300], flush=True)

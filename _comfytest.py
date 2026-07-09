"""Free E2E: ComfyUI still -> provider stores to B2 -> manifest to B2. No credits."""
import os, traceback
from dotenv import load_dotenv
load_dotenv()
from genblaze_core import Pipeline, Modality
from comfyui_provider import ComfyUIProvider, _b2

print("SUBMIT ComfyUI z-image-turbo ...", flush=True)
try:
    result = (
        Pipeline("comfy-smoke-still")
        .step(ComfyUIProvider(), model="z-image-turbo",
              prompt="A neon-lit rain-slicked Tokyo alley at night, cinematic, 35mm",
              modality=Modality.IMAGE, params={"width": 1024, "height": 576})
        .run(timeout=300)
    )
    run = getattr(result, "run", None) or result[0]
    manifest = getattr(result, "manifest", None) or result[1]
    step = run.steps[-1]
    print("STEP_STATUS=", getattr(step, "status", None), flush=True)
    a = step.assets[0]
    print("ASSET_URL=", a.url, flush=True)
    print("SHA256=", a.sha256, flush=True)
    print("SIZE=", a.size_bytes, flush=True)
    mkey = f"comfyui/manifests/{run.run_id}.json"
    _b2().put(mkey, manifest.to_canonical_json().encode())
    print("MANIFEST_KEY=", mkey, flush=True)
    print("CANONICAL_HASH=", manifest.canonical_hash, flush=True)
    print("VERIFY=", manifest.verify(), flush=True)
    print("VERIFY_HASH=", manifest.verify_hash(), flush=True)
except Exception as e:
    traceback.print_exc()
    print("ERR:", type(e).__name__, str(e)[:400], flush=True)

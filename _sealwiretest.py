"""No-GPU test of seal_and_lock: fake a generated asset on B2, then seal+lock it."""
import hashlib, tempfile
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
from PIL import Image
from genblaze_core import RunBuilder, StepBuilder, StepStatus, Modality, Manifest
from genblaze_core.media import PngHandler
from comfyui_provider import _b2
import pipeline

img = Path(tempfile.gettempdir()) / "wire.png"
Image.new("RGB", (80, 80), (30, 140, 90)).save(img)
raw = img.read_bytes(); sha = hashlib.sha256(raw).hexdigest()
b2key = f"comfyui/assets/{sha[:2]}/{sha[2:4]}/{sha}.png"
_b2().put(b2key, raw)
rec = {"b2_key": b2key, "sha256": sha, "media_type": "image/png",
       "run_id": "wire-" + sha[:8], "url": _b2().get_durable_url(b2key)}
step = (StepBuilder("comfyui", "z-image-turbo").prompt("wire test shot")
        .modality(Modality.IMAGE).status(StepStatus.SUCCEEDED)
        .asset("file://" + str(img), "image/png", sha256=sha).build())
man = Manifest.from_run(RunBuilder(rec["run_id"]).add_step(step).build())

pipeline.seal_and_lock(rec, man)
print("SEALED=", rec.get("sealed"), "LOCKED=", rec.get("locked"))
print("sealed_url=", rec.get("sealed_url"))
print("seal_error=", rec.get("seal_error"))
print("lock_error=", rec.get("lock_error"))

if rec.get("sealed_key"):
    out = Path(tempfile.gettempdir()) / "wire_sealed.png"
    out.write_bytes(_b2().get(rec["sealed_key"]))
    print("SEALED_FILE_VERIFY=", PngHandler().verify(out))

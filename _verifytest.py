"""Test /verify with three files: sealed, tampered, never-sealed."""
import hashlib, tempfile
from pathlib import Path
from PIL import Image
import httpx
from genblaze_core import RunBuilder, StepBuilder, StepStatus, Modality, Manifest
from genblaze_core.media import PngHandler

tmp = Path(tempfile.gettempdir())
sealed = tmp / "vf_sealed.png"
Image.new("RGB", (96, 96), (200, 60, 40)).save(sealed)
sha = hashlib.sha256(sealed.read_bytes()).hexdigest()
step = (StepBuilder("comfyui", "z-image-turbo").prompt("A neon Tokyo alley at night")
        .modality(Modality.IMAGE).status(StepStatus.SUCCEEDED)
        .asset("file://" + str(sealed), "image/png", sha256=sha).build())
man = Manifest.from_run(RunBuilder("verify-demo").add_step(step).build())
PngHandler().embed(sealed, man)

tampered = tmp / "vf_tampered.png"
b = bytearray(sealed.read_bytes()); b[len(b) // 2] ^= 0xFF
tampered.write_bytes(bytes(b))

plain = tmp / "vf_plain.png"
Image.new("RGB", (96, 96), (40, 40, 40)).save(plain)

BASE = "http://127.0.0.1:8090"
for label, path in [("SEALED", sealed), ("TAMPERED", tampered), ("UNSEALED", plain)]:
    try:
        with open(path, "rb") as f:
            r = httpx.post(BASE + "/verify",
                           files={"file": (path.name, f, "image/png")}, timeout=30)
        j = r.json()
        prov = (j.get("provenance") or {})
        print(f"{label}: sealed={j['sealed']} verified={j['verified']} "
              f"model={prov.get('model')} prompt={(prov.get('prompt') or '')[:24]}")
    except Exception as e:
        print(f"{label}: ERR {type(e).__name__} {e}")

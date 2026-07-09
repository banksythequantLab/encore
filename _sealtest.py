"""Prove the product linchpin: seal a manifest into a file, verify it,
then show an edited/tampered copy fails. No GPU, no network."""
import hashlib, tempfile
from pathlib import Path
from PIL import Image
from genblaze_core import RunBuilder, StepBuilder, StepStatus, Modality, Manifest
from genblaze_core.media import PngHandler

tmp = Path(tempfile.gettempdir())
p = tmp / "seal_demo.png"
Image.new("RGB", (96, 96), (20, 90, 180)).save(p)
sha = hashlib.sha256(p.read_bytes()).hexdigest()
print("orig_sha=", sha[:16])

step = (StepBuilder("comfyui", "z-image-turbo").prompt("A neon Tokyo alley at night")
        .modality(Modality.IMAGE).status(StepStatus.SUCCEEDED)
        .asset("file://" + str(p), "image/png", sha256=sha).build())
run = RunBuilder("seal-demo").add_step(step).build()
man = Manifest.from_run(run)
print("manifest_verify=", man.verify())

h = PngHandler()
h.embed(p, man)                              # seal manifest into the PNG (in place)
print("sealed_bytes=", len(p.read_bytes()))
ext = h.extract(p)
print("extract_ok=", ext is not None, "extract_verify=", (ext.verify() if ext else None))
print("SEALED_VERIFY=", h.verify(p))         # the verify-page check on the real file


def check(label, path):
    try:
        print(f"{label}=", h.verify(path))
    except Exception as e:
        print(f"{label}= FAIL ({type(e).__name__})")


# Tamper A: re-encode (an edit) -> strips the sealed chunk
p2 = tmp / "seal_edited.png"
Image.open(p).save(p2)
check("EDITED_VERIFY", p2)

# Tamper B: flip a content byte in the sealed file
b = bytearray(p.read_bytes())
b[len(b) // 2] ^= 0xFF
p3 = tmp / "seal_bitflip.png"
p3.write_bytes(bytes(b))
check("BITFLIP_VERIFY", p3)

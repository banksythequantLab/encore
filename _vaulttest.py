"""Migrate a real existing season onto the B2 Series Vault, round-trip, lock canon."""
import json
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
import vault

show = "hero-ai"
show_dir = Path(r"B:\QwenShowrunner\output\seasons") / show
sj = json.loads((show_dir / "season.json").read_text(encoding="utf-8"))
cast = []
for c in sj.get("cast", []):
    ref = show_dir / (c.get("ref") or "")
    if ref.exists():
        cast.append({"name": c.get("name", ""), "appearance": c.get("appearance", ""),
                     "locked": c.get("locked", []), "bytes": ref.read_bytes()})

doc = vault.save_cast_to_b2(show, {"style": sj.get("style", ""), "cast": cast})
print("SAVED show=", show, "cast=", [c["name"] for c in doc["cast"]])
for c in doc["cast"]:
    print("  anchor:", (c["name"] or "?"), "->", c["anchor_key"])

loaded = vault.load_cast_from_b2(show)
print("LOADED cast=", [(c["name"], "dataUri_len=" + str(len(c["dataUri"]))) for c in loaded["cast"]])

vault.lock_canon(show)
print("CANON_LOCKED (immutable on B2)")

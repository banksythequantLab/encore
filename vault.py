"""
B2 Series Vault — the studio's persistent memory.

A single clip is stateless; a SERIES needs durable memory of its cast so episode N
stars the same actors as episode 1. This lifts Filmwriter's season vault (season.mjs)
onto Backblaze B2: character identity anchors stored content-addressable, a versioned
season "bible", and an Object-Locked canon. Episodes pull anchors from here to stay
identity-consistent — B2 as the studio's long-term memory, not a file dump.

Layout on B2:
  vault/<show>/anchors/<sha[:2]>/<sha>.png        content-addressable cast anchors
  vault/<show>/season.json                        the mutable bible (current cast)
  (sealed bucket) vault/<show>/season.canon.json  Object-Locked immutable canon
"""
import base64
import datetime
import hashlib
import json
import os
import tempfile

from genblaze_core import ObjectLockConfig

from comfyui_provider import _b2

VAULT_PREFIX = "vault"


def _anchor_key(show, sha, ext=".png"):
    return f"{VAULT_PREFIX}/{show}/anchors/{sha[:2]}/{sha}{ext}"


def save_cast_to_b2(show: str, season: dict) -> dict:
    """season = {style?, cast:[{name, appearance?, locked?, bytes|path}]}.
    Uploads each anchor (content-addressable) + the season bible to B2."""
    out_cast = []
    for c in season.get("cast", []):
        data = c.get("bytes")
        if data is None and c.get("path"):
            with open(c["path"], "rb") as f:
                data = f.read()
        if not data:
            continue
        sha = hashlib.sha256(data).hexdigest()
        key = _anchor_key(show, sha)
        _b2().put(key, data)
        out_cast.append({
            "name": c["name"], "appearance": c.get("appearance", ""),
            "locked": c.get("locked", []), "anchor_key": key,
            "anchor_url": _b2().get_durable_url(key), "sha256": sha,
        })
    doc = {
        "show": show,
        "updated": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "style": season.get("style", ""), "cast": out_cast,
    }
    _b2().put(f"{VAULT_PREFIX}/{show}/season.json", json.dumps(doc, indent=2).encode())
    return doc


def load_cast_from_b2(show: str) -> dict:
    """Load the season bible from B2 and pull each anchor (data URI for image-edit
    conditioning + a durable URL)."""
    doc = json.loads(_b2().get(f"{VAULT_PREFIX}/{show}/season.json").decode())
    for c in doc.get("cast", []):
        data = _b2().get(c["anchor_key"])
        c["dataUri"] = "data:image/png;base64," + base64.b64encode(data).decode()
    return doc


def lock_canon(show: str, days: int = 365) -> bool:
    """Store an immutable (Object-Lock) copy of the season bible as the canon."""
    import pipeline
    canon = _b2().get(f"{VAULT_PREFIX}/{show}/season.json")
    until = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=days)
    pipeline._sealed_b2().put(
        f"{VAULT_PREFIX}/{show}/season.canon.json", canon,
        object_lock=ObjectLockConfig(retain_until=until, mode="GOVERNANCE"),
    )
    return True


def anchor_tempfile(show: str, character_name: str) -> str:
    """Download a character's anchor to a local temp file (for ComfyUI image-edit input)."""
    for c in load_cast_from_b2(show).get("cast", []):
        if c["name"].lower() == character_name.lower():
            fd, path = tempfile.mkstemp(suffix=".png")
            os.close(fd)
            with open(path, "wb") as f:
                f.write(_b2().get(c["anchor_key"]))
            return path
    raise KeyError(f"character {character_name!r} not in vault {show!r}")

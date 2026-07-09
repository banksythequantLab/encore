"""One-shot: generate posters for existing episodes that lack one."""
import traceback

from dotenv import load_dotenv

load_dotenv()

import posters  # noqa: E402
from comfyui_provider import _b2


def _list(prefix):
    b = _b2()
    keys, tok = [], None
    while True:
        page = b.list(prefix, continuation_token=tok)
        for e in page.entries:
            k = getattr(e, "key", None) or getattr(e, "name", None)
            if k:
                keys.append(k)
        tok = getattr(page, "next_token", None)
        if not tok:
            break
    return keys


have = set(_list("posters/"))
for k in _list("episodes/"):
    if not k.endswith(".mp4") or "/canon/" in k:
        continue
    show = k.split("/")[1]
    stem = k.split("/")[-1][:-4]
    if posters.poster_key(show, stem) in have:
        print("SKIP", stem, flush=True)
        continue
    title = stem.rsplit("-", 1)[0].replace("-", " ").title()
    print("GEN", show, stem, title, flush=True)
    try:
        pk = posters.generate_poster(show, title, stem)
        print("OK", pk, flush=True)
    except Exception as e:
        print("FAIL", stem, e, flush=True)
        traceback.print_exc()
print("DONE", flush=True)

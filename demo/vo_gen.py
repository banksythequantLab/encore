"""Generate the demo-video narration (5 beats) + trailer score on the local GPU."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from dotenv import load_dotenv

load_dotenv(os.path.join(ROOT, ".env"))

BEATS = {
    "b1_hook": ("Every AI video tool makes clips. Disposable. A stranger every time you press "
                "generate. Real stories need something harder — the same character, back again. "
                "This is Encore."),
    "b2_vault": ("Every cast member lives in a vault on Backblaze B2. Content-addressed. "
                 "Versioned. The network's memory. That's why Lena can come back."),
    "b3_judge": ("Every take is judged against her anchor by a local vision model. Wrong face? "
                 "The studio reshoots. And every retake is a sealed manifest with lineage, on B2."),
    "b4_network": ("Encore airs itself. Every night the planner reads the season so far from B2 "
                   "and writes the next chapter. Visitors make their own shots on the network's "
                   "single home GPU. Total cloud spend: zero."),
    "b5_stunt": ("And the canon? Object-locked. Try to delete it — Backblaze refuses, live. "
                 "Seasons, not clips. Encore."),
}

import shutil  # noqa: E402

import produce_episode  # noqa: E402  (same cloned voice the episodes use, :8300)

out_dir = os.path.dirname(os.path.abspath(__file__))
for name, text in BEATS.items():
    dst = os.path.join(out_dir, f"{name}.wav")
    if os.path.exists(dst):
        print("SKIP", name, flush=True)
        continue
    try:
        p = produce_episode._synth_vo(text)
        if not p:
            raise RuntimeError("no audio returned")
        shutil.copy(p, dst)
        os.remove(p)
        print("VO OK", name, dst, os.path.getsize(dst), flush=True)
    except Exception as e:
        print("VO FAIL", name, e, flush=True)

try:
    import music
    import shutil
    bed = music.generate_music_bed(
        "epic cinematic trailer score, driving percussion, dark orchestral hybrid, "
        "rising tension, heroic, instrumental, no vocals")
    dst = os.path.join(out_dir, "score.flac")
    shutil.copy(bed, dst)
    os.remove(bed)
    print("MUSIC OK", dst, flush=True)
except Exception as e:
    print("MUSIC FAIL", e, flush=True)
print("DONE", flush=True)

"""Demo v5 narration: one continuous script, silence-trimmed."""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from dotenv import load_dotenv

load_dotenv(os.path.join(ROOT, ".env"))
import produce_episode  # noqa: E402

BEATS = {
    "n1": "Every AI video tool gives you a clip. And a stranger, every time you press generate.",
    "n2": "Encore is different. It's a streaming network, with a cast that comes back, "
          "episode after episode.",
    "n3": "Here's the secret. The studio's memory doesn't live in the model. It lives on "
          "Backblaze B2. The cast's identity. The season's story. Every episode ever aired. "
          "And every new take is judged against that memory. Wrong face? Reshoot.",
    "n4": "So every episode continues the last one. The planner reads the story so far, "
          "from Backblaze B2, and writes the next chapter.",
    "n5": "Episodes, posters, music, narration — the studio builds all of it. "
          "Backblaze B2 keeps all of it.",
    "n6": "Seasons. Not clips. Encore — built on Backblaze B2.",
    "n7": "And here it is, working. Pick a cast member. Describe a scene. Generate.",
    "n8": "The job runs through the Genblaze pipeline — every step sealed as a manifest "
          "on Backblaze B2. And there's the take. Same face. Brand-new scene.",
}

D = os.path.dirname(os.path.abspath(__file__))
TRIM = ("silenceremove=start_periods=1:start_silence=0.05:start_threshold=-40dB,"
        "areverse,silenceremove=start_periods=1:start_silence=0.05:start_threshold=-40dB,"
        "areverse")
for name, text in BEATS.items():
    dst = os.path.join(D, f"{name}.wav")
    if os.path.exists(dst):
        print("SKIP", name, flush=True)
        continue
    p = produce_episode._synth_vo(text)
    if not p:
        print("FAIL", name, flush=True)
        continue
    r = subprocess.run(["ffmpeg", "-y", "-i", p, "-af", TRIM, dst],
                       capture_output=True, text=True)
    os.remove(p)
    if r.returncode != 0:
        print("TRIMFAIL", name, r.stderr[-200:], flush=True)
        continue
    d = subprocess.run(["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                        "-of", "csv=p=0", dst], capture_output=True, text=True).stdout.strip()
    print("OK", name, round(float(d), 1), "s", flush=True)
print("DONE", flush=True)

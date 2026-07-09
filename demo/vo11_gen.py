"""Demo v11: two new narration beats (retake proof + ledger), silence-trimmed."""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from dotenv import load_dotenv

load_dotenv(os.path.join(ROOT, ".env"))
import produce_episode  # noqa: E402

BEATS = {
    "n9": "And that's not a promise. Watch it happen. Same character, two takes. "
          "The judge scored this one point six — wrong jacket, wrong weapon — "
          "and sent it back with notes. The retake passed. "
          "The studio corrected itself.",
    "n10": "Every one of those decisions is on the record. The Ledger shows each take, "
           "its score, and its retake lineage — and every row links to the raw Genblaze "
           "manifest, sealed on Backblaze B2.",
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

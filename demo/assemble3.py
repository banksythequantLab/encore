"""Demo v5 — from scratch. Continuous narration drives the cut; zero dead air."""
import os
import subprocess
import sys

D = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(D)
sys.path.insert(0, ROOT)
from dotenv import load_dotenv

load_dotenv(os.path.join(ROOT, ".env"))
import composer  # noqa: E402


def run(args):
    r = subprocess.run(["ffmpeg", "-y"] + args, capture_output=True, text=True, cwd=D)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-600:])


def dur(f):
    r = subprocess.run(["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                        "-of", "csv=p=0", f], capture_output=True, text=True, cwd=D)
    return float(r.stdout.strip())


V = "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=30,format=yuv420p"
_N = [0]


def cap(line):
    _N[0] += 1
    fn = f"c3_{_N[0]}.txt"
    with open(os.path.join(D, fn), "w", encoding="utf-8") as f:
        f.write(line.replace("—", "-"))
    return (f"drawtext=fontfile=arialbd.ttf:textfile={fn}:fontcolor=white:fontsize=34:"
            f"x=64:y=h-120:box=1:boxcolor=black@0.6:boxborderw=14")


# ── narration timeline (VO drives everything) ──
GAP = 0.55           # breath between lines
CARD_OPEN = 4.2      # cinematic cold open (footage + title overlay)
END_LEN = 5.5        # footage outro with URLs
vo = [f"n{i}.wav" for i in range(1, 7)]
d = [dur(w) for w in vo]
starts = [1.3]       # n1 speaks over the cold open
for i in range(1, 6):
    starts.append(starts[i - 1] + d[i - 1] + GAP)
end_of_speech = starts[5] + d[5]

# beat i video runs from cut[i] to cut[i+1]
cuts = [CARD_OPEN] + [starts[i] - 0.25 for i in range(1, 6)] + [end_of_speech + 0.7]
seglen = [round(cuts[i + 1] - cuts[i], 2) for i in range(6)]

beats = [  # (source, ss, caption)
    ("flooded-pursuit-b29fa1f3.mp4", 13.0, "AI video today: every generation, a new stranger"),
    ("cap2_theater.mp4", 2.5, "encore.tlz.us - a live AI streaming network"),
    ("cap3_sections.mp4", 5.5, "identity anchors on Backblaze B2 - every take judged"),
    ("cap1_hero.mp4", 0.5, "serialized episodes - the story continues from B2"),
    ("submersion-ca5f894e.mp4", 12.0, "one home GPU - zero cloud costs"),
    ("cap3_sections.mp4", 12.0, "make your own shot right now - it's live"),
]
files = []
for i, (src, ss, text) in enumerate(beats):
    out = f"w{i}.mp4"
    run(["-ss", str(ss), "-t", str(seglen[i]), "-i", src,
         "-vf", V + "," + cap(text), "-an",
         "-c:v", "libx264", "-preset", "fast", "-crf", "19", out])
    files.append(out)
    print("beat", i + 1, seglen[i], "s", flush=True)

# Cold open: episode footage, fade in from black, big title overlaid.
def txt(line, fn, size, y, font="arialbd.ttf", color="white"):
    with open(os.path.join(D, fn), "w", encoding="utf-8") as f:
        f.write(line)
    return (f"drawtext=fontfile={font}:textfile={fn}:fontcolor={color}:fontsize={size}:"
            f"x=(w-text_w)/2:y={y}")


open_ov = ("drawbox=x=0:y=ih*0.60:w=iw:h=ih*0.30:color=black@0.55:t=fill," +
           txt("ENCORE", "t_o1.txt", 130, "h*0.625") + "," +
           txt("Seasons, not clips.", "t_o2.txt", 44, "h*0.625+160", "arial.ttf", "0xBFD3F2"))
run(["-ss", "3.0", "-t", str(CARD_OPEN), "-i", "submersion-ca5f894e.mp4",
     "-vf", V + ",fade=t=in:st=0:d=0.7," + open_ov, "-an",
     "-c:v", "libx264", "-preset", "fast", "-crf", "19", "c_open_n.mp4"])

end_ov = ("drawbox=x=0:y=ih*0.32:w=iw:h=ih*0.36:color=black@0.6:t=fill," +
          txt("encore.tlz.us", "t_e1.txt", 92, "h*0.35") + "," +
          txt("github.com/banksythequantLab/encore", "t_e2.txt", 38, "h*0.35+135",
              "arial.ttf", "0xBFD3F2") + "," +
          txt("seasons, not clips", "t_e3.txt", 34, "h*0.35+200", "arial.ttf", "0x8EA2C6"))
run(["-ss", "15.4", "-t", str(END_LEN), "-i", "flooded-pursuit-b29fa1f3.mp4",
     "-vf", V + "," + end_ov + f",fade=t=out:st={END_LEN - 0.9}:d=0.9", "-an",
     "-c:v", "libx264", "-preset", "fast", "-crf", "19", "c_end_n.mp4"])

order = ["c_open_n.mp4"] + files + ["c_end_n.mp4"]
with open(os.path.join(D, "cc3.txt"), "w") as f:
    for o in order:
        f.write(f"file '{o}'\n")
run(["-f", "concat", "-safe", "0", "-i", "cc3.txt", "-c", "copy", "v3only.mp4"])
total = sum(dur(o) for o in order)
print("video", round(total, 1), flush=True)

inputs, fl = [], []
for i, w in enumerate(vo):
    ms = int(starts[i] * 1000)
    inputs += ["-i", w]
    fl.append(f"[{i}:a]aresample=48000,pan=stereo|c0=c0|c1=c0,adelay={ms}|{ms}[v{i}]")
inputs += ["-stream_loop", "-1", "-i", "score.flac"]
fl.append(f"[6:a]aresample=48000,atrim=0:{total:.2f},volume=0.16,"
          f"afade=t=in:st=0:d=0.4,afade=t=out:st={total - 3.0:.2f}:d=3.0[m]")
fl.append("".join(f"[v{i}]" for i in range(6)) + "[m]amix=inputs=7:duration=longest:"
          f"dropout_transition=0,volume=2.4,atrim=0:{total:.2f}[a]")
run(inputs + ["-filter_complex", ";".join(fl), "-map", "[a]", "-c:a", "aac", "a3.m4a"])
run(["-i", "v3only.mp4", "-i", "a3.m4a", "-map", "0:v", "-map", "1:a",
     "-c", "copy", "-shortest", "encore_demo_v5.mp4"])
print("DONE encore_demo_v5.mp4", round(total, 1), "s", flush=True)

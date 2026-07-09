"""Encore demo v2 — tight pacing, title cards, lower-third context captions."""
import os
import subprocess
import sys

D = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(D)
sys.path.insert(0, ROOT)
from dotenv import load_dotenv

load_dotenv(os.path.join(ROOT, ".env"))
import composer  # noqa: E402  (branded title cards)

FONT = "C\\:/Windows/Fonts/arialbd.ttf"
FONT2 = "C\\:/Windows/Fonts/arial.ttf"


def run(args):
    r = subprocess.run(["ffmpeg", "-y"] + args, capture_output=True, text=True, cwd=D)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-700:])


def dur(f):
    r = subprocess.run(["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                        "-of", "csv=p=0", f], capture_output=True, text=True, cwd=D)
    return float(r.stdout.strip())


_CAPN = [0]


def cap(title, sub):
    """Two lower-third drawtexts via textfile= (no filter quoting at all)."""
    _CAPN[0] += 1
    fa, fb = f"capt{_CAPN[0]}a.txt", f"capt{_CAPN[0]}b.txt"
    for fn, txt in ((fa, title), (fb, sub)):
        with open(os.path.join(D, fn), "w", encoding="utf-8") as f:
            f.write(txt.replace("—", "-").replace("·", "-").replace("’", "'"))
    a = (f"drawtext=fontfile=arialbd.ttf:textfile={fa}:fontcolor=white:fontsize=40:"
         f"x=64:y=h-262:box=1:boxcolor=black@0.55:boxborderw=14")
    b = (f"drawtext=fontfile=arial.ttf:textfile={fb}:fontcolor=0xB9C8E8:fontsize=27:"
         f"x=64:y=h-200:box=1:boxcolor=black@0.55:boxborderw=12")
    return a + "," + b


V = "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=30,format=yuv420p"

# ── title cards from the episode composer (on-brand Bebas style) ──
png_open = composer._title_card(
    "ENCORE", "The network that remembers",
    "a persistent cast · a living canon on Backblaze B2",
    tick_l="a streaming network run by one GPU", tick_r="100% local · $0 cloud")
composer._still_segment(png_open, 3.2, os.path.join(D, "card_open.mp4"))
png_end = composer._title_card(
    "ENCORE", "encore.tlz.us",
    "github.com/banksythequantLab/encore — make a shot yourself, it's live",
    tick_l="every frame: one RTX 3090", tick_r="every byte: Backblaze B2")
composer._still_segment(png_end, 4.5, os.path.join(D, "card_end.mp4"))
print("cards ok", flush=True)

# ── beats: (out, src trim args, length, caption title, caption sub) ──
VO = {k: dur(k) for k in ("b1_hook.wav", "b2_vault.wav", "b3_judge.wav",
                          "b4_network.wav", "b5_stunt.wav")}
L = {  # segment video length = VO + breathing room
    "a1": round(VO["b1_hook.wav"] * 0.55, 1), "a2": round(VO["b1_hook.wav"] * 0.45 + 1.0, 1),
    "b": round(VO["b4_network.wav"] + 1.2, 1), "c": round(VO["b2_vault.wav"] + 1.0, 1),
    "d": round(VO["b3_judge.wav"] + 1.0, 1), "e": round(VO["b5_stunt.wav"] + 4.0, 1),
}
beats = [
    ("v_a1.mp4", ["-ss", "2", "-t", str(L["a1"]), "-i", "submersion-ca5f894e.mp4"],
     "EVERY FRAME AI-GENERATED ON ONE HOME GPU", "from the live library — episode 'Submersion'"),
    ("v_a2.mp4", ["-ss", "8", "-t", str(L["a2"]), "-i", "flooded-pursuit-b29fa1f3.mp4"],
     "SAME CHARACTER. DIFFERENT EPISODE.", "Lena, identity-anchored — episode 'Flooded Pursuit'"),
    ("v_b.mp4", ["-ss", "0.5", "-t", str(L["b"]), "-i", "cap1_hero.mp4"],
     "ENCORE.TLZ.US — LIVE NOW", "the network airs itself · real premiere countdown, tonight 9PM"),
    ("v_c.mp4", ["-ss", "5.5", "-t", str(L["c"]), "-i", "cap3_sections.mp4"],
     "THE SERIES VAULT — BACKBLAZE B2", "identity anchors, SHA-256 content-addressed · why the cast returns"),
    ("v_d.mp4", ["-ss", "2.5", "-t", str(L["d"]), "-i", "cap2_theater.mp4"],
     "STREAMING FROM B2 — 'SIGNAL IN THE SHADOWS'", "written, shot, scored + postered by the network itself, today"),
    ("v_e.mp4", ["-ss", "1", "-t", str(L["e"]), "-i", "cap4_canon.mp4"],
     "LIVE OBJECT LOCK TEST — NO TRICKS", "real DeleteObjectVersion → AccessDenied · the canon survives"),
]
for out, inargs, t, s in beats:
    run(inargs + ["-vf", V + "," + cap(t, s), "-an",
                  "-c:v", "libx264", "-preset", "fast", "-crf", "19", out])
    print("beat", out, flush=True)
print("beats ok", flush=True)

# ── concat all video ──
order = ["card_open.mp4", "v_a1.mp4", "v_a2.mp4", "v_b.mp4", "v_c.mp4",
         "v_d.mp4", "v_e.mp4", "card_end.mp4"]
# cards come from the composer at episode res — normalize them too
for c in ("card_open.mp4", "card_end.mp4"):
    run(["-i", c, "-vf", V, "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "19",
         c.replace(".mp4", "_n.mp4")])
order = [o.replace("card_open.mp4", "card_open_n.mp4").replace("card_end.mp4", "card_end_n.mp4")
         for o in order]
with open(os.path.join(D, "concat2.txt"), "w") as f:
    for o in order:
        f.write(f"file '{o}'\n")
run(["-f", "concat", "-safe", "0", "-i", "concat2.txt", "-c", "copy", "video2.mp4"])
segd = [dur(o) for o in order]
total = sum(segd)
print("video ok, total", round(total, 1), flush=True)

# ── audio: VO starts at each beat's segment start (+0.3s), score throughout ──
starts = []
acc = 0.0
for o, d0 in zip(order, segd):
    starts.append(acc)
    acc += d0
# order idx: 0 card, 1 a1, 2 a2, 3 b, 4 c, 5 d, 6 e, 7 card
vo_at = [("b1_hook.wav", starts[1] + 0.3), ("b4_network.wav", starts[3] + 0.3),
         ("b2_vault.wav", starts[4] + 0.3), ("b3_judge.wav", starts[5] + 0.3),
         ("b5_stunt.wav", starts[6] + 0.3)]
inputs, fl = [], []
for i, (w, t0) in enumerate(vo_at):
    ms = int(t0 * 1000)
    inputs += ["-i", w]
    fl.append(f"[{i}:a]aresample=48000,pan=stereo|c0=c0|c1=c0,adelay={ms}|{ms}[v{i}]")
inputs += ["-stream_loop", "-1", "-i", "score.flac"]
n = len(vo_at)
fl.append(f"[{n}:a]aresample=48000,atrim=0:{total:.2f},volume=0.13,"
          f"afade=t=in:st=0:d=1.5,afade=t=out:st={total - 3.5:.2f}:d=3.5[m]")
fl.append("".join(f"[v{i}]" for i in range(n)) + f"[m]amix=inputs={n + 1}:duration=longest:"
          f"dropout_transition=0,volume=2.2,atrim=0:{total:.2f}[a]")
run(inputs + ["-filter_complex", ";".join(fl), "-map", "[a]",
              "-c:a", "aac", "-ar", "48000", "audio2.m4a"])
run(["-i", "video2.mp4", "-i", "audio2.m4a", "-map", "0:v", "-map", "1:a",
     "-c:v", "copy", "-c:a", "copy", "-shortest", "encore_demo_v2.mp4"])
print("DONE encore_demo_v2.mp4", round(total, 1), "s", flush=True)

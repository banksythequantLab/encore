"""Demo v11 — retake proof + Ledger walkthrough. Narration drives the cut.

Pattern follows assemble3.py: textfile= drawtext with LOCAL fonts, persistent
backblaze B2 badge on every frame, branded open/end cards, VO over score.flac.
"""
import os
import subprocess

D = os.path.dirname(os.path.abspath(__file__))


def run(args):
    r = subprocess.run(["ffmpeg", "-y"] + args, capture_output=True, text=True, cwd=D)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-700:])


def dur(f):
    r = subprocess.run(["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                        "-of", "csv=p=0", f], capture_output=True, text=True, cwd=D)
    return float(r.stdout.strip())


V = "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=30,format=yuv420p"

# Persistent sponsor badge, top-right on every frame: backblaze + red B2 chip.
with open(os.path.join(D, "bb1.txt"), "w") as f:
    f.write("backblaze")
with open(os.path.join(D, "bb2.txt"), "w") as f:
    f.write("B2")
BADGE = ("drawtext=fontfile=arialbd.ttf:textfile=bb1.txt:fontcolor=white:fontsize=38:"
         "x=w-330:y=46:box=1:boxcolor=black@0.45:boxborderw=10,"
         "drawtext=fontfile=arialbd.ttf:textfile=bb2.txt:fontcolor=white:fontsize=38:"
         "x=w-116:y=46:box=1:boxcolor=0xE4002B:boxborderw=10")
_N = [0]


def cap(line):
    _N[0] += 1
    fn = f"c4_{_N[0]}.txt"
    with open(os.path.join(D, fn), "w", encoding="utf-8") as f:
        f.write(line.replace("—", "-"))
    return (f"drawtext=fontfile=arialbd.ttf:textfile={fn}:fontcolor=white:fontsize=34:"
            f"x=64:y=h-120:box=1:boxcolor=black@0.6:boxborderw=14")


# ── VO durations (measured, drive nothing here but sanity-checked vs plan) ──
vo = ["n1.wav", "n3.wav", "n9.wav", "n10.wav", "n4.wav",
      "n7.wav", "n8.wav", "n5.wav", "n6.wav"]
vd = {w: dur(w) for w in vo}
for w in vo:
    print(w, round(vd[w], 2), flush=True)

# ── fixed segment lengths (video is the clock; VO starts near each seg start).
# Screen captures get long tails on purpose: the ledger JSON and the maker
# typing carry themselves and stretch the cut into the 2:10-2:35 window.
CARD_OPEN = 3.0      # reuse of v10 branded open card, trimmed
L1B = 5.5            # ditd 0-5.5: PREVIOUSLY card + first beat of scene
L2 = 17.5            # ditd 5-22.5 (n3 thesis)
L3 = 15.5            # comp_retake still (n9)
L4 = 32.0            # cap_ledger 1-33: hover, click ~11-14, JSON 14-28, return
L5 = 10.0            # ditd 16.9-26.9 (n4) - later scene, minimal overlap w/ b2
L6 = 17.0            # cap_maker 1-18: dropdown pick, typing, up to GENERATE
L7A, L7B = 9.0, 9.5  # cap_maker 18-27 (click+log) then cap_result 0-9.5
L8 = 8.4             # cap_result 9.4-17.8 tail (n5)
CARD_END = 7.0       # rebuilt end card, fade out 0.9

# (out, src, ss, seglen, caption)
beats = [
    ("x1b.mp4", "data-in-the-deep.mp4", 0.0, L1B,
     "the network whose cast comes back"),
    ("x2.mp4", "data-in-the-deep.mp4", 5.0, L2,
     "the memory lives on Backblaze B2"),
    (None, None, None, L3, None),  # b3 still handled below
    ("x4.mp4", "cap_ledger.mp4", 1.0, L4,
     "The Ledger - every take sealed as a Genblaze manifest on B2"),
    ("x5.mp4", "data-in-the-deep.mp4", 16.9, L5,
     "episode 3 - premise written from season memory on B2"),
    ("x6.mp4", "cap_maker.mp4", 1.0, L6,
     "the studio maker - live"),
]
for out, src, ss, seglen, text in beats:
    if out is None:
        # b3: retake proof — still image as video (labels burned into the png)
        c = cap("identity 0.60 rejected -> 0.85 passed - real judge scores")
        run(["-loop", "1", "-t", str(L3), "-i", "comp_retake.png",
             "-vf", V + "," + c + "," + BADGE, "-an",
             "-c:v", "libx264", "-preset", "fast", "-crf", "19", "x3.mp4"])
        print("beat x3 (retake still)", L3, "s", flush=True)
        continue
    run(["-ss", str(ss), "-t", str(seglen), "-i", src,
         "-vf", V + "," + cap(text) + "," + BADGE, "-an",
         "-c:v", "libx264", "-preset", "fast", "-crf", "19", out])
    print("beat", out, seglen, "s", flush=True)

# b7: pipeline/result — GENERATE click + progress log, then finished panels.
c7 = cap("Genblaze pipeline - every step sealed on B2")
run(["-ss", "18.0", "-t", str(L7A), "-i", "cap_maker.mp4",
     "-vf", V + "," + c7 + "," + BADGE, "-an",
     "-c:v", "libx264", "-preset", "fast", "-crf", "19", "x7a.mp4"])
run(["-ss", "0.0", "-t", str(L7B), "-i", "cap_result.mp4",
     "-vf", V + "," + c7 + "," + BADGE, "-an",
     "-c:v", "libx264", "-preset", "fast", "-crf", "19", "x7b.mp4"])
print("beat x7a/x7b", L7A + L7B, "s", flush=True)

# b8: keeps — result tail (different range than b7's 0-9.5)
run(["-ss", "9.4", "-t", str(L8), "-i", "cap_result.mp4",
     "-vf", V + "," + cap("same identity, new scene") + "," + BADGE, "-an",
     "-c:v", "libx264", "-preset", "fast", "-crf", "19", "x8.mp4"])
print("beat x8", L8, "s", flush=True)

# ── cards ──
# open: reuse v10's branded card (badge + title already burned in), first 3s
run(["-ss", "0", "-t", str(CARD_OPEN), "-i", "c_open_n.mp4",
     "-vf", V, "-an",
     "-c:v", "libx264", "-preset", "fast", "-crf", "19", "o_card4.mp4"])


# end: rebuilt at 7s (v10 card is only 5.5s; n6 needs the room) — same overlay
def txt(line, fn, size, y, font="arialbd.ttf", color="white"):
    with open(os.path.join(D, fn), "w", encoding="utf-8") as f:
        f.write(line.replace("—", "-"))
    return (f"drawtext=fontfile={font}:textfile={fn}:fontcolor={color}:fontsize={size}:"
            f"x=(w-text_w)/2:y={y}")


end_ov = ("drawbox=x=0:y=ih*0.32:w=iw:h=ih*0.36:color=black@0.6:t=fill," +
          txt("encore.tlz.us", "t4_e1.txt", 92, "h*0.35") + "," +
          txt("github.com/banksythequantLab/encore", "t4_e2.txt", 38, "h*0.35+135",
              "arial.ttf", "0xBFD3F2") + "," +
          txt("seasons, not clips — built on Backblaze B2", "t4_e3.txt", 36,
              "h*0.35+200", "arialbd.ttf", "0xFF5A6E"))
fp_dur = dur("flooded-pursuit-b29fa1f3.mp4")
end_ss = min(15.4, max(0.0, fp_dur - CARD_END - 0.3))
run(["-ss", str(end_ss), "-t", str(CARD_END), "-i", "flooded-pursuit-b29fa1f3.mp4",
     "-vf", V + "," + end_ov + "," + BADGE +
     f",fade=t=out:st={CARD_END - 0.9}:d=0.9", "-an",
     "-c:v", "libx264", "-preset", "fast", "-crf", "19", "e_card4.mp4"])
print("cards ok", flush=True)

# ── concat video ──
order = ["o_card4.mp4", "x1b.mp4", "x2.mp4", "x3.mp4", "x4.mp4", "x5.mp4",
         "x6.mp4", "x7a.mp4", "x7b.mp4", "x8.mp4", "e_card4.mp4"]
with open(os.path.join(D, "cc4.txt"), "w") as f:
    for o in order:
        f.write(f"file '{o}'\n")
run(["-f", "concat", "-safe", "0", "-i", "cc4.txt", "-c", "copy", "v4only.mp4"])
segd = [dur(o) for o in order]
total = sum(segd)
print("video ok, total", round(total, 2), flush=True)

# ── audio: VO placed at each beat's real (measured) start, score under ──
acc, starts = 0.0, []
for d0 in segd:
    starts.append(acc)
    acc += d0
# order idx: 0 card, 1 x1b, 2 x2, 3 x3, 4 x4, 5 x5, 6 x6, 7 x7a, 8 x7b, 9 x8, 10 card
vo_at = [("n1.wav", 0.5),                 # over the open card, runs into x1b
         ("n3.wav", starts[2] + 0.4), ("n9.wav", starts[3] + 0.4),
         ("n10.wav", starts[4] + 0.4), ("n4.wav", starts[5] + 0.4),
         ("n7.wav", starts[6] + 0.4), ("n8.wav", starts[7] + 0.3),
         ("n5.wav", starts[9] + 0.4), ("n6.wav", starts[10] + 0.5)]
inputs, fl = [], []
for i, (w, t0) in enumerate(vo_at):
    ms = int(t0 * 1000)
    inputs += ["-i", w]
    fl.append(f"[{i}:a]aresample=48000,pan=stereo|c0=c0|c1=c0,adelay={ms}|{ms}[v{i}]")
inputs += ["-stream_loop", "-1", "-i", "score.flac"]
n = len(vo_at)
fl.append(f"[{n}:a]aresample=48000,atrim=0:{total:.2f},volume=0.16,"
          f"afade=t=in:st=0:d=0.4,afade=t=out:st={total - 3.0:.2f}:d=3.0[m]")
fl.append("".join(f"[v{i}]" for i in range(n)) + f"[m]amix=inputs={n + 1}:duration=longest:"
          f"dropout_transition=0,volume=2.4,atrim=0:{total:.2f}[a]")
run(inputs + ["-filter_complex", ";".join(fl), "-map", "[a]", "-c:a", "aac", "a4.m4a"])
run(["-i", "v4only.mp4", "-i", "a4.m4a", "-map", "0:v", "-map", "1:a",
     "-c", "copy", "-shortest", "encore_demo_v11.mp4"])
for w, t0 in vo_at:
    print(f"  {w} @ {t0:.2f} -> {t0 + vd[w]:.2f}", flush=True)
print("DONE encore_demo_v11.mp4", round(total, 2), "s", flush=True)

"""Demo v12 -- Derek's v11 review notes, all three mandatory:
1) Kill dead air: tighten worst tails (total target 120-135s) AND make the
   score bed dynamic -- 0.16 under VO, ramping to 0.38 (0.7s ramps) during
   any VO gap longer than 2s. Verify: silencedetect -35dB/2.5s = zero hits.
2) Compact lower thirds: single line, fontsize 28, 10px box padding,
   whole band inside the bottom ~12%% of frame (~48px tall).
3) Lower thirds on the RIGHT: x = w - text_w - 48. Backblaze badge stays
   top-right; episode burn-ins sit bottom-LEFT, so bottom-right is clear.
Everything else identical to v11 (assemble4.py): beat order/footage/VO
n1,n3,n9,n10,n4,n7,n8,n5,n6; comp_retake still; open/end cards; badge.
Intermediates use NEW names (y*, *5) so v11 files are untouched.
"""
import os
import re
import subprocess

D = os.path.dirname(os.path.abspath(__file__))


def run(args):
    r = subprocess.run(["ffmpeg", "-y"] + args, capture_output=True, text=True, cwd=D)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-900:])


def dur(f):
    r = subprocess.run(["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                        "-of", "csv=p=0", f], capture_output=True, text=True, cwd=D)
    return float(r.stdout.strip())


def peak_db(f):
    r = subprocess.run(["ffmpeg", "-i", f, "-af", "volumedetect", "-f", "null", "-"],
                       capture_output=True, text=True, cwd=D)
    m = re.search(r"max_volume: (-?[0-9.]+) dB", r.stderr)
    return float(m.group(1)) if m else -6.0


V = ("scale=1920:1080:force_original_aspect_ratio=decrease,"
     "pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=30,format=yuv420p")

# Persistent sponsor badge, top-right on every frame (unchanged from v11).
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
    # Derek notes 2+3: compact single-line band, bottom-RIGHT.
    # Box spans y=h-102..h-54 (48px tall, inside bottom 12%), right edge w-38.
    _N[0] += 1
    fn = f"c5_{_N[0]}.txt"
    with open(os.path.join(D, fn), "w", encoding="utf-8") as f:
        f.write(line.replace("—", "-"))
    return (f"drawtext=fontfile=arialbd.ttf:textfile={fn}:fontcolor=white:fontsize=28:"
            f"x=w-text_w-48:y=h-92:box=1:boxcolor=black@0.6:boxborderw=10")


# ── VO durations drive the cut (Derek note 1a: tails = VO + 2-4s) ──
vo = ["n1.wav", "n3.wav", "n9.wav", "n10.wav", "n4.wav",
      "n7.wav", "n8.wav", "n5.wav", "n6.wav"]
vd = {w: dur(w) for w in vo}
for w in vo:
    print(w, round(vd[w], 2), flush=True)

VOFF = 0.4                      # VO start offset inside its beat
CARD_OPEN = 3.0
P = {
    "X1B": max(5.5, vd["n1.wav"] + 0.5 + 1.5 - CARD_OPEN),  # previously card
    "L2": vd["n3.wav"] + VOFF + 3.0,      # thesis over ditd scene
    "L3": vd["n9.wav"] + VOFF + 3.0,      # comp_retake still
    "L4": 22.0,                           # ledger: click ~10-13s in, JSON to end
    "L5": min(vd["n4.wav"] + VOFF + 3.0, 10.0),  # serial beat; src ends at 27s
    "L6": vd["n7.wav"] + VOFF + 3.0,      # maker form (was 17.0 in v11)
    "L7": vd["n8.wav"] + 0.3 + 3.0,       # pipeline: y7a(6.0)+y7b (was 18.5)
    "L8": min(vd["n5.wav"] + VOFF + 3.0, 8.4),  # result tail (src file limit)
    "CARD_END": vd["n6.wav"] + 0.5 + 2.5,
}


def total_len():
    return CARD_OPEN + sum(P.values())


# Fit into 122-132 (Derek target 120-135): stretch/shrink within hard caps.
stretch = [("L4", 24.0), ("X1B", 8.5),
           ("L2", min(vd["n3.wav"] + VOFF + 5.0, 21.5)),
           ("L3", vd["n9.wav"] + VOFF + 5.0),
           ("CARD_END", vd["n6.wav"] + 0.5 + 4.0),
           ("L5", min(vd["n4.wav"] + VOFF + 4.0, 10.0)),
           ("L6", vd["n7.wav"] + VOFF + 4.0),
           ("L7", vd["n8.wav"] + 0.3 + 4.0)]
shrink = [("L4", 20.0),
          ("L2", vd["n3.wav"] + VOFF + 2.0), ("L3", vd["n9.wav"] + VOFF + 2.0),
          ("L5", vd["n4.wav"] + VOFF + 2.0), ("L6", vd["n7.wav"] + VOFF + 2.0),
          ("L7", vd["n8.wav"] + 0.3 + 2.0),
          ("L8", min(vd["n5.wav"] + VOFF + 2.0, 8.4)),
          ("CARD_END", vd["n6.wav"] + 0.5 + 1.6)]
for key, cap_v in stretch:
    need = 122.0 - total_len()
    if need <= 0:
        break
    if cap_v > P[key]:
        P[key] = min(cap_v, P[key] + need)
for key, floor_v in shrink:
    over = total_len() - 132.0
    if over <= 0:
        break
    if floor_v < P[key]:
        P[key] = max(floor_v, P[key] - over)
print("plan:", {k: round(v, 2) for k, v in P.items()},
      "total", round(total_len(), 2), flush=True)

# ── beats (same order/footage/captions as v11; new lengths + caption style) ──
beats = [
    ("y1b.mp4", "data-in-the-deep.mp4", 0.0, P["X1B"],
     "the network whose cast comes back"),
    ("y2.mp4", "data-in-the-deep.mp4", 5.0, P["L2"],
     "the memory lives on Backblaze B2"),
    (None, None, None, P["L3"], None),  # b3 retake still handled below
    ("y4.mp4", "cap_ledger.mp4", 1.0, P["L4"],
     "The Ledger - every take sealed as a Genblaze manifest on B2"),
    ("y5.mp4", "data-in-the-deep.mp4", 16.9, P["L5"],
     "episode 3 - premise written from season memory on B2"),
    ("y6.mp4", "cap_maker.mp4", 1.0, P["L6"],
     "the studio maker - live"),
]
for out, src, ss, seglen, text in beats:
    if out is None:
        c = cap("identity 0.60 rejected -> 0.85 passed - real judge scores")
        run(["-loop", "1", "-t", str(seglen), "-i", "comp_retake.png",
             "-vf", V + "," + c + "," + BADGE, "-an",
             "-c:v", "libx264", "-preset", "fast", "-crf", "19", "y3.mp4"])
        print("beat y3 (retake still)", round(seglen, 2), "s", flush=True)
        continue
    run(["-ss", str(ss), "-t", str(seglen), "-i", src,
         "-vf", V + "," + cap(text) + "," + BADGE, "-an",
         "-c:v", "libx264", "-preset", "fast", "-crf", "19", out])
    print("beat", out, round(seglen, 2), "s", flush=True)

# b7: GENERATE click + progress log, then finished panels (n8 spans both).
L7A = 6.0
c7 = cap("Genblaze pipeline - every step sealed on B2")
run(["-ss", "18.0", "-t", str(L7A), "-i", "cap_maker.mp4",
     "-vf", V + "," + c7 + "," + BADGE, "-an",
     "-c:v", "libx264", "-preset", "fast", "-crf", "19", "y7a.mp4"])
run(["-ss", "0.0", "-t", str(P["L7"] - L7A), "-i", "cap_result.mp4",
     "-vf", V + "," + c7 + "," + BADGE, "-an",
     "-c:v", "libx264", "-preset", "fast", "-crf", "19", "y7b.mp4"])
# b8: keeps -- result tail (different range than b7's head)
run(["-ss", "9.4", "-t", str(P["L8"]), "-i", "cap_result.mp4",
     "-vf", V + "," + cap("same identity, new scene") + "," + BADGE, "-an",
     "-c:v", "libx264", "-preset", "fast", "-crf", "19", "y8.mp4"])
print("beats y7a/y7b/y8 ok", flush=True)

# ── cards (v11 pattern; end card length now derived from n6) ──
run(["-ss", "0", "-t", str(CARD_OPEN), "-i", "c_open_n.mp4",
     "-vf", V, "-an",
     "-c:v", "libx264", "-preset", "fast", "-crf", "19", "o_card5.mp4"])


def txt(line, fn, size, y, font="arialbd.ttf", color="white"):
    with open(os.path.join(D, fn), "w", encoding="utf-8") as f:
        f.write(line.replace("—", "-"))
    return (f"drawtext=fontfile={font}:textfile={fn}:fontcolor={color}:fontsize={size}:"
            f"x=(w-text_w)/2:y={y}")


CARD_END = P["CARD_END"]
end_ov = ("drawbox=x=0:y=ih*0.32:w=iw:h=ih*0.36:color=black@0.6:t=fill," +
          txt("encore.tlz.us", "t5_e1.txt", 92, "h*0.35") + "," +
          txt("github.com/banksythequantLab/encore", "t5_e2.txt", 38, "h*0.35+135",
              "arial.ttf", "0xBFD3F2") + "," +
          txt("seasons, not clips — built on Backblaze B2", "t5_e3.txt", 36,
              "h*0.35+200", "arialbd.ttf", "0xFF5A6E"))
fp_dur = dur("flooded-pursuit-b29fa1f3.mp4")
end_ss = min(15.4, max(0.0, fp_dur - CARD_END - 0.3))
run(["-ss", str(end_ss), "-t", str(CARD_END), "-i", "flooded-pursuit-b29fa1f3.mp4",
     "-vf", V + "," + end_ov + "," + BADGE +
     f",fade=t=out:st={CARD_END - 0.9:.2f}:d=0.9", "-an",
     "-c:v", "libx264", "-preset", "fast", "-crf", "19", "e_card5.mp4"])
print("cards ok", flush=True)

# ── concat video ──
order = ["o_card5.mp4", "y1b.mp4", "y2.mp4", "y3.mp4", "y4.mp4", "y5.mp4",
         "y6.mp4", "y7a.mp4", "y7b.mp4", "y8.mp4", "e_card5.mp4"]
with open(os.path.join(D, "cc5.txt"), "w") as f:
    for o in order:
        f.write(f"file '{o}'\n")
run(["-f", "concat", "-safe", "0", "-i", "cc5.txt", "-c", "copy", "v5only.mp4"])
segd = [dur(o) for o in order]
total = sum(segd)
acc, starts = 0.0, []
for d0 in segd:
    starts.append(acc)
    acc += d0
print("video ok, total", round(total, 2), flush=True)

# ── audio: VO at measured beat starts; DYNAMIC score bed (Derek note 1b) ──
# order idx: 0 card, 1 y1b, 2 y2, 3 y3, 4 y4, 5 y5, 6 y6, 7 y7a, 8 y7b,
#            9 y8, 10 e_card
vo_at = [("n1.wav", 0.5),
         ("n3.wav", starts[2] + VOFF), ("n9.wav", starts[3] + VOFF),
         ("n10.wav", starts[4] + VOFF), ("n4.wav", starts[5] + VOFF),
         ("n7.wav", starts[6] + VOFF), ("n8.wav", starts[7] + 0.3),
         ("n5.wav", starts[9] + VOFF), ("n6.wav", starts[10] + 0.5)]

# Bed sits at 0.16 under VO; in any VO gap > 2s it ramps to 0.38 over 0.7s
# and back down 0.7s before the next VO. Gaps from real VO starts/durations.
BASE, GAPV, RAMP = 0.16, 0.38, 0.7
iv = [(t0, t0 + vd[w]) for w, t0 in vo_at]
gaps, prev = [], 0.0
for s, e in iv:
    if s - prev > 2.0:
        gaps.append((prev, s))
    prev = max(prev, e)
if total - prev > 2.0:
    gaps.append((prev, total))
terms = "".join(
    f"+{GAPV - BASE:.2f}*min(max((t-{s:.2f})/{RAMP},0),1)"
    f"*min(max(({e:.2f}-t)/{RAMP},0),1)"
    for s, e in gaps)
expr = f"{BASE}{terms}"
print("gaps:", [(round(s, 2), round(e, 2)) for s, e in gaps], flush=True)

# normalize=0 mix with explicit levels. v11 used amix auto-normalize + x2.4,
# so the bed level drifted with active-input count -- half the dead-air bug.
# VO peak-normalized to -1.5dB, score to -1dB, limiter for safety.
inputs, fl = [], []
for i, (w, t0) in enumerate(vo_at):
    g = min(10 ** ((-1.5 - peak_db(w)) / 20.0), 3.0)
    ms = int(t0 * 1000)
    inputs += ["-i", w]
    fl.append(f"[{i}:a]aresample=48000,pan=stereo|c0=c0|c1=c0,"
              f"volume={g:.3f},adelay={ms}|{ms}[v{i}]")
inputs += ["-stream_loop", "-1", "-i", "score.flac"]
n = len(vo_at)
gm = min(10 ** ((-1.0 - peak_db("score.flac")) / 20.0), 4.0)
fl.append(f"[{n}:a]aresample=48000,atrim=0:{total:.2f},volume={gm:.3f},"
          f"volume=volume='{expr}':eval=frame,"
          f"afade=t=in:st=0:d=0.4,afade=t=out:st={total - 3.0:.2f}:d=3.0[m]")
fl.append("".join(f"[v{i}]" for i in range(n)) +
          f"[m]amix=inputs={n + 1}:duration=longest:dropout_transition=0:"
          f"normalize=0,alimiter=limit=0.95:level=false,atrim=0:{total:.2f}[a]")
run(inputs + ["-filter_complex", ";".join(fl), "-map", "[a]", "-c:a", "aac", "a5.m4a"])
run(["-i", "v5only.mp4", "-i", "a5.m4a", "-map", "0:v", "-map", "1:a",
     "-c", "copy", "-shortest", "encore_demo_v12.mp4"])
for w, t0 in vo_at:
    print(f"  {w} @ {t0:.2f} -> {t0 + vd[w]:.2f}", flush=True)
print("segments:", [(o, round(d0, 2)) for o, d0 in zip(order, segd)], flush=True)
print("DONE encore_demo_v12.mp4", round(total, 2), "s", flush=True)

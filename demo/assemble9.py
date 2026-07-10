"""Demo v16 -- Derek's v15 notes: kill face-swap span, calm 7s explainer open.

1) FACE SWAP KILLED. v15's thesis beat (z2) used data-in-the-deep ss=5.0
   for ~14s, crossing the i2v chain-join drift at src ~10-17s (she walks
   out and a different long-haired character walks back in ~13-14s;
   verified on 1-fps contact sheets). Every episode-footage span in this
   cut was frame-checked at <=1.5-2s intervals for identity consistency:
     - previously card: data-in-the-deep 0.00-3.95  (cards only)
     - thesis shot A:   submersion       3.20-7.95  (Lena, rainy exterior)
     - thesis shot B:   submersion      14.50-20.92 (Lena, tunnel scene)
     - serial beat:     data-in-the-deep 16.90-25.97 (Final Shot + card)
     - end underlay:    flooded-pursuit 15.40-21.60 (rooftop silhouette)
   ditd ~10-17 and submersion ~11.5-14.5 are drift zones -> not used.
   n3 (13.12s) needs an 11.2s thesis; no source has a clean span that
   long, so the thesis is TWO verified shots cut on an n3 pause
   (7.27-7.73s) -- a deliberate scene cut, not an in-shot swap.

2) CALM OPEN. Beat 1: one solid explainer card (dark navy, badge
   top-right, big ENCORE + three lines), held C1=2.0+n1+0.25 (~7.6s,
   >=7.0 spec); no VO for the first 2.0s, n1 starts at t=2.0 and ends
   0.25s before the card ends. Beat 2: cut to Previously-on card
   (ditd 0-3.95, ~4s); n3 starts 1.2s after the cut; the thesis footage
   change lands at n3 offset 2.75, inside the measured 2.58-2.90 pause
   (not mid-word). Only ONE cut in the first 11s (at ~7.6s; next 11.6s).

Everything else identical to v15 (assemble8.py): beats n9,n10,n4,n7,n8,
n5,n6, captions bottom-right, badge, gaps ~1.2s (<=1.5), NARRATION-ONLY
audio chain verbatim. Acceptance re-run: 0.5s-window RMS on the final
mux (mono 8k): no stretch below -35 dB longer than 2.0s except the
<=2.5s end tail; speech windows -10..-14 dB; no clipping.
"""
import math
import os
import re
import struct
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


def mean_db(f):
    r = subprocess.run(["ffmpeg", "-i", f, "-af", "volumedetect", "-f", "null", "-"],
                       capture_output=True, text=True, cwd=D)
    m = re.search(r"mean_volume: (-?[0-9.]+) dB", r.stderr)
    return float(m.group(1))


def peak_db(f):
    r = subprocess.run(["ffmpeg", "-i", f, "-af", "volumedetect", "-f", "null", "-"],
                       capture_output=True, text=True, cwd=D)
    m = re.search(r"max_volume: (-?[0-9.]+) dB", r.stderr)
    return float(m.group(1)) if m else -6.0


V = ("scale=1920:1080:force_original_aspect_ratio=decrease,"
     "pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=30,format=yuv420p")

# Persistent sponsor badge, top-right on every frame (identical to v15).
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
    # Compact single-line band, bottom-RIGHT (Derek v11 notes 2+3, kept).
    _N[0] += 1
    fn = f"c9_{_N[0]}.txt"
    with open(os.path.join(D, fn), "w", encoding="utf-8") as f:
        f.write(line.replace("—", "-"))
    return (f"drawtext=fontfile=arialbd.ttf:textfile={fn}:fontcolor=white:fontsize=28:"
            f"x=w-text_w-48:y=h-92:box=1:boxcolor=black@0.6:boxborderw=10")


def txt(line, fn, size, y, font="arialbd.ttf", color="white"):
    with open(os.path.join(D, fn), "w", encoding="utf-8") as f:
        f.write(line.replace("—", "-"))
    return (f"drawtext=fontfile={font}:textfile={fn}:fontcolor={color}:fontsize={size}:"
            f"x=(w-text_w)/2:y={y}")


# ── VO durations drive the whole cut ──
vo = ["n1.wav", "n3.wav", "n9.wav", "n10.wav", "n4.wav",
      "n7.wav", "n8.wav", "n5.wav", "n6.wav"]
vd = {w: dur(w) for w in vo}
for w in vo:
    print(w, round(vd[w], 2), flush=True)

GAP = 1.2            # target silence between VO clips (spec 0.8-1.5s)
VOFF = 0.4           # VO start offset inside its beat
# Beat 1: explainer card. No VO for 2.0s, n1 @ 2.0, ends 0.25s pre-cut.
CARD_OPEN = 2.0 + vd["n1.wav"] + 0.25
assert CARD_OPEN >= 7.0, "explainer card must hold >=7.0s"
# n3 pause map (silencedetect -30dB/0.12s): 2.58-2.90 and 7.27-7.73.
N3_CUT1 = 2.75       # previously->thesis cut lands in this pause
N3_CUT2 = 7.50       # thesis shot A->B cut lands in this pause
P = {
    "P2A": GAP + N3_CUT1,                       # previously card ~3.95s
    "P2B": N3_CUT2 - N3_CUT1,                   # thesis shot A 4.75s
    # gap after n3 = 1.2 -> total thesis footage = n3 + 2.0 - P2A
    "P2C": vd["n3.wav"] + 2.0 - (GAP + N3_CUT1) - (N3_CUT2 - N3_CUT1),
    "L3": vd["n9.wav"] + GAP,
    "L4": vd["n10.wav"] + GAP,          # ledger; ss=5.0 as v15
    "L5": vd["n4.wav"] + GAP,           # ditd 16.9 (src ends 27.0)
    "L6": vd["n7.wav"] + GAP,           # maker form
    "L7": vd["n8.wav"] + GAP - 0.1,     # n8 @ +0.3, next VO @ +0.4
    "L8": min(vd["n5.wav"] + GAP - 0.1, 8.4),   # cap_result src limit
    "CARD_END": vd["n6.wav"] + 0.5 + 1.5,       # n6 @ +0.5, hold 1.5s
}
SS_2B, SS_2C = 3.20, 14.50      # submersion spans, face-checked
assert SS_2B + P["P2B"] <= 11.5 + 0.05, "thesis A leaves clean zone"
assert SS_2C + P["P2C"] <= 21.9 + 0.05, "thesis B leaves clean zone"
assert 16.9 + P["L5"] <= dur("data-in-the-deep.mp4") + 0.05, "L5 over src"
assert P["P2A"] <= 4.0 + 0.05, "previously card must stay on ditd 0-4"
total_plan = CARD_OPEN + sum(P.values())
print("plan:", {k: round(v, 2) for k, v in P.items()},
      "card", round(CARD_OPEN, 2), "total", round(total_plan, 2), flush=True)
SS_LEDGER = 5.0

# ── beat 1: explainer card (dark navy, house style, badge) ──
card_ov = (txt("ENCORE", "t9_o1.txt", 132, "h*0.26") + "," +
           txt("An AI streaming network with a persistent cast.",
               "t9_o2.txt", 42, "h*0.47", "arial.ttf", "0xD7E1F5") + "," +
           txt("Episodes are planned, shot, judged, and archived automatically.",
               "t9_o3.txt", 42, "h*0.47+72", "arial.ttf", "0xD7E1F5") + "," +
           txt("The cast and the season's story live durably on Backblaze B2.",
               "t9_o4.txt", 42, "h*0.47+144", "arial.ttf", "0xBFD3F2"))
run(["-f", "lavfi", "-i",
     f"color=c=0x0B1020:s=1920x1080:r=30:d={CARD_OPEN:.3f}",
     "-vf", card_ov + "," + BADGE, "-an",
     "-c:v", "libx264", "-preset", "fast", "-crf", "19", "o_card9.mp4"])
print("explainer card", round(CARD_OPEN, 2), "s", flush=True)

# ── render beats (q* names; v15 z*/y*/x* files untouched) ──
beats = [
    ("q2a.mp4", "data-in-the-deep.mp4", 0.0, P["P2A"],
     "the network whose cast comes back"),
    ("q2b.mp4", "submersion-ca5f894e.mp4", SS_2B, P["P2B"],
     "the memory lives on Backblaze B2"),
    ("q2c.mp4", "submersion-ca5f894e.mp4", SS_2C, P["P2C"],
     "the memory lives on Backblaze B2"),
    (None, None, None, P["L3"], None),  # retake still handled below
    ("q4.mp4", "cap_ledger.mp4", SS_LEDGER, P["L4"],
     "The Ledger - every take sealed as a Genblaze manifest on B2"),
    ("q5.mp4", "data-in-the-deep.mp4", 16.9, P["L5"],
     "episode 3 - premise written from season memory on B2"),
    ("q6.mp4", "cap_maker.mp4", 1.0, P["L6"],
     "the studio maker - live"),
]
for out, src, ss, seglen, text in beats:
    if out is None:
        c = cap("identity 0.60 rejected -> 0.85 passed - real judge scores")
        run(["-loop", "1", "-t", f"{seglen:.3f}", "-i", "comp_retake.png",
             "-vf", V + "," + c + "," + BADGE, "-an",
             "-c:v", "libx264", "-preset", "fast", "-crf", "19", "q3.mp4"])
        print("beat q3 (retake still)", round(seglen, 2), "s", flush=True)
        continue
    run(["-ss", f"{ss:.3f}", "-t", f"{seglen:.3f}", "-i", src,
         "-vf", V + "," + cap(text) + "," + BADGE, "-an",
         "-c:v", "libx264", "-preset", "fast", "-crf", "19", out])
    print("beat", out, round(seglen, 2), "s", flush=True)

# pipeline: GENERATE click + progress log head, then finished panels
L7A = 6.0
c7 = cap("Genblaze pipeline - every step sealed on B2")
run(["-ss", "18.0", "-t", f"{L7A:.3f}", "-i", "cap_maker.mp4",
     "-vf", V + "," + c7 + "," + BADGE, "-an",
     "-c:v", "libx264", "-preset", "fast", "-crf", "19", "q7a.mp4"])
run(["-ss", "0.0", "-t", f"{P['L7'] - L7A:.3f}", "-i", "cap_result.mp4",
     "-vf", V + "," + c7 + "," + BADGE, "-an",
     "-c:v", "libx264", "-preset", "fast", "-crf", "19", "q7b.mp4"])
run(["-ss", "9.4", "-t", f"{P['L8']:.3f}", "-i", "cap_result.mp4",
     "-vf", V + "," + cap("same identity, new scene") + "," + BADGE, "-an",
     "-c:v", "libx264", "-preset", "fast", "-crf", "19", "q8.mp4"])
print("beats q7a/q7b/q8 ok", flush=True)

# ── end card (identical to v15; flooded-pursuit 15.4-21.6 face-checked) ──
CARD_END = P["CARD_END"]
end_ov = ("drawbox=x=0:y=ih*0.32:w=iw:h=ih*0.36:color=black@0.6:t=fill," +
          txt("encore.tlz.us", "t9_e1.txt", 92, "h*0.35") + "," +
          txt("github.com/banksythequantLab/encore", "t9_e2.txt", 38, "h*0.35+135",
              "arial.ttf", "0xBFD3F2") + "," +
          txt("seasons, not clips — built on Backblaze B2", "t9_e3.txt", 36,
              "h*0.35+200", "arialbd.ttf", "0xFF5A6E"))
fp_dur = dur("flooded-pursuit-b29fa1f3.mp4")
end_ss = min(15.4, max(0.0, fp_dur - CARD_END - 0.3))
run(["-ss", f"{end_ss:.3f}", "-t", f"{CARD_END:.3f}",
     "-i", "flooded-pursuit-b29fa1f3.mp4",
     "-vf", V + "," + end_ov + "," + BADGE +
     f",fade=t=out:st={CARD_END - 0.9:.2f}:d=0.9", "-an",
     "-c:v", "libx264", "-preset", "fast", "-crf", "19", "e_card9.mp4"])
print("cards ok", flush=True)

# ── concat video ──
order = ["o_card9.mp4", "q2a.mp4", "q2b.mp4", "q2c.mp4", "q3.mp4", "q4.mp4",
         "q5.mp4", "q6.mp4", "q7a.mp4", "q7b.mp4", "q8.mp4", "e_card9.mp4"]
with open(os.path.join(D, "cc9.txt"), "w") as f:
    for o in order:
        f.write(f"file '{o}'\n")
run(["-f", "concat", "-safe", "0", "-i", "cc9.txt", "-c", "copy", "v9only.mp4"])
segd = [dur(o) for o in order]
total = sum(segd)
acc, starts = 0.0, []
for d0 in segd:
    starts.append(acc)
    acc += d0
print("video ok, total", round(total, 2), flush=True)
# first-11s rhythm: exactly one cut (card->previously) before t=11
cuts_11 = [s for s in starts[1:] if s < 11.0]
assert len(cuts_11) == 1, f"first-11s rhythm broken: cuts at {cuts_11}"

# ── VO placement at MEASURED beat starts (same scheme as v15) ──
# order idx: 0 card, 1 q2a, 2 q2b, 3 q2c, 4 q3, 5 q4, 6 q5, 7 q6,
#            8 q7a, 9 q7b, 10 q8, 11 e_card
vo_at = [("n1.wav", 2.0),
         ("n3.wav", starts[1] + GAP), ("n9.wav", starts[4] + VOFF),
         ("n10.wav", starts[5] + VOFF), ("n4.wav", starts[6] + VOFF),
         ("n7.wav", starts[7] + VOFF), ("n8.wav", starts[8] + 0.3),
         ("n5.wav", starts[10] + VOFF), ("n6.wav", starts[11] + 0.5)]
prev_end = None
for w, t0 in vo_at:
    g = None if prev_end is None else t0 - prev_end
    print(f"  {w} @ {t0:.2f} -> {t0 + vd[w]:.2f}"
          + (f"  (gap {g:.2f}s)" if g is not None else ""), flush=True)
    if g is not None:
        assert 0.7 <= g <= 1.6, f"gap {g:.2f}s out of spec before {w}"
    prev_end = t0 + vd[w]
print(f"  tail after n6: {total - prev_end:.2f}s", flush=True)
# thesis cuts land inside measured n3 pauses (2.58-2.90, 7.27-7.73)
n3_t0 = vo_at[1][1]
for cut, lo, hi in ((starts[2], 2.58, 2.90), (starts[3], 7.27, 7.73)):
    off = cut - n3_t0
    assert lo - 0.06 <= off <= hi + 0.06, f"cut at n3 offset {off:.2f} mid-word"
    print(f"  cut @ {cut:.2f} = n3 offset {off:.2f} (pause {lo}-{hi})", flush=True)

# ── build audio: NARRATION ONLY, v15 VO chain verbatim (no bed input) ──
VO_TARGET = -10.0
inputs, fl = [], []
for i, (w, t0) in enumerate(vo_at):
    cw = f"_vo9_{i}.wav"
    run(["-i", w, "-af",
         "acompressor=threshold=-24dB:ratio=8:attack=2:release=100",
         "-ar", "48000", "-ac", "1", cw])
    g = min(10 ** ((VO_TARGET - mean_db(cw)) / 20.0), 30.0)
    ms = int(t0 * 1000)
    inputs += ["-i", cw]
    fl.append(f"[{i}:a]pan=stereo|c0=c0|c1=c0,"
              f"volume={g:.3f},alimiter=limit=0.891:level=false,"
              f"adelay={ms}|{ms}[v{i}]")
    print(f"  {w} @ {t0:.2f}s comp mean {mean_db(cw):.1f} dB, "
          f"makeup x{g:.2f} ({20*math.log10(g):+.1f} dB), "
          f"peak out {peak_db(cw) + 20*math.log10(g):+.1f} dB", flush=True)
n = len(vo_at)
fl.append("".join(f"[v{i}]" for i in range(n)) +
          f"amix=inputs={n}:duration=longest:dropout_transition=0:"
          f"normalize=0,alimiter=limit=0.891:level=false,"
          f"apad,atrim=0:{total:.2f}[a]")
run(inputs + ["-filter_complex", ";".join(fl), "-map", "[a]",
              "-c:a", "aac", "-b:a", "256k", "a9.m4a"])
run(["-i", "v9only.mp4", "-i", "a9.m4a", "-map", "0:v", "-map", "1:a",
     "-c", "copy", "-shortest", "encore_demo_v16.mp4"])
print("segments:", [(o, round(d0, 2)) for o, d0 in zip(order, segd)], flush=True)
print("DONE encore_demo_v16.mp4", round(dur("encore_demo_v16.mp4"), 2), "s",
      flush=True)

# ── acceptance: 0.5s-window RMS (mono 8k) on the final mux ──
raw = os.path.join(D, "_acc9.pcm")
run(["-i", "encore_demo_v16.mp4", "-ac", "1", "-ar", "8000",
     "-f", "s16le", "_acc9.pcm"])
data = open(raw, "rb").read()
ns = len(data) // 2
samp = struct.unpack(f"<{ns}h", data[:ns * 2])
W = 4000  # 0.5s @ 8k
wins = []
for i in range(0, ns - W + 1, W):
    s2 = sum(x * x for x in samp[i:i + W]) / W
    wins.append(20 * math.log10(max(math.sqrt(s2), 1e-9) / 32768.0))
runs, cur = [], 0
for dbv in wins:
    if dbv < -35.0:
        cur += 1
    else:
        if cur:
            runs.append(cur)
        cur = 0
if cur:
    runs.append((cur, "tail"))
interior = [r for r in runs if not isinstance(r, tuple)]
tail = next((r[0] for r in runs if isinstance(r, tuple)), 0)
worst = max(interior) * 0.5 if interior else 0.0
print(f"silence: worst interior {worst:.1f}s, end tail {tail * 0.5:.1f}s",
      flush=True)
assert worst <= 2.0, f"interior silence {worst:.1f}s > 2.0s"
assert tail * 0.5 <= 2.5, f"end tail {tail * 0.5:.1f}s > 2.5s"
for w, t0 in vo_at:
    i0 = int((t0 + 0.4) / 0.5)
    i1 = int((t0 + vd[w] - 0.4) / 0.5)
    lv = sorted(wins[i0:i1 + 1])
    med = lv[len(lv) // 2]
    print(f"  speech {w}: median window {med:.1f} dB", flush=True)
    assert -14.0 <= med <= -10.0, f"{w} speech level {med:.1f} out of range"
pk = peak_db("encore_demo_v16.mp4")
print(f"peak {pk:+.1f} dB", flush=True)
assert pk < 0.0, "clipping"
os.remove(raw)
print("ACCEPTANCE PASS", flush=True)

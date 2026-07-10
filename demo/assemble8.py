"""Demo v15 -- Derek's v14 notes: NARRATION ONLY, kill remaining dead air.

1) NO music bed. All ACE-Step beds are DC flatline (see assemble7.py
   docstring); rather than ship the fallback loop, Derek cut music
   entirely. The mix is the nine VO clips and nothing else.
2) With no bed, any VO-free stretch is pure silence, so the timeline is
   re-fit: every gap between one VO ending and the next starting is
   ~1.2s (spec 0.8-1.5s). Each beat's footage = its VO length + ~1.2s.
   Video segments are RE-RENDERED (z*, *8 names; v12/v14 files untouched).

VO chain identical to assemble7.py (v14): per-clip crest compressor
(acompressor -24dB/8:1), measured makeup gain to VO_TARGET=-10 dB mean,
-1 dB limiter per clip and on the bus. No bed input, no bed fades.

Special cases (per Derek):
- open card 3.0s, n1 starts 0.5s in and spills into z1b;
- ledger beat: cap_ledger ss=5.0 so the manifest click (src ~11-14s)
  lands mid-VO (beat t 6.0-9.0 of a 14.2s VO) and the manifest JSON
  (src 14-28s) is on screen from beat t 9.0 through the beat end;
- pipeline beat keeps the 6.0s GENERATE click+log head (cap_maker 18-24)
  then cap_result from 0.0 for the remainder;
- end card: n6 ends, ~1.5s hold, 0.9s fade out.

Acceptance (0.5s-window RMS on the final mux, mono 8k): no stretch
below -35 dB longer than 2.0s anywhere except the <=2.5s end tail;
speech windows -10..-14 dB; no clipping.
"""
import math
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

# Persistent sponsor badge, top-right on every frame (identical to v12/v14).
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
    fn = f"c8_{_N[0]}.txt"
    with open(os.path.join(D, fn), "w", encoding="utf-8") as f:
        f.write(line.replace("—", "-"))
    return (f"drawtext=fontfile=arialbd.ttf:textfile={fn}:fontcolor=white:fontsize=28:"
            f"x=w-text_w-48:y=h-92:box=1:boxcolor=black@0.6:boxborderw=10")


# ── VO durations drive the whole cut ──
vo = ["n1.wav", "n3.wav", "n9.wav", "n10.wav", "n4.wav",
      "n7.wav", "n8.wav", "n5.wav", "n6.wav"]
vd = {w: dur(w) for w in vo}
for w in vo:
    print(w, round(vd[w], 2), flush=True)

GAP = 1.2            # target silence between VO clips (spec 0.8-1.5s)
VOFF = 0.4           # VO start offset inside its beat
CARD_OPEN = 3.0
P = {
    # n1 @ 0.5 abs; n3 @ CARD_OPEN+Z1B+VOFF; gap = that - (0.5+n1) = GAP
    "Z1B": 0.5 + vd["n1.wav"] + GAP - CARD_OPEN - VOFF,
    "L2": vd["n3.wav"] + GAP,
    "L3": vd["n9.wav"] + GAP,
    "L4": vd["n10.wav"] + GAP,          # ledger; ss picked below
    "L5": vd["n4.wav"] + GAP,           # ditd 16.9 (src ends 27.0)
    "L6": vd["n7.wav"] + GAP,           # maker form (~5.3s, reads fine)
    "L7": vd["n8.wav"] + GAP - 0.1,     # n8 @ +0.3, next VO @ +0.4
    "L8": min(vd["n5.wav"] + GAP - 0.1, 8.4),   # cap_result src limit
    "CARD_END": vd["n6.wav"] + 0.5 + 1.5,       # n6 @ +0.5, hold 1.5s
}
assert 16.9 + P["L5"] <= dur("data-in-the-deep.mp4") + 0.05, "L5 over src"
assert 5.0 + P["L2"] <= dur("data-in-the-deep.mp4") + 0.05, "L2 over src"
total_plan = CARD_OPEN + sum(P.values())
print("plan:", {k: round(v, 2) for k, v in P.items()},
      "total", round(total_plan, 2), flush=True)

# Ledger ss: click at src 11-14 must land mid-VO (VO spans beat 0.4-14.2),
# JSON (src 14-28) on screen as the VO ends. ss=5.0: click at beat 6.0-9.0,
# JSON from beat 9.0; VO ends at src 19.2 and beat ends at src ~20.0.
SS_LEDGER = 5.0

# ── render beats (z* names; y*/x* files untouched) ──
beats = [
    ("z1b.mp4", "data-in-the-deep.mp4", 0.0, P["Z1B"],
     "the network whose cast comes back"),
    ("z2.mp4", "data-in-the-deep.mp4", 5.0, P["L2"],
     "the memory lives on Backblaze B2"),
    (None, None, None, P["L3"], None),  # retake still handled below
    ("z4.mp4", "cap_ledger.mp4", SS_LEDGER, P["L4"],
     "The Ledger - every take sealed as a Genblaze manifest on B2"),
    ("z5.mp4", "data-in-the-deep.mp4", 16.9, P["L5"],
     "episode 3 - premise written from season memory on B2"),
    ("z6.mp4", "cap_maker.mp4", 1.0, P["L6"],
     "the studio maker - live"),
]
for out, src, ss, seglen, text in beats:
    if out is None:
        c = cap("identity 0.60 rejected -> 0.85 passed - real judge scores")
        run(["-loop", "1", "-t", f"{seglen:.3f}", "-i", "comp_retake.png",
             "-vf", V + "," + c + "," + BADGE, "-an",
             "-c:v", "libx264", "-preset", "fast", "-crf", "19", "z3.mp4"])
        print("beat z3 (retake still)", round(seglen, 2), "s", flush=True)
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
     "-c:v", "libx264", "-preset", "fast", "-crf", "19", "z7a.mp4"])
run(["-ss", "0.0", "-t", f"{P['L7'] - L7A:.3f}", "-i", "cap_result.mp4",
     "-vf", V + "," + c7 + "," + BADGE, "-an",
     "-c:v", "libx264", "-preset", "fast", "-crf", "19", "z7b.mp4"])
run(["-ss", "9.4", "-t", f"{P['L8']:.3f}", "-i", "cap_result.mp4",
     "-vf", V + "," + cap("same identity, new scene") + "," + BADGE, "-an",
     "-c:v", "libx264", "-preset", "fast", "-crf", "19", "z8.mp4"])
print("beats z7a/z7b/z8 ok", flush=True)

# ── cards ──
run(["-ss", "0", "-t", f"{CARD_OPEN:.3f}", "-i", "c_open_n.mp4",
     "-vf", V, "-an",
     "-c:v", "libx264", "-preset", "fast", "-crf", "19", "o_card8.mp4"])


def txt(line, fn, size, y, font="arialbd.ttf", color="white"):
    with open(os.path.join(D, fn), "w", encoding="utf-8") as f:
        f.write(line.replace("—", "-"))
    return (f"drawtext=fontfile={font}:textfile={fn}:fontcolor={color}:fontsize={size}:"
            f"x=(w-text_w)/2:y={y}")


CARD_END = P["CARD_END"]
end_ov = ("drawbox=x=0:y=ih*0.32:w=iw:h=ih*0.36:color=black@0.6:t=fill," +
          txt("encore.tlz.us", "t8_e1.txt", 92, "h*0.35") + "," +
          txt("github.com/banksythequantLab/encore", "t8_e2.txt", 38, "h*0.35+135",
              "arial.ttf", "0xBFD3F2") + "," +
          txt("seasons, not clips — built on Backblaze B2", "t8_e3.txt", 36,
              "h*0.35+200", "arialbd.ttf", "0xFF5A6E"))
fp_dur = dur("flooded-pursuit-b29fa1f3.mp4")
end_ss = min(15.4, max(0.0, fp_dur - CARD_END - 0.3))
run(["-ss", f"{end_ss:.3f}", "-t", f"{CARD_END:.3f}",
     "-i", "flooded-pursuit-b29fa1f3.mp4",
     "-vf", V + "," + end_ov + "," + BADGE +
     f",fade=t=out:st={CARD_END - 0.9:.2f}:d=0.9", "-an",
     "-c:v", "libx264", "-preset", "fast", "-crf", "19", "e_card8.mp4"])
print("cards ok", flush=True)

# ── concat video ──
order = ["o_card8.mp4", "z1b.mp4", "z2.mp4", "z3.mp4", "z4.mp4", "z5.mp4",
         "z6.mp4", "z7a.mp4", "z7b.mp4", "z8.mp4", "e_card8.mp4"]
with open(os.path.join(D, "cc8.txt"), "w") as f:
    for o in order:
        f.write(f"file '{o}'\n")
run(["-f", "concat", "-safe", "0", "-i", "cc8.txt", "-c", "copy", "v8only.mp4"])
segd = [dur(o) for o in order]
total = sum(segd)
acc, starts = 0.0, []
for d0 in segd:
    starts.append(acc)
    acc += d0
print("video ok, total", round(total, 2), flush=True)

# ── VO placement at MEASURED beat starts (same scheme as v12/v14) ──
# order idx: 0 card, 1 z1b, 2 z2, 3 z3, 4 z4, 5 z5, 6 z6, 7 z7a, 8 z7b,
#            9 z8, 10 e_card
vo_at = [("n1.wav", 0.5),
         ("n3.wav", starts[2] + VOFF), ("n9.wav", starts[3] + VOFF),
         ("n10.wav", starts[4] + VOFF), ("n4.wav", starts[5] + VOFF),
         ("n7.wav", starts[6] + VOFF), ("n8.wav", starts[7] + 0.3),
         ("n5.wav", starts[9] + VOFF), ("n6.wav", starts[10] + 0.5)]
prev_end = None
for w, t0 in vo_at:
    g = None if prev_end is None else t0 - prev_end
    print(f"  {w} @ {t0:.2f} -> {t0 + vd[w]:.2f}"
          + (f"  (gap {g:.2f}s)" if g is not None else ""), flush=True)
    if g is not None:
        assert 0.7 <= g <= 1.6, f"gap {g:.2f}s out of spec before {w}"
    prev_end = t0 + vd[w]
print(f"  tail after n6: {total - prev_end:.2f}s", flush=True)

# ── build audio: NARRATION ONLY, v14 VO chain verbatim (no bed input) ──
VO_TARGET = -10.0
inputs, fl = [], []
for i, (w, t0) in enumerate(vo_at):
    cw = f"_vo8_{i}.wav"
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
              "-c:a", "aac", "-b:a", "256k", "a8.m4a"])
run(["-i", "v8only.mp4", "-i", "a8.m4a", "-map", "0:v", "-map", "1:a",
     "-c", "copy", "-shortest", "encore_demo_v15.mp4"])
print("segments:", [(o, round(d0, 2)) for o, d0 in zip(order, segd)], flush=True)
print("DONE encore_demo_v15.mp4", round(dur("encore_demo_v15.mp4"), 2), "s",
      flush=True)

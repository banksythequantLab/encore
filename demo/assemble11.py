"""Demo v18 -- fix: fully STATIC opening cards (title + premise).

v17 problems (frame-verified): the ENCORE lockup was composited with a
zoompan so it drifted and rescaled across card 1; the background
footage showed a character firing a rifle with the episode's burned-in
caption ("Rooftop. Final Shot") visible under the title; the premise
text on card 2 sat right-heavy.

v18 cards -- NOTHING moves. No footage, no zoompan, no per-letter
animation:
CARD 1 (4.0s, silent): solid 0x0B0E14 + static subtle vignette.
  Centered lockup: ENCORE (arialbd 170, white, x=(w-text_w)/2) at
  y=420; below it "on [BACKBLAZE B2]" (dim gray 34 + red 0xE4002B
  chip, white bold 44) centered AS A UNIT at y~640 -- component
  widths are measured off a rendered probe frame, no guessing.
  The ENTIRE card fades in from black over 0.4s then holds; text
  coordinates constant for the whole card. Badge top-right.
CARD 2 (~6.65s): same solid background. Three premise lines, each
  centered x=(w-text_w)/2, y=440/540/640, sizes 44/36/36, bold white
  lead + two lighter gray lines. All three lines present the whole
  card; single whole-card 0.3s fade-in. n1 starts 1.0s into the card
  (v17 timing, unchanged). Badge top-right.
THEN: q2a..q8 + e_card9.mp4 = APPROVED v16/v17 body segments reused
byte-identical (concat -c copy, NOT re-rendered). Audio: narration-
only chain, v17 scheme verbatim. Acceptance thresholds unchanged.
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


# Persistent sponsor badge, top-right on every frame (identical to v16/v17).
with open(os.path.join(D, "bb1.txt"), "w") as f:
    f.write("backblaze")
with open(os.path.join(D, "bb2.txt"), "w") as f:
    f.write("B2")
BADGE = ("drawtext=fontfile=arialbd.ttf:textfile=bb1.txt:fontcolor=white:fontsize=38:"
         "x=w-330:y=46:box=1:boxcolor=black@0.45:boxborderw=10,"
         "drawtext=fontfile=arialbd.ttf:textfile=bb2.txt:fontcolor=white:fontsize=38:"
         "x=w-116:y=46:box=1:boxcolor=0xE4002B:boxborderw=10")


def txtf(line, fn):
    with open(os.path.join(D, fn), "w", encoding="utf-8") as f:
        f.write(line.replace("—", "-"))
    return fn


def text_width(fn, font, size):
    """Advance width of rendered text, measured off a probe frame (no PIL)."""
    run(["-f", "lavfi", "-i", "color=c=black:s=1920x300:r=30:d=0.1",
         "-vf", (f"drawtext=fontfile={font}:textfile={fn}:fontcolor=white:"
                 f"fontsize={size}:x=100:y=80"),
         "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "gray", "_mw11.raw"])
    data = open(os.path.join(D, "_mw11.raw"), "rb").read()
    W, H = 1920, 300
    maxx = 0
    for yy in range(H):
        row = data[yy * W:(yy + 1) * W]
        for xx in range(W - 1, maxx, -1):
            if row[xx] > 40:
                if xx > maxx:
                    maxx = xx
                break
    os.remove(os.path.join(D, "_mw11.raw"))
    assert maxx > 100, "text width probe failed"
    return maxx - 100 + 1


# ── VO durations drive the whole cut (same clips as v16/v17) ──
vo = ["n1.wav", "n3.wav", "n9.wav", "n10.wav", "n4.wav",
      "n7.wav", "n8.wav", "n5.wav", "n6.wav"]
vd = {w: dur(w) for w in vo}
for w in vo:
    print(w, round(vd[w], 2), flush=True)

GAP = 1.2            # target silence between VO clips (spec 0.8-1.5s)
VOFF = 0.4           # VO start offset inside its beat (v16 scheme)
N1_OFF = 1.0         # n1 starts 1.0s into card 2 (v17, unchanged)
CARD1 = 4.0          # title card, silent (head-silence budget: 5.0s)
CARD2 = N1_OFF + vd["n1.wav"] + 0.25   # n1 ends ~0.25s before the cut
OPEN = CARD1 + CARD2
assert CARD1 >= 4.0 and CARD2 >= 4.0, "open cards must each hold >=4.0s"
assert CARD1 + N1_OFF <= 5.001, "silent head exceeds 5.0s exemption"
assert 6.0 <= CARD2 <= 8.2, f"card 2 length {CARD2:.2f} off spec"
print(f"open plan: card1 {CARD1:.2f}s + card2 {CARD2:.2f}s = {OPEN:.2f}s",
      flush=True)

# ── CARD 1: STATIC title card on solid 0x0B0E14, nothing moves ──
BG = "0x0B0E14"
txtf("ENCORE", "t11_title.txt")
txtf("on", "t11_on.txt")
txtf("BACKBLAZE B2", "t11_chip.txt")
w_on = text_width("t11_on.txt", "arial.ttf", 34)
w_chip = text_width("t11_chip.txt", "arialbd.ttf", 44)
BORDER, GAPX = 16, 26
lock_w = w_on + GAPX + BORDER + w_chip + BORDER
on_x = round((1920 - lock_w) / 2)
chip_x = on_x + w_on + GAPX + BORDER
print(f"lockup: on={w_on}px chip={w_chip}px -> on_x={on_x} chip_x={chip_x} "
      f"lock_w={lock_w} center={on_x + lock_w / 2:.0f}", flush=True)
assert abs(on_x + lock_w / 2 - 960) <= 1.0, "lockup not centered"

c1 = (f"drawtext=fontfile=arialbd.ttf:textfile=t11_title.txt:fontcolor=white:"
      f"fontsize=170:x=(w-text_w)/2:y=420,"
      f"drawtext=fontfile=arial.ttf:textfile=t11_on.txt:fontcolor=0x9AA3B2:"
      f"fontsize=34:x={on_x}:y=649,"
      f"drawtext=fontfile=arialbd.ttf:textfile=t11_chip.txt:fontcolor=white:"
      f"fontsize=44:x={chip_x}:y=640:box=1:boxcolor=0xE4002B:boxborderw={BORDER}")
run(["-f", "lavfi", "-i", f"color=c={BG}:s=1920x1080:r=30:d={CARD1:.3f}",
     "-vf", "vignette=a=PI/5," + c1 + "," + BADGE +
     ",fade=t=in:st=0:d=0.4,format=yuv420p",
     "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "19", "t_card11.mp4"])
print("card 1 (static title) rendered", round(dur("t_card11.mp4"), 2), "s",
      flush=True)

# ── CARD 2: STATIC premise card, all three lines up the whole card ──
plines = [
    ("An AI streaming network with a persistent cast.",
     "t11_p1.txt", "arialbd.ttf", 44, "white", 440),
    ("Episodes are planned, shot, judged, and archived automatically.",
     "t11_p2.txt", "arial.ttf", 36, "0xC9D4E8", 540),
    ("The cast and the season's story live durably on Backblaze B2.",
     "t11_p3.txt", "arial.ttf", 36, "0xB8C6E0", 640),
]
pov = []
for line, fn, font, size, color, y in plines:
    txtf(line, fn)
    pov.append(f"drawtext=fontfile={font}:textfile={fn}:fontcolor={color}:"
               f"fontsize={size}:x=(w-text_w)/2:y={y}")
run(["-f", "lavfi", "-i", f"color=c={BG}:s=1920x1080:r=30:d={CARD2:.3f}",
     "-vf", "vignette=a=PI/5," + ",".join(pov) + "," + BADGE +
     ",fade=t=in:st=0:d=0.3,format=yuv420p",
     "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "19", "p_card11.mp4"])
print("card 2 (static premise) rendered", round(dur("p_card11.mp4"), 2), "s",
      flush=True)

# ── concat: new open + APPROVED body segments reused byte-identical ──
order = ["t_card11.mp4", "p_card11.mp4", "q2a.mp4", "q2b.mp4", "q2c.mp4",
         "q3.mp4", "q4.mp4", "q5.mp4", "q6.mp4", "q7a.mp4", "q7b.mp4",
         "q8.mp4", "e_card9.mp4"]
for o in order[2:]:
    assert os.path.exists(os.path.join(D, o)), f"approved segment missing: {o}"
with open(os.path.join(D, "cc11.txt"), "w") as f:
    for o in order:
        f.write(f"file '{o}'\n")
run(["-f", "concat", "-safe", "0", "-i", "cc11.txt", "-c", "copy", "v11only.mp4"])
segd = [dur(o) for o in order]
total = sum(segd)
acc, starts = 0.0, []
for d0 in segd:
    starts.append(acc)
    acc += d0
print("video ok, total", round(total, 2), flush=True)
# pace: only the two open cuts before t=13; nothing fully inside 13s < 4.0s
cuts_13 = [round(s, 2) for s in starts[1:] if s < 13.0]
assert len(cuts_13) == 2, f"first-13s rhythm broken: cuts at {cuts_13}"
for s, d0 in zip(starts, segd):
    if s + d0 <= 13.0 + 0.05:
        assert d0 >= 4.0 - 1.0 / 30, f"visual at {s:.2f} only {d0:.2f}s (<4s)"
print("first-13s cuts:", cuts_13, flush=True)

# ── VO placement at MEASURED beat starts (v17 scheme verbatim) ──
# order idx: 0 card1, 1 card2, 2 q2a, 3 q2b, 4 q2c, 5 q3, 6 q4, 7 q5,
#            8 q6, 9 q7a, 10 q7b, 11 q8, 12 e_card
vo_at = [("n1.wav", starts[1] + N1_OFF),
         ("n3.wav", starts[2] + GAP), ("n9.wav", starts[5] + VOFF),
         ("n10.wav", starts[6] + VOFF), ("n4.wav", starts[7] + VOFF),
         ("n7.wav", starts[8] + VOFF), ("n8.wav", starts[9] + 0.3),
         ("n5.wav", starts[11] + VOFF), ("n6.wav", starts[12] + 0.5)]
prev_end = None
for w, t0 in vo_at:
    g = None if prev_end is None else t0 - prev_end
    print(f"  {w} @ {t0:.2f} -> {t0 + vd[w]:.2f}"
          + (f"  (gap {g:.2f}s)" if g is not None else ""), flush=True)
    if g is not None:
        assert 0.7 <= g <= 1.5 + 0.02, f"gap {g:.2f}s out of spec before {w}"
    prev_end = t0 + vd[w]
print(f"  tail after n6: {total - prev_end:.2f}s", flush=True)
# thesis cuts land inside measured n3 pauses (2.58-2.90, 7.27-7.73)
n3_t0 = vo_at[1][1]
for cut, lo, hi in ((starts[3], 2.58, 2.90), (starts[4], 7.27, 7.73)):
    off = cut - n3_t0
    assert lo - 0.06 <= off <= hi + 0.06, f"cut at n3 offset {off:.2f} mid-word"
    print(f"  cut @ {cut:.2f} = n3 offset {off:.2f} (pause {lo}-{hi})", flush=True)

# ── build audio: NARRATION ONLY, v17 VO chain verbatim ──
VO_TARGET = -10.0
inputs, fl = [], []
for i, (w, t0) in enumerate(vo_at):
    cw = f"_vo11_{i}.wav"
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
              "-c:a", "aac", "-b:a", "256k", "a11.m4a"])
run(["-i", "v11only.mp4", "-i", "a11.m4a", "-map", "0:v", "-map", "1:a",
     "-c", "copy", "-shortest", "encore_demo_v18.mp4"])
print("segments:", [(o, round(d0, 2)) for o, d0 in zip(order, segd)], flush=True)
print("DONE encore_demo_v18.mp4", round(dur("encore_demo_v18.mp4"), 2), "s",
      flush=True)

# ── acceptance: 0.5s-window RMS (mono 8k) on the final mux ──
raw = os.path.join(D, "_acc11.pcm")
run(["-i", "encore_demo_v18.mp4", "-ac", "1", "-ar", "8000",
     "-f", "s16le", "_acc11.pcm"])
data = open(raw, "rb").read()
ns = len(data) // 2
samp = struct.unpack(f"<{ns}h", data[:ns * 2])
W = 4000  # 0.5s @ 8k
wins = []
for i in range(0, ns - W + 1, W):
    s2 = sum(x * x for x in samp[i:i + W]) / W
    wins.append(20 * math.log10(max(math.sqrt(s2), 1e-9) / 32768.0))
runs, cur_start, cur = [], None, 0
for wi, dbv in enumerate(wins):
    if dbv < -35.0:
        if cur == 0:
            cur_start = wi
        cur += 1
    else:
        if cur:
            runs.append((cur_start, cur))
        cur = 0
if cur:
    runs.append((cur_start, cur))
head = tail = 0.0
interior = []
for st, ln in runs:
    if st == 0:
        head = ln * 0.5
    elif st + ln >= len(wins):
        tail = ln * 0.5
    else:
        interior.append(ln * 0.5)
worst = max(interior) if interior else 0.0
print(f"silence: head {head:.1f}s (exempt <=5.0), worst interior "
      f"{worst:.1f}s, end tail {tail:.1f}s", flush=True)
assert head <= 5.0 + 0.01, f"head silence {head:.1f}s > 5.0s exemption"
assert worst <= 2.0, f"interior silence {worst:.1f}s > 2.0s"
assert tail <= 2.5, f"end tail {tail:.1f}s > 2.5s"
for w, t0 in vo_at:
    i0 = int((t0 + 0.4) / 0.5)
    i1 = int((t0 + vd[w] - 0.4) / 0.5)
    lv = sorted(wins[i0:i1 + 1])
    med = lv[len(lv) // 2]
    print(f"  speech {w}: median window {med:.1f} dB", flush=True)
    assert -14.0 <= med <= -10.0, f"{w} speech level {med:.1f} out of range"
pk = peak_db("encore_demo_v18.mp4")
print(f"peak {pk:+.1f} dB", flush=True)
assert pk < 0.0, "clipping"
os.remove(raw)
print("ACCEPTANCE PASS", flush=True)

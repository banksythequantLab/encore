"""Demo v19 -- Derek's v18 notes: unstretched retake comparison + tighter open.

1) RETAKE COMPARISON UNSTRETCHED. v18's retake beat used comp_retake.png,
   which force-scaled take_rejected.png / take_accepted.png (both 1024x1024,
   ffprobe-verified) to 948x534 -- a hard squash. comp_retake2.png rebuilds
   the SAME layout (1920x1080, bg 0x0B0E14, header 'ONE ANCHOR. EVERY TAKE
   JUDGED.', red REJECTED caption + judge subline under the left slot, green
   PASSED caption + subline under the right slot) but each source is scaled
   with force_original_aspect_ratio=decrease into its 948x534 slot and
   letterboxed with the background color -- NO distortion (squares stay
   534x534, asserted off the rendered PNG). The retake beat is re-rendered
   as q3r12.mp4 with the v16 caption/badge recipe at the exact q3.mp4
   duration; every other body segment is reused byte-identical.

2) TIGHTER, RICHER OPEN (everything STATIC -- nothing moves/scales/drifts):
   CARD 1 (2.5s): the v18 pixel-locked ENCORE + red 'on [BACKBLAZE B2]' chip
     lockup, unchanged coordinates, over a STATIC pre-rendered mosaic of the
     five episode posters (5 x 384x1080 columns, dimmed to ~28% brightness,
     slight blur). Poster sources: /api/episodes poster_url -> /media/...;
     if the API/B2 is down (transaction cap), fall back to the local ComfyUI
     outputs that generated those exact posters (site library frame-matched).
     Whole-card 0.4s fade-in from black as in v18; coordinates constant.
   n1 STARTS AT t=1.0 absolute (over card 1) -> head silence 1.0s (was 5.0).
   CARD 2 (~4.5s): v18 premise card verbatim (3 static centered lines),
     trimmed; n1 (5.37s) finishes over it at ~6.37, cut at 7.0.
   n3's beat follows as before: n3 @ cut+1.2 (standard gap re-fit); the n3
   thesis pause-cuts stay at offsets 2.75/7.50 because q2a/q2b are reused
   byte-identical. n1->n3 silence is ~1.83s (interior <=2.0s spec holds).
THEN: q2a..q8 + e_card9.mp4 byte-identical (concat -c copy), retake beat
swapped for q3r12.mp4 at identical duration. Audio: narration-only chain,
v17/v18 scheme verbatim. Acceptance: head silence ~1.0s, interior <=2.0s,
speech medians -10..-14 dB, no clipping.
"""
import math
import os
import re
import shutil
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


def dims(f):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                        "-show_entries", "stream=width,height", "-of", "csv=p=0", f],
                       capture_output=True, text=True, cwd=D)
    w, h = r.stdout.strip().split(",")[:2]
    return int(w), int(h)


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


# Persistent sponsor badge, top-right on every frame (identical to v16-v18).
with open(os.path.join(D, "bb1.txt"), "w") as f:
    f.write("backblaze")
with open(os.path.join(D, "bb2.txt"), "w") as f:
    f.write("B2")
BADGE = ("drawtext=fontfile=arialbd.ttf:textfile=bb1.txt:fontcolor=white:fontsize=38:"
         "x=w-330:y=46:box=1:boxcolor=black@0.45:boxborderw=10,"
         "drawtext=fontfile=arialbd.ttf:textfile=bb2.txt:fontcolor=white:fontsize=38:"
         "x=w-116:y=46:box=1:boxcolor=0xE4002B:boxborderw=10")

V = ("scale=1920:1080:force_original_aspect_ratio=decrease,"
     "pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=30,format=yuv420p")

_N = [0]


def cap(line):
    # Compact single-line band, bottom-RIGHT (v16 recipe, kept for the body).
    _N[0] += 1
    fn = f"c12_{_N[0]}.txt"
    with open(os.path.join(D, fn), "w", encoding="utf-8") as f:
        f.write(line.replace("—", "-"))
    return (f"drawtext=fontfile=arialbd.ttf:textfile={fn}:fontcolor=white:fontsize=28:"
            f"x=w-text_w-48:y=h-92:box=1:boxcolor=black@0.6:boxborderw=10")


def txtf(line, fn):
    with open(os.path.join(D, fn), "w", encoding="utf-8") as f:
        f.write(line.replace("—", "-"))
    return fn


def text_width(fn, font, size):
    """Advance width of rendered text, measured off a probe frame (no PIL)."""
    run(["-f", "lavfi", "-i", "color=c=black:s=1920x300:r=30:d=0.1",
         "-vf", (f"drawtext=fontfile={font}:textfile={fn}:fontcolor=white:"
                 f"fontsize={size}:x=100:y=80"),
         "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "gray", "_mw12.raw"])
    data = open(os.path.join(D, "_mw12.raw"), "rb").read()
    W, H = 1920, 300
    maxx = 0
    for yy in range(H):
        row = data[yy * W:(yy + 1) * W]
        for xx in range(W - 1, maxx, -1):
            if row[xx] > 40:
                if xx > maxx:
                    maxx = xx
                break
    os.remove(os.path.join(D, "_mw12.raw"))
    assert maxx > 100, "text width probe failed"
    return maxx - 100 + 1


# ── Derek fix 1: rebuild the comparison frame WITHOUT distortion ──
BG = "0x0B0E14"
for src in ("take_rejected.png", "take_accepted.png"):
    w, h = dims(src)
    print(f"source {src}: {w}x{h}", flush=True)
    assert (w, h) == (1024, 1024), f"unexpected source dims for {src}"

SLOT_W, SLOT_H = 948, 534
LX, RX, IY = 12, 960, 275          # same slot geometry as comp_retake.png
hdr = txtf("ONE ANCHOR. EVERY TAKE JUDGED.", "t12_hdr.txt")
lc1 = txtf("TAKE 1  -  identity 0.60  -  REJECTED", "t12_l1.txt")
lc2 = txtf("judge: wrong wardrobe, wrong weapon", "t12_l2.txt")
rc1 = txtf("RETAKE  -  identity 0.85  -  PASSED", "t12_r1.txt")
rc2 = txtf("same prompt, feedback fed back in", "t12_r2.txt")
fit = (f"scale={SLOT_W}:{SLOT_H}:force_original_aspect_ratio=decrease,"
       f"pad={SLOT_W}:{SLOT_H}:(ow-iw)/2:(oh-ih)/2:{BG}")
texts = (
    f"drawtext=fontfile=arialbd.ttf:textfile=t12_hdr.txt:fontcolor=white:"
    f"fontsize=64:x=(w-text_w)/2:y=125,"
    f"drawtext=fontfile=arialbd.ttf:textfile=t12_l1.txt:fontcolor=0xFF5A6E:"
    f"fontsize=44:x={LX}+({SLOT_W}-text_w)/2:y=852,"
    f"drawtext=fontfile=arial.ttf:textfile=t12_l2.txt:fontcolor=0xC9D4E8:"
    f"fontsize=32:x={LX}+({SLOT_W}-text_w)/2:y=918,"
    f"drawtext=fontfile=arialbd.ttf:textfile=t12_r1.txt:fontcolor=0x6CE8A0:"
    f"fontsize=44:x={RX}+({SLOT_W}-text_w)/2:y=852,"
    f"drawtext=fontfile=arial.ttf:textfile=t12_r2.txt:fontcolor=0xC9D4E8:"
    f"fontsize=32:x={RX}+({SLOT_W}-text_w)/2:y=918")
run(["-f", "lavfi", "-i", f"color=c={BG}:s=1920x1080:r=30:d=0.1",
     "-i", "take_rejected.png", "-i", "take_accepted.png",
     "-filter_complex",
     f"[1:v]{fit}[l];[2:v]{fit}[r];"
     f"[0:v][l]overlay={LX}:{IY}[t1];[t1][r]overlay={RX}:{IY},{texts}",
     "-frames:v", "1", "comp_retake2.png"])

# Verify off the rendered PNG: each displayed image must still be SQUARE
# (1024x1024 fitted with =decrease into 948x534 -> 534x534, centered).
run(["-i", "comp_retake2.png", "-f", "rawvideo", "-pix_fmt", "gray", "_cf12.raw"])
data = open(os.path.join(D, "_cf12.raw"), "rb").read()
os.remove(os.path.join(D, "_cf12.raw"))
W, H = 1920, 1080


def content_bbox(x0, y0, w0, h0):
    minx, maxx, miny, maxy = None, None, None, None
    for yy in range(y0, y0 + h0):
        row = data[yy * W + x0: yy * W + x0 + w0]
        xs = [i for i, v in enumerate(row) if v > 19]  # bg luma is ~14, exact
        if xs:
            if minx is None or xs[0] < minx:
                minx = xs[0]
            if maxx is None or xs[-1] > maxx:
                maxx = xs[-1]
            if miny is None:
                miny = yy
            maxy = yy
    return minx, maxx, miny - y0, maxy - y0


for name, sx in (("left", LX), ("right", RX)):
    x0, x1, ytop, ybot = content_bbox(sx, IY, SLOT_W, SLOT_H)
    iw, ih = x1 - x0 + 1, ybot - ytop + 1
    ar = iw / ih
    print(f"comp_retake2 {name} slot content {iw}x{ih} (aspect {ar:.3f})", flush=True)
    assert 0.95 <= ar <= 1.05, f"{name} image distorted: {iw}x{ih}"
    assert ih >= SLOT_H - 4, f"{name} image does not fill slot height"
print("comp_retake2.png ok -- both takes rendered square (no stretch)", flush=True)


# ── VO durations drive the whole cut (same clips as v16-v18) ──
vo = ["n1.wav", "n3.wav", "n9.wav", "n10.wav", "n4.wav",
      "n7.wav", "n8.wav", "n5.wav", "n6.wav"]
vd = {w: dur(w) for w in vo}
for w in vo:
    print(w, round(vd[w], 2), flush=True)

GAP = 1.2            # standard silence between VO clips
VOFF = 0.4           # VO start offset inside its beat (v16 scheme)
N1_AT = 1.0          # n1 starts at ABSOLUTE t=1.0, over card 1 (Derek v19)
CARD1 = 2.5          # title card over static poster mosaic
CARD2 = max(4.5, N1_AT + vd["n1.wav"] + 0.25 - CARD1)  # ~4.5s; n1 ends over it
OPEN = CARD1 + CARD2
assert N1_AT + vd["n1.wav"] <= OPEN - 0.25, "n1 must finish before the cold open"
print(f"open plan: card1 {CARD1:.2f}s + card2 {CARD2:.2f}s = {OPEN:.2f}s; "
      f"n1 {N1_AT:.2f}->{N1_AT + vd['n1.wav']:.2f}", flush=True)

# ── re-render the retake beat with the fixed frame (v16 recipe/duration) ──
seglen = vd["n9.wav"] + GAP
c3 = cap("identity 0.60 rejected -> 0.85 passed - real judge scores")
run(["-loop", "1", "-t", f"{seglen:.3f}", "-i", "comp_retake2.png",
     "-vf", V + "," + c3 + "," + BADGE, "-an",
     "-c:v", "libx264", "-preset", "fast", "-crf", "19", "q3r12.mp4"])
assert abs(dur("q3r12.mp4") - dur("q3.mp4")) < 1.0 / 30 + 0.005, \
    "retake beat duration drifted from approved q3.mp4"
print("beat q3r12 (unstretched retake still)", round(dur("q3r12.mp4"), 2), "s",
      flush=True)

# ── Derek fix 2, card 1 backdrop: static mosaic of the five episode posters ──
# Primary source: the service API. Fallback (B2 daily transaction cap makes
# /api/episodes and /media 500/404 right now): the local ComfyUI outputs that
# produced those exact posters -- frame-matched against the site library
# capture (cap1_hero.mp4: Warlords Sniper - 5 episodes, newest first).
COMFY_OUT = r"B:\ComfyUI-Easy-Install\ComfyUI-Easy-Install\ComfyUI\output"
LOCAL_POSTERS = [
    ("signal-in-the-shadows", "gb_5483a15c3a_00001_.png"),
    ("submersion",            "gb_25fe474905_00001_.png"),
    ("flooded-pursuit",       "gb_a8910b17b4_00001_.png"),
    ("rain-s-edge",           "gb_1777ce9ade_00001_.png"),
    ("rainfall",              "gb_973d20e3d9_00001_.png"),
]
API = "http://127.0.0.1:8090"
poster_files = []
try:
    import json
    import urllib.request
    with urllib.request.urlopen(f"{API}/api/episodes", timeout=15) as r:
        eps = json.load(r)["episodes"]
    urls = [e["poster_url"] for e in eps if e.get("poster_url")][:5]
    assert len(urls) == 5, f"expected 5 posters, API returned {len(urls)}"
    for i, u in enumerate(urls):
        fn = f"poster12_{i}.png"
        urllib.request.urlretrieve(f"{API}{u}", os.path.join(D, fn))
        poster_files.append(fn)
    print("posters fetched from /api/episodes:", urls, flush=True)
except Exception as e:
    print(f"API poster fetch failed ({e!r}); using local ComfyUI copies",
          flush=True)
    for i, (stem, src) in enumerate(LOCAL_POSTERS):
        fn = f"poster12_{i}.png"
        shutil.copyfile(os.path.join(COMFY_OUT, src), os.path.join(D, fn))
        poster_files.append(fn)
        print(f"  poster12_{i}.png <- {src} ({stem})", flush=True)

# Tile as five 384x1080 columns, dim to ~28% brightness, slight blur. The
# result is a single pre-rendered STATIC png -- nothing can move on card 1.
cols = []
inputs = []
for i, fn in enumerate(poster_files):
    inputs += ["-i", fn]
    cols.append(f"[{i}:v]scale=384:1080:force_original_aspect_ratio=increase,"
                f"crop=384:1080,setsar=1[c{i}]")
fc = (";".join(cols) + ";" + "".join(f"[c{i}]" for i in range(5)) +
      "hstack=inputs=5,gblur=sigma=2.5,"
      "colorchannelmixer=rr=0.28:gg=0.28:bb=0.28,format=rgb24")
run(inputs + ["-filter_complex", fc, "-frames:v", "1", "mosaic12.png"])
assert dims("mosaic12.png") == (1920, 1080), "mosaic not 1920x1080"
print("mosaic12.png rendered (static, dimmed 28%, blurred)", flush=True)


# ── CARD 1: v18 pixel-locked lockup, unchanged coordinates, mosaic behind ──
txtf("ENCORE", "t12_title.txt")
txtf("on", "t12_on.txt")
txtf("BACKBLAZE B2", "t12_chip.txt")
w_on = text_width("t12_on.txt", "arial.ttf", 34)
w_chip = text_width("t12_chip.txt", "arialbd.ttf", 44)
BORDER, GAPX = 16, 26
lock_w = w_on + GAPX + BORDER + w_chip + BORDER
on_x = round((1920 - lock_w) / 2)
chip_x = on_x + w_on + GAPX + BORDER
print(f"lockup: on={w_on}px chip={w_chip}px -> on_x={on_x} chip_x={chip_x} "
      f"lock_w={lock_w} center={on_x + lock_w / 2:.0f}", flush=True)
assert abs(on_x + lock_w / 2 - 960) <= 1.0, "lockup not centered"

c1 = (f"drawtext=fontfile=arialbd.ttf:textfile=t12_title.txt:fontcolor=white:"
      f"fontsize=170:x=(w-text_w)/2:y=420,"
      f"drawtext=fontfile=arial.ttf:textfile=t12_on.txt:fontcolor=0x9AA3B2:"
      f"fontsize=34:x={on_x}:y=649,"
      f"drawtext=fontfile=arialbd.ttf:textfile=t12_chip.txt:fontcolor=white:"
      f"fontsize=44:x={chip_x}:y=640:box=1:boxcolor=0xE4002B:boxborderw={BORDER}")
run(["-loop", "1", "-t", f"{CARD1:.3f}", "-i", "mosaic12.png",
     "-vf", "fps=30,vignette=a=PI/5," + c1 + "," + BADGE +
     ",fade=t=in:st=0:d=0.4,format=yuv420p",
     "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "19", "t_card12.mp4"])
print("card 1 (static title over mosaic) rendered",
      round(dur("t_card12.mp4"), 2), "s", flush=True)

# ── CARD 2: v18 static premise card verbatim, trimmed to ~4.5s ──
plines = [
    ("An AI streaming network with a persistent cast.",
     "t12_p1.txt", "arialbd.ttf", 44, "white", 440),
    ("Episodes are planned, shot, judged, and archived automatically.",
     "t12_p2.txt", "arial.ttf", 36, "0xC9D4E8", 540),
    ("The cast and the season's story live durably on Backblaze B2.",
     "t12_p3.txt", "arial.ttf", 36, "0xB8C6E0", 640),
]
pov = []
for line, fn, font, size, color, y in plines:
    txtf(line, fn)
    pov.append(f"drawtext=fontfile={font}:textfile={fn}:fontcolor={color}:"
               f"fontsize={size}:x=(w-text_w)/2:y={y}")
run(["-f", "lavfi", "-i", f"color=c={BG}:s=1920x1080:r=30:d={CARD2:.3f}",
     "-vf", "vignette=a=PI/5," + ",".join(pov) + "," + BADGE +
     ",fade=t=in:st=0:d=0.3,format=yuv420p",
     "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "19", "p_card12.mp4"])
print("card 2 (static premise) rendered", round(dur("p_card12.mp4"), 2), "s",
      flush=True)

# ── concat: new open + fixed retake beat + APPROVED body byte-identical ──
order = ["t_card12.mp4", "p_card12.mp4", "q2a.mp4", "q2b.mp4", "q2c.mp4",
         "q3r12.mp4", "q4.mp4", "q5.mp4", "q6.mp4", "q7a.mp4", "q7b.mp4",
         "q8.mp4", "e_card9.mp4"]
for o in order:
    assert os.path.exists(os.path.join(D, o)), f"segment missing: {o}"
with open(os.path.join(D, "cc12.txt"), "w") as f:
    for o in order:
        f.write(f"file '{o}'\n")
run(["-f", "concat", "-safe", "0", "-i", "cc12.txt", "-c", "copy", "v12only.mp4"])
segd = [dur(o) for o in order]
total = sum(segd)
acc, starts = 0.0, []
for d0 in segd:
    starts.append(acc)
    acc += d0
print("video ok, total", round(total, 2), flush=True)
# pace: the two open cuts + the previously->thesis cut land before t=13.
cuts_13 = [round(s, 2) for s in starts[1:] if s < 13.0]
assert abs(cuts_13[0] - CARD1) <= 0.05 and abs(cuts_13[1] - OPEN) <= 0.07, \
    f"open cuts off plan: {cuts_13}"
assert len(cuts_13) <= 3, f"first-13s rhythm broken: cuts at {cuts_13}"
# card1 is 2.5s by Derek's v19 direction; every other early beat >=3.9s
for s, d0 in zip(starts[1:], segd[1:]):
    if s + d0 <= 13.0 + 0.05:
        assert d0 >= 3.9, f"visual at {s:.2f} only {d0:.2f}s (<3.9s)"
print("first-13s cuts:", cuts_13, flush=True)


# ── VO placement (v18 scheme; n1 pulled to t=1.0, rest re-fit) ──
# order idx: 0 card1, 1 card2, 2 q2a, 3 q2b, 4 q2c, 5 q3r12, 6 q4, 7 q5,
#            8 q6, 9 q7a, 10 q7b, 11 q8, 12 e_card
vo_at = [("n1.wav", N1_AT),
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
        # n1->n3 is ~1.83s by design (card2 ~4.5s + standard cut+1.2 re-fit);
        # measured interior silence stays <=2.0s (asserted below on the mux).
        assert 0.7 <= g <= 1.9, f"gap {g:.2f}s out of spec before {w}"
    prev_end = t0 + vd[w]
print(f"  tail after n6: {total - prev_end:.2f}s", flush=True)
# thesis cuts land inside measured n3 pauses (2.58-2.90, 7.27-7.73)
n3_t0 = vo_at[1][1]
for cut, lo, hi in ((starts[3], 2.58, 2.90), (starts[4], 7.27, 7.73)):
    off = cut - n3_t0
    assert lo - 0.06 <= off <= hi + 0.06, f"cut at n3 offset {off:.2f} mid-word"
    print(f"  cut @ {cut:.2f} = n3 offset {off:.2f} (pause {lo}-{hi})", flush=True)

# ── build audio: NARRATION ONLY, v17/v18 VO chain verbatim ──
VO_TARGET = -10.0
inputs, fl = [], []
for i, (w, t0) in enumerate(vo_at):
    cw = f"_vo12_{i}.wav"
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
          # final limiter at -1.4 dB (v18 used -1.0; AAC overshoot grazed
          # 0 dBFS on this cut, so a touch more headroom -- no clipping)
          f"normalize=0,alimiter=limit=0.851:level=false,"
          f"apad,atrim=0:{total:.2f}[a]")
run(inputs + ["-filter_complex", ";".join(fl), "-map", "[a]",
              "-c:a", "aac", "-b:a", "256k", "a12.m4a"])
run(["-i", "v12only.mp4", "-i", "a12.m4a", "-map", "0:v", "-map", "1:a",
     "-c", "copy", "-shortest", "encore_demo_v19.mp4"])
print("segments:", [(o, round(d0, 2)) for o, d0 in zip(order, segd)], flush=True)
print("DONE encore_demo_v19.mp4", round(dur("encore_demo_v19.mp4"), 2), "s",
      flush=True)

# ── acceptance: 0.5s-window RMS (mono 8k) on the final mux ──
raw = os.path.join(D, "_acc12.pcm")
run(["-i", "encore_demo_v19.mp4", "-ac", "1", "-ar", "8000",
     "-f", "s16le", "_acc12.pcm"])
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
print(f"silence: head {head:.1f}s (target ~1.0), worst interior "
      f"{worst:.1f}s, end tail {tail:.1f}s", flush=True)
assert head <= 1.0 + 0.01, f"head silence {head:.1f}s > 1.0s"
assert head >= 0.5, f"head silence {head:.1f}s -- n1 not at 1.0?"
assert worst <= 2.0, f"interior silence {worst:.1f}s > 2.0s"
assert tail <= 2.5, f"end tail {tail:.1f}s > 2.5s"
for w, t0 in vo_at:
    i0 = int((t0 + 0.4) / 0.5)
    i1 = int((t0 + vd[w] - 0.4) / 0.5)
    lv = sorted(wins[i0:i1 + 1])
    med = lv[len(lv) // 2]
    print(f"  speech {w}: median window {med:.1f} dB", flush=True)
    assert -14.0 <= med <= -10.0, f"{w} speech level {med:.1f} out of range"
pk = peak_db("encore_demo_v19.mp4")
print(f"peak {pk:+.1f} dB", flush=True)
assert pk < 0.0, "clipping"
os.remove(raw)
print("ACCEPTANCE PASS", flush=True)

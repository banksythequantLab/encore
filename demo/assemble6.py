"""Demo v13 -- AUDIO-ONLY fix of v12's inverted mix (Derek: "major sound gaps").

Diagnosis (measured on encore_demo_v12.mp4, 2s-window RMS):
  VO windows sat at -15..-16.5 dB while VO-free gap swells hit -9.4..-11 dB,
  i.e. narration ~6 dB QUIETER than the fill music. Root cause: assemble5.py
  peak-normalized VO to -1.5 dB, but the VO wavs already peak near -1 dB with
  mean RMS ~-21 dB (peaky TTS), so VO gain was ~1.0x while the full-scale
  score bed swelled to 0.38 in gaps.

Fix (this script changes ONLY the audio; video/captions/beats untouched):
  * VO: per clip, 8:1 crest compression above -24 dB, then a measured
    makeup gain that puts its mean RMS at VO_TARGET, safety limiter -1 dB.
  * Bed: 0.11 under VO (was 0.16), gap swell 0.18 (was 0.38), same 0.7s ramps.
  * Reuses v5only.mp4 (approved video) and the y*/card segment files for
    timing; writes a6.m4a + encore_demo_v13.mp4. Nothing is overwritten.

Acceptance (2s-window RMS on v13): VO windows avg -11..-13 dB, gap windows
-15..-18 dB, no window < -20 dB before the final fade, no clipping.
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


def mean_db(f):
    """Mean RMS level (volumedetect mean_volume) in dBFS."""
    r = subprocess.run(["ffmpeg", "-i", f, "-af", "volumedetect", "-f", "null", "-"],
                       capture_output=True, text=True, cwd=D)
    m = re.search(r"mean_volume: (-?[0-9.]+) dB", r.stderr)
    return float(m.group(1))


def peak_db(f):
    r = subprocess.run(["ffmpeg", "-i", f, "-af", "volumedetect", "-f", "null", "-"],
                       capture_output=True, text=True, cwd=D)
    m = re.search(r"max_volume: (-?[0-9.]+) dB", r.stderr)
    return float(m.group(1)) if m else -6.0


# ── timing comes from the APPROVED v12 segments (no video re-render) ──
order = ["o_card5.mp4", "y1b.mp4", "y2.mp4", "y3.mp4", "y4.mp4", "y5.mp4",
         "y6.mp4", "y7a.mp4", "y7b.mp4", "y8.mp4", "e_card5.mp4"]
segd = [dur(o) for o in order]
total = sum(segd)
acc, starts = 0.0, []
for d0 in segd:
    starts.append(acc)
    acc += d0
assert abs(total - dur("v5only.mp4")) < 0.1, "segment sum != v5only duration"
print("video total", round(total, 2), flush=True)

VOFF = 0.4
vo = ["n1.wav", "n3.wav", "n9.wav", "n10.wav", "n4.wav",
      "n7.wav", "n8.wav", "n5.wav", "n6.wav"]
vd = {w: dur(w) for w in vo}
# Same placement as assemble5.py (approved).
vo_at = [("n1.wav", 0.5),
         ("n3.wav", starts[2] + VOFF), ("n9.wav", starts[3] + VOFF),
         ("n10.wav", starts[4] + VOFF), ("n4.wav", starts[5] + VOFF),
         ("n7.wav", starts[6] + VOFF), ("n8.wav", starts[7] + 0.3),
         ("n5.wav", starts[9] + VOFF), ("n6.wav", starts[10] + 0.5)]

# ── level scheme (THE fix) ──
VO_TARGET = -10.5   # mean RMS target for narration in the mix
BASE, GAPV, RAMP = 0.11, 0.18, 0.7   # bed: under VO / gap swell / ramp secs
# Measured on this footage: VO 2s-windows land ~2 dB under VO_TARGET (edge
# windows + clip/bus limiters); gap windows land at 20*log10(0.891*GAPV)
# minus 0..1.8 dB of music dynamics. -10.5 / 0.18 puts VO ~-12.5 avg and
# gaps ~-16.1 avg: ~3.6 dB separation, inside the -11..-13 / -15..-18 spec.

# Gap detection identical to assemble5.py (0.7s ramps kept).
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

# ── build audio: crest-compress each VO, then measured gain to VO_TARGET ──
# Static gain alone doesn't work: the TTS clips have ~20 dB crest factor, so
# boosting mean RMS to -12 dB puts peaks ~+9 dBFS and any limiter then eats
# ~5 dB of the boost (measured: VO windows landed -14.2 avg on the first
# render). Instead: 8:1 compression above -24 dB tames the crest, then an
# EXACT measured makeup gain hits the RMS target; a -1 dB safety limiter
# only touches brief residual transients.
import math
inputs, fl = [], []
for i, (w, t0) in enumerate(vo_at):
    cw = f"_vo6_{i}.wav"
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
inputs += ["-stream_loop", "-1", "-i", "score.flac"]
n = len(vo_at)
gm = min(10 ** ((-1.0 - peak_db("score.flac")) / 20.0), 4.0)
fl.append(f"[{n}:a]aresample=48000,atrim=0:{total:.2f},volume={gm:.3f},"
          f"volume=volume='{expr}':eval=frame,"
          f"afade=t=in:st=0:d=0.4,afade=t=out:st={total - 3.0:.2f}:d=3.0[m]")
fl.append("".join(f"[v{i}]" for i in range(n)) +
          f"[m]amix=inputs={n + 1}:duration=longest:dropout_transition=0:"
          f"normalize=0,alimiter=limit=0.891:level=false,atrim=0:{total:.2f}[a]")
# final limiter at -1 dB (v12 used 0.95): VO peaks ride the bus limiter now,
# so leave headroom for AAC encode overshoot -- v13 must not clip.
run(inputs + ["-filter_complex", ";".join(fl), "-map", "[a]", "-c:a", "aac", "a6.m4a"])
run(["-i", "v5only.mp4", "-i", "a6.m4a", "-map", "0:v", "-map", "1:a",
     "-c", "copy", "-shortest", "encore_demo_v13.mp4"])
for w, t0 in vo_at:
    print(f"  {w} @ {t0:.2f} -> {t0 + vd[w]:.2f}", flush=True)
print("bed: base", BASE, "gap", GAPV, "ramp", RAMP, "score gm", round(gm, 3), flush=True)
print("DONE encore_demo_v13.mp4", round(dur("encore_demo_v13.mp4"), 2), "s", flush=True)

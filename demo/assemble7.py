"""Demo v14 -- replace the bed SOURCE only (v13 mix scheme kept).

Root cause found 2026-07-09: score.flac (bed for v11-v13) is 31.95s of
FULL-SCALE DC FLATLINE -- non-audio that fooled RMS checks, so v13 "passed"
its profile while the music was inaudible. ALL ComfyUI/ACE-Step beds
generated today are DC (gb_*.flac, 14KB each, 10:23AM-10:47PM), so no new
bed can be generated until ACE-Step is debugged.

Harvest attempt (per PM): submersion-ca5f894e.mp4 was profiled in 0.5s
windows expecting a real music bed. MEASURED RESULT: its audio is a DC
flatline at -0.07 FS (-23.1 dB "RMS" -- which is what volumedetect reported
as "mean -23.2 / max -8.8") plus two short VO bursts (~3.0-5.0s, ~12.5-14.0s,
300-3400Hz speech-band dominant). It contains NO music. Same for
flooded-pursuit-b29fa1f3.mp4 and data-in-the-deep.mp4 (checked; single
audio stream each). The episode beds were NEVER audible.

Fallback bed (real, instrumental, on-machine, no generation needed):
ACE-Step's bundled instrumental demo track --
  ComfyUI python_embeded/.../comfyui_workflow_templates_media_image/
  templates/audio_ace_step_1_t2a_instrumentals-1.mp3  (29.9s, real music:
  0.5s-window RMS -11.5..-25 dB, broadband). Harvested span 4.5-18.5s
  (14.0s steady groove; avoids quiet intro, 18.5-20.5s loud bass drop and
  27.5s+ fade-out). Looped x3 with 1.0s tri acrossfades + highpass=f=40
  -> bed14.wav (40.0s seamless, mean -14.9 dB, max -1.8 dB, 2s-window RMS
  varies -15.8..-20.1 std 1.2 -- verified real music, no speech).

Levels: VO chain identical to assemble6.py (v13). Because bed14's inherent
RMS (-17 dB) differs from the DC file's (0 dB), BASE/GAPV are now computed
from the MEASURED bed mean so the bed lands at BED_BASE_DB under VO and
BED_GAP_DB in gap swells (same 0.7s ramps, same gap detection).

Acceptance (same as v13, 2s-window RMS): VO windows avg -11..-13 dB and
clearly louder than gaps; gap windows -15..-19 dB; no window < -21 dB
before the final fade; no clipping. PLUS music-reality check: gap audio
must have window-to-window RMS variance and 100Hz-8kHz spectral energy.
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


# ── bed14.wav: real instrumental loop (built once; see docstring) ──
BED = "bed14.wav"
BED_SRC = (r"B:\ComfyUI-Easy-Install\ComfyUI-Easy-Install\python_embeded"
           r"\Lib\site-packages\comfyui_workflow_templates_media_image"
           r"\templates\audio_ace_step_1_t2a_instrumentals-1.mp3")
if not os.path.exists(os.path.join(D, BED)):
    run(["-ss", "4.5", "-t", "14.0", "-i", BED_SRC,
         "-af", "highpass=f=40", "-ar", "48000", "-ac", "2", "_bed14_span.wav"])
    run(["-i", "_bed14_span.wav", "-i", "_bed14_span.wav", "-i", "_bed14_span.wav",
         "-filter_complex",
         "[0:a][1:a]acrossfade=d=1.0:c1=tri:c2=tri[x];"
         "[x][2:a]acrossfade=d=1.0:c1=tri:c2=tri[a]",
         "-map", "[a]", BED])
print("bed14.wav", round(dur(BED), 2), "s mean", mean_db(BED),
      "dB peak", peak_db(BED), "dB", flush=True)

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

# ── level scheme: VO identical to v13; bed re-leveled from MEASURED RMS ──
VO_TARGET = -10.0     # v13 used -10.5, but v13's VO windows read -12.6 only
# because the full-scale DC bed added ~0.5 dB of constant (inaudible) power
# to every window. With a real bed at -19 the same chain measured -13.03
# (render 3) -- just outside the -11..-13 spec. +0.5 dB restores v13's
# measured VO profile; chain architecture is unchanged.
BED_BASE_DB = -19.0   # bed RMS under VO (v13's DC bed sat at -20.2 eff.)
BED_GAP_DB = -14.3    # bed RMS in gap swells (v13 spec: gaps -15..-19)
# NOTE: targets are ~2 dB hotter than the naive spec numbers because the
# acceptance profile decodes MONO 8k: the wide-stereo music loses ~2.2 dB
# in the downmix vs volumedetect's per-channel mean (measured on render 1:
# gap windows landed -19.0 avg with BED_GAP_DB=-16.5; -14.3 centers them
# at ~-16.8, range ~-15.2..-18.3, inside the -15..-19 spec).
RAMP = 0.7            # same 0.7s ramps as v13
# gm normalizes bed peak to -1 dB; BASE/GAPV are then derived from the
# bed's measured mean RMS so the real music (unlike the DC file, whose
# "RMS" equalled its peak) lands on the same mix targets as v13.
gm = min(10 ** ((-1.0 - peak_db(BED)) / 20.0), 4.0)
import math
bed_mean_norm = mean_db(BED) + 20 * math.log10(gm)
BASE = 10 ** ((BED_BASE_DB - bed_mean_norm) / 20.0)
GAPV = 10 ** ((BED_GAP_DB - bed_mean_norm) / 20.0)
print(f"bed norm mean {bed_mean_norm:.1f} dB -> BASE {BASE:.3f} GAPV {GAPV:.3f}",
      flush=True)

# Gap detection identical to assemble5.py/assemble6.py (0.7s ramps kept).
iv = [(t0, t0 + vd[w]) for w, t0 in vo_at]
gaps, prev = [], 0.0
for s, e in iv:
    if s - prev > 2.0:
        gaps.append((prev, s))
    prev = max(prev, e)
if total - prev > 2.0:
    gaps.append((prev, total))
terms = "".join(
    f"+{GAPV - BASE:.3f}*min(max((t-{s:.2f})/{RAMP},0),1)"
    f"*min(max(({e:.2f}-t)/{RAMP},0),1)"
    for s, e in gaps)
expr = f"{BASE:.3f}{terms}"
print("gaps:", [(round(s, 2), round(e, 2)) for s, e in gaps], flush=True)

# ── build audio: crest-compress each VO, then measured gain to VO_TARGET ──
# (identical VO chain to assemble6.py -- see its docstring for rationale)
inputs, fl = [], []
for i, (w, t0) in enumerate(vo_at):
    cw = f"_vo7_{i}.wav"
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
inputs += ["-stream_loop", "-1", "-i", BED]
n = len(vo_at)
fl.append(f"[{n}:a]aresample=48000,atrim=0:{total:.2f},volume={gm:.3f},"
          f"volume=volume='{expr}':eval=frame,"
          # real music (unlike the DC bed) has transients that ride the -1 dB
          # bus limiter and overshoot to 0 dBFS after AAC encode (measured:
          # 2 full-scale samples on render 2). -1.5 dB bed limiter fixes it.
          f"alimiter=limit=0.841:level=false,"
          f"afade=t=in:st=0:d=0.4,afade=t=out:st={total - 3.0:.2f}:d=3.0[m]")
fl.append("".join(f"[v{i}]" for i in range(n)) +
          f"[m]amix=inputs={n + 1}:duration=longest:dropout_transition=0:"
          f"normalize=0,alimiter=limit=0.891:level=false,atrim=0:{total:.2f}[a]")
# final limiter at -1 dB, same as v13. With a REAL bed the VO+music sum
# rides this ceiling during narration and default-bitrate AAC overshot to
# 0 dBFS (2 full-scale samples at 15.1s/54.7s, render 3); encoding at
# 256k keeps quantization overshoot down instead of squeezing the mix.
run(inputs + ["-filter_complex", ";".join(fl), "-map", "[a]",
              "-c:a", "aac", "-b:a", "256k", "a7.m4a"])
run(["-i", "v5only.mp4", "-i", "a7.m4a", "-map", "0:v", "-map", "1:a",
     "-c", "copy", "-shortest", "encore_demo_v14.mp4"])
for w, t0 in vo_at:
    print(f"  {w} @ {t0:.2f} -> {t0 + vd[w]:.2f}", flush=True)
print("bed: base", round(BASE, 3), "gap", round(GAPV, 3), "ramp", RAMP,
      "gm", round(gm, 3), flush=True)
print("DONE encore_demo_v14.mp4", round(dur("encore_demo_v14.mp4"), 2), "s", flush=True)

"""Assemble the Encore demo video: captures + episode montage + VO + score."""
import os
import subprocess

D = os.path.dirname(os.path.abspath(__file__))


def run(args):
    r = subprocess.run(["ffmpeg", "-y"] + args, capture_output=True, text=True, cwd=D)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-600:])


# 1) Normalized, silent video segments (1920x1080@30)
V = "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=30,format=yuv420p"
segs = [
    ("s_a1.mp4", ["-ss", "2", "-t", "10", "-i", "submersion-ca5f894e.mp4"]),
    ("s_a2.mp4", ["-ss", "6", "-t", "10", "-i", "flooded-pursuit-b29fa1f3.mp4"]),
    ("s_b.mp4",  ["-t", "15.9", "-i", "cap1_hero.mp4"]),
    ("s_c.mp4",  ["-t", "18.8", "-i", "cap3_sections.mp4"]),
    ("s_d.mp4",  ["-ss", "1.5", "-t", "18", "-i", "cap2_theater.mp4"]),
    ("s_e.mp4",  ["-ss", "1", "-t", "20.8", "-i", "cap4_canon.mp4"]),
]
for out, inargs in segs:
    run(inargs + ["-vf", V, "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "19", out])
    print("seg", out, flush=True)

# 2) Concat video
with open(os.path.join(D, "concat.txt"), "w") as f:
    for out, _ in segs:
        f.write(f"file '{out}'\n")
run(["-f", "concat", "-safe", "0", "-i", "concat.txt", "-c", "copy", "video_only.mp4"])
print("video concat ok", flush=True)

# 3) Audio: VO beats at offsets + looped score under everything
# segment starts: A=0 (20s), B=20, C=35.9, D=54.7, E=72.7; total 93.5
total = 93.5
vo = [("b1_hook.wav", 500), ("b4_network.wav", 20500), ("b2_vault.wav", 36400),
      ("b3_judge.wav", 55200), ("b5_stunt.wav", 74200)]
inputs, fl = [], []
for i, (w, ms) in enumerate(vo):
    inputs += ["-i", w]
    fl.append(f"[{i}:a]aresample=48000,pan=stereo|c0=c0|c1=c0,adelay={ms}|{ms}[v{i}]")
inputs += ["-stream_loop", "-1", "-i", "score.flac"]
n = len(vo)
fl.append(f"[{n}:a]aresample=48000,atrim=0:{total},volume=0.13,afade=t=out:st={total-3}:d=3[m]")
fl.append("".join(f"[v{i}]" for i in range(n)) + f"[m]amix=inputs={n + 1}:duration=longest:"
          f"dropout_transition=0,volume=2.2,atrim=0:{total}[a]")
run(inputs + ["-filter_complex", ";".join(fl), "-map", "[a]",
              "-c:a", "aac", "-ar", "48000", "audio.m4a"])
print("audio ok", flush=True)

# 4) Mux
run(["-i", "video_only.mp4", "-i", "audio.m4a", "-map", "0:v", "-map", "1:a",
     "-c:v", "copy", "-c:a", "copy", "-shortest", "encore_demo_rough.mp4"])
print("DONE encore_demo_rough.mp4", flush=True)

import subprocess

from dotenv import load_dotenv

load_dotenv()

import music  # noqa: E402

p = music.generate_music_bed(seconds=20)
print("PATH", p, flush=True)
r = subprocess.run(["ffprobe", "-v", "quiet", "-show_entries", "format=duration,format_name",
                    "-of", "default=nw=1", p], capture_output=True, text=True)
print(r.stdout, flush=True)
print("DONE", flush=True)

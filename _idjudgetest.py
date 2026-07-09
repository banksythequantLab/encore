"""Validate the LOCAL identity judge (Ollama qwen3-vl): same vs different character."""
import os, base64
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
os.environ["JUDGE_STRATEGY"] = "ollama"  # fully local, no cloud key
import judges, vault

OUT = Path(r"C:\Users\solti\AppData\Roaming\Claude\local-agent-mode-sessions\052aebbf-870d-4145-83e8-ff7179b1782a\8e6f879d-68f7-44e0-8e92-2909603272a8\local_1977794e-6a98-487b-a662-bdbf3f2d4791\outputs")

def datauri(p):
    return "data:image/png;base64," + base64.b64encode(Path(p).read_bytes()).decode()

show = vault.load_cast_from_b2("hero-ai")
eva = next(c for c in show["cast"] if "Eva" in c["name"])["dataUri"]
sarah = next(c for c in show["cast"] if "Sarah" in c["name"])["dataUri"]
eva_render = datauri(OUT / "ep_eva.png")

print("judging (same: Eva anchor vs Eva render) ...", flush=True)
r1 = judges.make_identity_judge(eva, "A.I. (Eva)")(eva_render)
print(f"SAME -> passed={r1.passed} score={r1.score} fb={r1.feedback}", flush=True)

print("judging (different: Eva anchor vs Sarah anchor) ...", flush=True)
r2 = judges.make_identity_judge(eva, "A.I. (Eva)")(sarah)
print(f"DIFFERENT -> passed={r2.passed} score={r2.score} fb={r2.feedback}", flush=True)

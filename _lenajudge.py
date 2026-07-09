import os, base64
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
os.environ["JUDGE_STRATEGY"] = "ollama"
import judges, vault

OUT = Path(r"C:\Users\solti\AppData\Roaming\Claude\local-agent-mode-sessions"
           r"\052aebbf-870d-4145-83e8-ff7179b1782a\8e6f879d-68f7-44e0-8e92-2909603272a8"
           r"\local_1977794e-6a98-487b-a662-bdbf3f2d4791\outputs")

def du(p):
    return "data:image/png;base64," + base64.b64encode(Path(p).read_bytes()).decode()

show = vault.load_cast_from_b2("warlords-sniper")
lena = next(c for c in show["cast"] if c["name"].lower() == "lena")["dataUri"]
arin = next(c for c in show["cast"] if "Arin" in c["name"])["dataUri"]

r1 = judges.make_identity_judge(lena, "Lena")(du(OUT / "ep_lena.png"))
print(f"SAME score={r1.score} passed={r1.passed}", flush=True)
r2 = judges.make_identity_judge(lena, "Lena")(arin)
print(f"DIFF score={r2.score} passed={r2.passed} fb={r2.feedback}", flush=True)

"""Free E2E of the self-correction loop: ComfyUI render -> mock judge fails ->
retry with lineage -> pass. Every attempt's asset + manifest on B2."""
import os, traceback
from dotenv import load_dotenv
load_dotenv()
os.environ["JUDGE_STRATEGY"] = "mock"  # deterministic: fail take 0, pass take 1

import pipeline, judges

PROMPT = "A neon-lit rain-slicked Tokyo alley at night, cinematic, 35mm"
judge = judges.make_judge(PROMPT)
try:
    out = pipeline.gen_still(PROMPT, judge, aspect_ratio="16:9",
                             run_name="loopdemo", max_iter=3)
    print("PASSED=", out["passed"], "RETAKES=", out["retakes"], flush=True)
    for it in out["iterations"]:
        print(f"  iter{it['iteration']} score={it['score']} passed={it['passed']} "
              f"run={it['run_id']} key={it['b2_key']} fb={it['feedback']}", flush=True)
    print("CHOSEN_URL=", out["chosen"]["url"], flush=True)
    prov = pipeline.read_provenance(out["chosen"]["run_id"])
    print("CHOSEN_VERIFY=", prov.get("verified"), "hash=", prov.get("canonical_hash"), flush=True)
except Exception as e:
    traceback.print_exc()
    print("ERR:", type(e).__name__, str(e)[:400], flush=True)

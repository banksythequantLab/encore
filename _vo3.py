import httpx
REF = r"B:\freeclone-backend\derek-voice.wav"
OUT = r"B:\Filmwriter-Local\video\vo\vo3.wav"
text = ("Episode one. Lena, on a rooftop over a neon city at night. Episode two. A snowy mountain "
        "ridge at dawn. Same Lena. Not a lookalike. Her actual identity, pulled from her vault "
        "anchor and edited into a brand new scene.")
with open(REF, "rb") as f:
    r = httpx.post("http://127.0.0.1:8300/api/clone",
                   files={"prompt_audio": ("ref.wav", f, "audio/wav")},
                   data={"text": text, "lang": "en"}, timeout=1800)
open(OUT, "wb").write(r.content)
print("VO3_OK", len(r.content))

import httpx
REF = r"B:\freeclone-backend\derek-voice.wav"
OUT = r"B:\Filmwriter-Local\video\vo\vo2.wav"
text = ("This is the Series Vault, living on Backblaze B2. Each character is stored as a content "
        "addressable identity anchor, with a versioned show bible. This is what lets a character "
        "come back.")
with open(REF, "rb") as f:
    r = httpx.post("http://127.0.0.1:8300/api/clone",
                   files={"prompt_audio": ("ref.wav", f, "audio/wav")},
                   data={"text": text, "lang": "en"}, timeout=1800)
open(OUT, "wb").write(r.content)
print("VO2_OK", len(r.content))

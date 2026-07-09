import httpx
REF = r"B:\freeclone-backend\derek-voice.wav"
segs = {
    "vo7": "One RTX 3090. Zero cloud credits. Unlimited episodes. And every single frame sealed with verifiable provenance on B2.",
    "vo8": "And you are not locked to local. Genblaze lets you swap in Sora, Veo, or Runway with a single line. Local today, any engine tomorrow, same provenance.",
}
for n, t in segs.items():
    with open(REF, "rb") as f:
        r = httpx.post("http://127.0.0.1:8300/api/clone",
                       files={"prompt_audio": ("ref.wav", f, "audio/wav")},
                       data={"text": t, "lang": "en"}, timeout=1800)
    open(rf"B:\Filmwriter-Local\video\vo\{n}.wav", "wb").write(r.content)
    print(n, "OK", len(r.content), flush=True)
print("VO78_DONE", flush=True)

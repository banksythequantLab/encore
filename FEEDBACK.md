# Genblaze SDK feedback (for the feedback prize)

File these as two issues at https://github.com/backblaze-labs/genblaze/issues

---

## Issue 1 — Bug: Windows `file://` local-asset transfer mangles the drive letter

**Type:** Bug report

**Summary:** On Windows, uploading a locally-generated asset through `ObjectStorageSink`
fails — the sink rejects files that are actually inside the allowed temp dir.

**Root cause:** `genblaze_core/storage/transfer.py::_read_local_file` does:
```python
path = unquote(urlparse(url).path)      # file:///C:/Users/... -> "/C:/Users/..."
resolved = Path(path).resolve()          # -> "C:Users\Users\..." (drive separator dropped)
```
`Path("/C:/Users/...").resolve()` on Windows produces a drive-relative path
(`C:Users\...`), so the `is_relative_to(temp_root)` allowlist check fails and the
upload is refused: *"local file path … is outside allowed directories."*

**Repro (Windows):** point a provider's asset URL at a file under `tempfile.gettempdir()`
via `pathlib.Path(p).as_uri()` and run a pipeline with an `ObjectStorageSink`. Every
`file://` form (`file:///C:/…`, `file://C:/…`) resolves wrong.

**Suggested fix:** on Windows, convert `file://` URLs with `urllib.request.url2pathname`
(handles the drive correctly), or strip the leading slash before a `X:` drive token.

**Workaround we used:** our provider uploads bytes to B2 itself (`backend.put` +
`get_durable_url`) and runs the pipeline sink-less.

---

## Issue 2 — Contribution offer: a self-hosted **ComfyUI** provider

**Type:** Feature request / contribution offer

**Summary:** We built a `BaseProvider` adapter that drives a local **ComfyUI** server
(`/prompt` submit, `/history` poll, `/view` fetch) so a Genblaze pipeline can generate on
your own GPU with zero API cost or quota — while still emitting standard manifests and
storing to B2. It maps ComfyUI's `{inputs, outputs, workflow}` template shape onto the
`submit/poll/fetch_output` lifecycle and handles image + video + audio workflows.

**Why it's useful:** many teams already run ComfyUI (Wan, LTX, FLUX, SDXL, Qwen-Image).
A first-class ComfyUI provider lets them adopt Genblaze provenance without moving
generation to a paid cloud — a big on-ramp.

**Happy to open a PR** following `docs/guides/new-provider.md` if there's interest.

**Minor doc note:** `Step` generation options must go in `params={...}`; several README
examples pass `duration=`, `aspect_ratio=` as top-level kwargs to `.step(...)`, which the
installed `step()` signature (0.3.4) rejects.

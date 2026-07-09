// Filmwriter (Node) -> Genblaze service (Python/FastAPI) client.
// Drop into B:\QwenShowrunner\lib\ and import from the generation agents
// (render.mjs / voice.mjs / sound.mjs) in place of the DashScope calls.
//
// Each generation now returns B2 URLs + SHA-256 + manifest URI, so the
// conductor and UI can surface provenance and the self-correction lineage.

const BASE = process.env.GENBLAZE_URL || "http://127.0.0.1:8090";

async function post(path, body) {
  const r = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`genblaze ${path} ${r.status}: ${await r.text()}`);
  return r.json();
}

// { prompt, aspect_ratio?, run_name?, max_iter? }
//   -> { passed, retakes, chosen:{url,sha256,manifest_uri,...}, iterations:[...] }
export const genStill = (opts) => post("/gen/still", opts);

// { prompt, image_url?, duration?, aspect_ratio?, run_name? } -> asset record
export const genVideo = (opts) => post("/gen/video", opts);

// { text, voice?, run_name? } -> asset record
export const genVoice = (opts) => post("/gen/voice", opts);

export async function provenance(runId) {
  const r = await fetch(`${BASE}/provenance/${encodeURIComponent(runId)}`);
  if (!r.ok) throw new Error(`genblaze provenance ${r.status}`);
  return r.json();
}

export async function health() {
  const r = await fetch(`${BASE}/health`);
  return r.json();
}

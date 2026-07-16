const BASE = "";

async function handle(res) {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed with status ${res.status}`);
  }
  return res.json();
}

export const api = {
  health: () => fetch(`${BASE}/health`).then(handle),

  createVideo: (payload) =>
    fetch(`${BASE}/videos`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }).then(handle),

  getStatus: (id) => fetch(`${BASE}/videos/${id}`).then(handle),

  getScript: (id) => fetch(`${BASE}/videos/${id}/script`).then(handle),

  approveScript: (id, editedScriptJson) =>
    fetch(`${BASE}/videos/${id}/approve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: editedScriptJson ? JSON.stringify({ approved_script_json: editedScriptJson }) : "{}",
    }).then(handle),

  downloadUrl: (id) => `${BASE}/videos/${id}/download`,
};

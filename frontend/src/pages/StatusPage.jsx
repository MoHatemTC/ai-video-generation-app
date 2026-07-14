import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/client.js";

const STAGES = [
  "queued", "script", "awaiting_review", "planning", "audio",
  "alignment", "assets", "composition", "animation", "rendering", "completed",
];

export default function StatusPage() {
  const { id } = useParams();
  const [status, setStatus] = useState(null);
  const [scriptText, setScriptText] = useState("");
  const [approving, setApproving] = useState(false);
  const [error, setError] = useState(null);
  const pollRef = useRef(null);

  useEffect(() => {
    let cancelled = false;

    async function poll() {
      try {
        const s = await api.getStatus(id);
        if (cancelled) return;
        setStatus(s);

        if (s.status === "awaiting_review" && !scriptText) {
          const script = await api.getScript(id);
          if (!cancelled) setScriptText(JSON.stringify(script, null, 2));
        }
        if (s.status !== "completed" && s.status !== "failed") {
          pollRef.current = setTimeout(poll, 2000);
        }
      } catch (err) {
        if (!cancelled) setError(err.message);
      }
    }
    poll();

    return () => {
      cancelled = true;
      clearTimeout(pollRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function handleApprove() {
    setApproving(true);
    setError(null);
    try {
      await api.approveScript(id, scriptText);
    } catch (err) {
      setError(err.message);
    } finally {
      setApproving(false);
    }
  }

  if (!status) return <div className="card">Loading…</div>;

  const currentIdx = STAGES.indexOf(status.status);

  return (
    <div className="card">
      <p>
        Job <code>{id}</code>
      </p>

      <ul className="stage-list">
        {STAGES.map((stage, i) => (
          <li key={stage} className={i < currentIdx ? "done" : i === currentIdx ? "active" : ""}>
            {i < currentIdx ? "✓" : i === currentIdx ? "●" : "○"} {stage.replace("_", " ")}
          </li>
        ))}
      </ul>

      {status.status === "awaiting_review" && (
        <>
          <label>Review &amp; edit the generated script before rendering</label>
          <textarea
            style={{ minHeight: 260, fontFamily: "monospace", fontSize: "0.85rem" }}
            value={scriptText}
            onChange={(e) => setScriptText(e.target.value)}
          />
          <button onClick={handleApprove} disabled={approving}>
            {approving ? "Starting render…" : "Approve & render video"}
          </button>
        </>
      )}

      {status.status === "failed" && <p className="error">Generation failed: {status.error_message}</p>}

      {status.status === "completed" && (
        <>
          <p>Your video is ready 🎉</p>
          <video controls src={api.downloadUrl(id)} />
          <div>
            <a href={api.downloadUrl(id)} download>
              <button>Download video</button>
            </a>
          </div>
        </>
      )}

      {error && <p className="error">{error}</p>}
    </div>
  );
}

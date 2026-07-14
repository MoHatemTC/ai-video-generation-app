import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client.js";

export default function RequestPage() {
  const [instruction, setInstruction] = useState("");
  const [tone, setTone] = useState("professional");
  const [audience, setAudience] = useState("general");
  const [lengthMinutes, setLengthMinutes] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const video = await api.createVideo({
        instruction,
        tone,
        audience,
        length_minutes: Number(lengthMinutes),
      });
      if (video.status === "failed") {
        setError(video.error_message || "Script generation failed.");
        setLoading(false);
        return;
      }
      navigate(`/videos/${video.id}`);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  }

  return (
    <div className="card">
      <p>Turn a single instruction into a complete, narration-synced e-learning video.</p>
      <form onSubmit={handleSubmit}>
        <label>What should the video be about?</label>
        <textarea
          required
          placeholder="e.g. I want a video about how photosynthesis works"
          value={instruction}
          onChange={(e) => setInstruction(e.target.value)}
        />

        <label>Tone</label>
        <select value={tone} onChange={(e) => setTone(e.target.value)}>
          <option value="professional">Professional</option>
          <option value="friendly">Friendly</option>
          <option value="energetic">Energetic</option>
        </select>

        <label>Audience level</label>
        <select value={audience} onChange={(e) => setAudience(e.target.value)}>
          <option value="general">General</option>
          <option value="beginner">Beginner</option>
          <option value="advanced">Advanced</option>
        </select>

        <label>Target length (minutes)</label>
        <input
          type="text"
          inputMode="decimal"
          value={lengthMinutes}
          onChange={(e) => setLengthMinutes(e.target.value)}
        />

        <button type="submit" disabled={loading}>
          {loading ? "Generating script…" : "Generate video"}
        </button>
        {error && <p className="error">{error}</p>}
      </form>
    </div>
  );
}

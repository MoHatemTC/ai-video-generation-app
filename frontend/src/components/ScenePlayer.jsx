import React, { useState, useEffect, useRef } from 'react';

/**
 * ScenePlayer: The Interactive Web Render Player
 * Renders the live interactive HTML video directly inside an iframe or custom canvas controls.
 */
export default function ScenePlayer({ jobId, scriptData, audioData, timestampData, assetData }) {
  const [mode, setMode] = useState('rendered'); // 'rendered' or 'canvas'
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const audioRef = useRef(null);

  const renderUrl = jobId ? `http://localhost:8000/api/render/${jobId}` : null;

  useEffect(() => {
    if (audioRef.current) {
      if (isPlaying) audioRef.current.play();
      else audioRef.current.pause();
    }
  }, [isPlaying]);

  const handleTimeUpdate = () => {
    if (audioRef.current) setCurrentTime(audioRef.current.currentTime);
  };

  const getActiveContent = () => {
    if (!scriptData?.segments) return null;
    const segmentIndex = Math.floor(currentTime / 5);
    return scriptData.segments[segmentIndex] || scriptData.segments[0];
  };

  const activeContent = getActiveContent();

  return (
    <div className="w-full h-full bg-slate-900 rounded-xl overflow-hidden relative flex flex-col group">
      {/* Top Controls Bar */}
      <div className="bg-slate-950/80 backdrop-blur-md px-4 py-2 flex items-center justify-between border-b border-white/10 text-xs text-slate-300 z-10">
        <span className="font-semibold text-teal-400 flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          Live Interactive Player
        </span>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setMode('rendered')}
            className={`px-2.5 py-1 rounded-md transition-all ${mode === 'rendered' ? 'bg-blue-600 text-white font-bold' : 'hover:bg-white/10 text-slate-400'}`}
          >
            Rendered HTML
          </button>
          <button
            onClick={() => setMode('canvas')}
            className={`px-2.5 py-1 rounded-md transition-all ${mode === 'canvas' ? 'bg-blue-600 text-white font-bold' : 'hover:bg-white/10 text-slate-400'}`}
          >
            Subtitle Preview
          </button>
        </div>
      </div>

      {/* Primary Display Area */}
      <div className="flex-1 relative w-full h-full bg-black">
        {mode === 'rendered' && renderUrl ? (
          <iframe
            src={renderUrl}
            title="Rendered Educational Video"
            className="w-full h-full border-none"
            allow="autoplay; fullscreen"
          />
        ) : (
          <div className="w-full h-full flex flex-col justify-between p-8">
            <div className="flex-1 flex items-center justify-center">
              <div className="bg-white/5 backdrop-blur-md p-6 rounded-2xl border border-white/10 w-full max-w-lg text-center shadow-xl">
                <h3 className="text-teal-400 font-bold mb-4 uppercase tracking-widest text-xs">Visual Cue</h3>
                <p className="text-white text-xl leading-relaxed">{activeContent?.visual_cue || "Initializing course preview..."}</p>
              </div>
            </div>

            <div className="bg-black/90 p-5 rounded-xl border border-white/10 text-center">
              <p className="text-white text-base font-medium italic">
                {activeContent?.narrator_text || "..."}
              </p>
            </div>

            {audioData?.audio_file_path && (
              <audio
                ref={audioRef}
                src={audioData.audio_file_path}
                onTimeUpdate={handleTimeUpdate}
                className="hidden"
              />
            )}

            <div className="absolute bottom-6 right-6 z-20">
              <button
                onClick={() => setIsPlaying(!isPlaying)}
                className="bg-emerald-500 hover:bg-emerald-400 text-black font-bold py-2.5 px-5 rounded-full shadow-xl transition-all hover:scale-105"
              >
                {isPlaying ? "Pause" : "Play Voiceover"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
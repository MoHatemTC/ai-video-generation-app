import React, { useState, useEffect, useRef } from 'react';

/**
 * ScenePlayer: The Web-Based Render Engine
 * Replaces the need for a backend composition service.
 * It takes the raw pipeline stages and syncs them in the browser.
 */
export default function ScenePlayer({ scriptData, audioData, timestampData, assetData }) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const audioRef = useRef(null);

  useEffect(() => {
    if (audioRef.current) {
      if (isPlaying) audioRef.current.play();
      else audioRef.current.pause();
    }
  }, [isPlaying]);

  const handleTimeUpdate = () => {
    if (audioRef.current) setCurrentTime(audioRef.current.currentTime);
  };

  // Get active text and visual cue based on the current audio timestamp
  const getActiveContent = () => {
    if (!scriptData?.segments || !timestampData?.word_timestamps) return null;
    
    // Simple sync logic: Map current time to the closest script segment
    // In a production app, we would use the WhisperX timestamps here
    const segmentIndex = Math.floor(currentTime / 5); // Rough estimation
    return scriptData.segments[segmentIndex] || scriptData.segments[0];
  };

  const activeContent = getActiveContent();

  if (!scriptData || !audioData) {
    return (
      <div className="w-full h-full bg-slate-900 rounded-xl flex items-center justify-center text-gray-500 font-mono">
        Loading Render Engine...
      </div>
    );
  }

  return (
    <div className="w-full h-full bg-slate-900 rounded-xl overflow-hidden relative flex flex-col">
      {/* Visual Canvas */}
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="bg-white/5 backdrop-blur-md p-6 rounded-2xl border border-white/10 w-full max-w-lg text-center">
            <h3 className="text-teal-400 font-bold mb-4 uppercase tracking-widest text-xs">Visual Cue</h3>
            <p className="text-white text-xl">{activeContent?.visual_cue || "Initializing..."}</p>
        </div>
      </div>

      {/* Subtitle Bar */}
      <div className="bg-black/80 p-6 text-center">
        <p className="text-white text-lg font-medium italic">
            {activeContent?.narrator_text || "..."}
        </p>
      </div>

      {/* Audio Controller */}
      <audio 
        ref={audioRef} 
        src={audioData.audio_file_path} 
        onTimeUpdate={handleTimeUpdate}
        className="hidden"
      />
      
      <div className="absolute bottom-20 right-8">
        <button 
          onClick={() => setIsPlaying(!isPlaying)}
          className="bg-teal-500 hover:bg-teal-400 text-black font-bold py-3 px-6 rounded-full shadow-lg transition-all"
        >
          {isPlaying ? "Pause" : "Play Course"}
        </button>
      </div>
    </div>
  );
}
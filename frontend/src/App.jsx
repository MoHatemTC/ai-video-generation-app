import { useState, useEffect, useRef } from 'react';
import { Loader2, CheckCircle2, AlertCircle, Terminal, ChevronDown, ChevronUp, Sparkles, Download, ArrowRight, ShieldCheck } from 'lucide-react';

const PIPELINE_STAGES = [
  { id: 'generating_script', label: 'Script Generation (Ahmed)', dataKey: 'script_data' },
  { id: 'planning_scenes', label: 'Scene Planning (Mostafa)', dataKey: 'scene_data' },
  { id: 'generating_audio', label: 'Voiceover TTS (Mahdy)', dataKey: 'audio_metadata' },
  { id: 'aligning_timestamps', label: 'WhisperX Alignment (Osama)', dataKey: 'timestamp_data' },
  { id: 'fetching_assets', label: 'Asset Service (Omar)', dataKey: 'asset_data' },
  { id: 'composing_scenes', label: 'Composition (Nada)', dataKey: 'composition_data' },
  { id: 'animating', label: 'Animation & Render (Youssef)', dataKey: 'animation_data' },
  { id: 'completed', label: 'Video Ready', dataKey: null }
];

const API_BASE_URL = (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_BASE_URL) || 'http://localhost:8000';

export default function App() {
  const [prompt, setPrompt] = useState('explain LangChain');
  const [jobId, setJobId] = useState(null);
  const [currentStatus, setCurrentStatus] = useState('idle');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [progress, setProgress] = useState(0);
  const [errorMsg, setErrorMsg] = useState(null);
  const [videoUrl, setVideoUrl] = useState(null);
  
  const [stageData, setStageData] = useState({});
  const [expandedStages, setExpandedStages] = useState({});
  const [completedStages, setCompletedStages] = useState(new Set());
  
  const fetchedKeys = useRef(new Set());

  useEffect(() => {
    let intervalId;

    const checkStatus = async () => {
      if (!jobId) return;

      try {
        const response = await fetch(`${API_BASE_URL}/api/status/${jobId}`);
        if (!response.ok) throw new Error('Failed to fetch status from server');
        
        const data = await response.json();
        setCurrentStatus(data.status);
        if (data.video_url) setVideoUrl(data.video_url);
        if (data.error_message) setErrorMsg(data.error_message);

        const currentIndex = PIPELINE_STAGES.findIndex(s => s.id === data.status);
        if (currentIndex >= 0) {
          setProgress(Math.round(((currentIndex + 1) / PIPELINE_STAGES.length) * 100));
        } else if (data.status === 'completed') {
          setProgress(100);
        } else if (data.status === 'failed') {
          setProgress(67);
        }

        const isFinishedOrFailed = data.status === 'completed' || data.status === 'failed';
        const stagesToFetch = PIPELINE_STAGES.filter((stage, idx) => 
          stage.dataKey && !fetchedKeys.current.has(stage.dataKey) && (
            isFinishedOrFailed || currentIndex > idx || data.status === stage.id
          )
        );

        for (const stage of stagesToFetch) {
          try {
            const dataRes = await fetch(`${API_BASE_URL}/api/data/${jobId}/${stage.dataKey}`);
            if (dataRes.ok) {
              const stageJson = await dataRes.json();
              if (stageJson[stage.dataKey] !== undefined && stageJson[stage.dataKey] !== null) {
                const payload = stageJson[stage.dataKey];
                setStageData(prev => ({...prev, [stage.dataKey]: payload}));
                fetchedKeys.current.add(stage.dataKey);
                setCompletedStages(prev => new Set(prev).add(stage.dataKey));
              }
            }
          } catch (e) {
            console.error("Failed to fetch stage data", e);
          }
        }

        if (data.status === 'completed' || data.status === 'failed') {
          clearInterval(intervalId);
        }
      } catch (err) {
        console.error("Polling error:", err);
      }
    };

    if (jobId && currentStatus !== 'completed' && currentStatus !== 'failed') {
      intervalId = setInterval(checkStatus, 2000);
    }

    return () => clearInterval(intervalId);
  }, [jobId, currentStatus]);

  const handleGenerate = async (e) => {
    e.preventDefault();
    if (!prompt || !prompt.trim() || isSubmitting || jobId !== null) return;

    setIsSubmitting(true);
    setJobId(null);
    setVideoUrl(null);
    setErrorMsg(null);
    setStageData({});
    setCompletedStages(new Set());
    fetchedKeys.current.clear();
    setCurrentStatus('pending');
    setProgress(5);

    try {
      const res = await fetch(`${API_BASE_URL}/api/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: prompt.trim() })
      });

      if (!res.ok) throw new Error('Failed to start video generation job');
      
      const data = await res.json();
      setJobId(data.job_id);
      setCurrentStatus(data.status);
    } catch (err) {
      setErrorMsg(err.message);
      setCurrentStatus('failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  const toggleStageExpand = (key) => {
    setExpandedStages(prev => ({...prev, [key]: !prev[key]}));
  };

  return (
    <div className="min-h-screen bg-[#FBFBFD] text-[#0F172B] font-sans selection:bg-blue-100 selection:text-blue-900">
      <header className="bg-[#FBFBFC] fixed top-0 z-50 max-h-20 w-full border-b border-gray-100 shadow-sm">
        <nav className="flex items-center justify-between mx-auto max-w-7xl px-4 sm:px-8 h-20">
          <div className="flex items-center gap-2">
            <a href="/" className="block">
              <img src="https://sprintscdn-fnh2cugtb8a4deba.z02.azurefd.net/production/files/17845432766a5df82c15dcd.svg" className="w-32 h-8" alt="Sprints Logo" />
            </a>
          </div>
          <div className="hidden lg:flex items-center gap-8 text-sm text-gray-700 font-medium">
            <span className="hover:text-blue-600 cursor-pointer">Learn</span>
            <span className="hover:text-blue-600 cursor-pointer">Virtual Internship</span>
            <span className="hover:text-blue-600 cursor-pointer">For Businesses</span>
          </div>
          <div className="flex items-center gap-4">
            <button className="bg-blue-600 hover:bg-blue-700 text-white py-2 px-6 rounded-lg font-semibold shadow-md transition-all">
              Dashboard
            </button>
          </div>
        </nav>
      </header>

      <main className="pt-28 pb-16 px-4 max-w-5xl mx-auto">
        <div className="text-center mb-10">
          <span className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-blue-50 text-blue-700 text-xs font-semibold mb-4 border border-blue-100">
            <Sparkles className="w-3.5 h-3.5" /> AI Micro-Agent Orchestrator
          </span>
          <h1 className="text-3xl lg:text-5xl font-extrabold text-gray-900 tracking-tight mb-4">
            AI-Guided Learning That Gets You Job-Ready, <span className="bg-gradient-to-r from-[#004EFF] to-[#33D7D1] bg-clip-text text-transparent">Faster.</span>
          </h1>
          <p className="text-gray-600 max-w-2xl mx-auto text-base lg:text-lg mb-8">
            Enter a topic, and our multi-agent architecture will instantly generate a complete, timed, and rendered educational video tailored for your students.
          </p>

          <form onSubmit={handleGenerate} className="flex flex-col sm:flex-row items-center gap-3 bg-white p-2 rounded-2xl shadow-xl border border-gray-200 max-w-2xl mx-auto">
            <input
              type="text"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="e.g., Explain Python decorators or Quantum Computing..."
              className="w-full px-4 py-3 rounded-xl border-none focus:outline-none text-gray-800 text-base"
            />
            <button
              type="submit"
              disabled={isSubmitting || (currentStatus !== 'idle' && currentStatus !== 'completed' && currentStatus !== 'failed' && jobId !== null)}
              className="w-full sm:w-auto bg-[#004EFF] hover:bg-blue-700 text-white font-semibold px-8 py-3.5 rounded-xl whitespace-nowrap shadow-lg flex items-center justify-center gap-2 transition-all disabled:opacity-50"
            >
              {isSubmitting || (currentStatus !== 'idle' && currentStatus !== 'completed' && currentStatus !== 'failed' && jobId !== null) ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" /> Generating...
                </>
              ) : (
                <>
                  Generate Course <ArrowRight className="w-5 h-5" />
                </>
              )}
            </button>
          </form>
        </div>

        {errorMsg && (
          <div className="mb-8 p-6 bg-red-50 border border-red-200 rounded-2xl flex items-start gap-4 text-red-800 shadow-sm">
            <AlertCircle className="w-6 h-6 flex-shrink-0 mt-0.5 text-red-600" />
            <div>
              <h3 className="font-bold text-lg">Pipeline Interrupted</h3>
              <p className="text-sm mt-1">{errorMsg}</p>
            </div>
          </div>
        )}

        {jobId && (
          <div className="bg-white rounded-3xl p-6 lg:p-8 shadow-xl border border-gray-100 mb-8">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
              <div>
                <h2 className="text-xl font-bold text-gray-900">Generation Progress</h2>
                <p className="text-xs text-gray-500 font-mono mt-1">Job ID: {jobId}</p>
              </div>
              <div className="text-3xl font-extrabold text-blue-600">
                {progress}%
              </div>
            </div>

            <div className="w-full bg-gray-100 h-3 rounded-full overflow-hidden mb-8">
              <div 
                className="bg-gradient-to-r from-blue-600 to-teal-400 h-full transition-all duration-500 rounded-full"
                style={{ width: `${progress}%` }}
              ></div>
            </div>

            <div className="space-y-3">
              <h4 className="text-xs uppercase tracking-wider text-gray-400 font-bold mb-4">Pipeline Execution Log & State Data</h4>
              {PIPELINE_STAGES.map((stage, idx) => {
                const isCompleted = completedStages.has(stage.dataKey) || currentStatus === 'completed' || (stage.dataKey && stageData[stage.dataKey] !== undefined && stageData[stage.dataKey] !== null);
                const isCurrent = currentStatus === stage.id || (idx === 0 && currentStatus === 'pending');
                const hasData = stage.dataKey && stageData[stage.dataKey] !== undefined && stageData[stage.dataKey] !== null;
                const isExpanded = expandedStages[stage.dataKey];

                return (
                  <div key={stage.id} className="border border-gray-100 rounded-2xl p-4 bg-gray-50/50 transition-all">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        {isCompleted ? (
                          <CheckCircle2 className="w-5 h-5 text-green-500 flex-shrink-0" />
                        ) : isCurrent ? (
                          <Loader2 className="w-5 h-5 text-blue-600 animate-spin flex-shrink-0" />
                        ) : (
                          <div className="w-5 h-5 rounded-full border-2 border-gray-300 flex-shrink-0"></div>
                        )}
                        <span className={`text-sm font-semibold ${isCurrent ? 'text-blue-600 font-bold' : isCompleted ? 'text-gray-800' : 'text-gray-400'}`}>
                          Stage {idx + 1}: {stage.label}
                        </span>
                      </div>

                      {hasData && (
                        <button
                          onClick={() => toggleStageExpand(stage.dataKey)}
                          className="text-xs flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-50 text-blue-700 hover:bg-blue-100 font-medium transition-colors"
                        >
                          <Terminal className="w-3.5 h-3.5" />
                          {isExpanded ? 'Hide Payload' : 'Inspect JSON'}
                          {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                        </button>
                      )}
                    </div>

                    {hasData && isExpanded && (
                      <div className="mt-4 bg-[#0F172B] text-teal-300 p-4 rounded-xl font-mono text-xs overflow-x-auto shadow-inner border border-slate-800">
                        <pre>{JSON.stringify(stageData[stage.dataKey], null, 2)}</pre>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {videoUrl && (
              <div className="mt-10 p-6 bg-gradient-to-br from-blue-50 to-teal-50 rounded-2xl border border-blue-200 text-center">
                <h3 className="text-2xl font-extrabold text-gray-900 mb-2 flex items-center justify-center gap-2">
                  <ShieldCheck className="w-6 h-6 text-blue-600" /> Video Render Complete!
                </h3>
                <p className="text-gray-600 text-sm mb-6">Your AI-generated course has been successfully stitched and rendered.</p>
                
                <div className="aspect-video max-w-2xl mx-auto rounded-xl overflow-hidden shadow-2xl bg-black mb-6">
                  <video src={videoUrl} controls className="w-full h-full object-cover" />
                </div>

                <a
                  href={videoUrl}
                  download
                  className="inline-flex items-center gap-2 bg-[#004EFF] hover:bg-blue-700 text-white font-bold px-8 py-4 rounded-xl shadow-lg transition-all text-base"
                >
                  <Download className="w-5 h-5" /> Download Final Video (.mp4)
                </a>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
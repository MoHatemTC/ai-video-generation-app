import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from backend.app.pipeline.orchestrator import process_video_job
from backend.app.schemas.script import VideoScriptBlueprint, ScriptSegment

@pytest.fixture
def mock_script_data():
    """Provides a valid Pydantic model so we don't need to call the real LLM."""
    return VideoScriptBlueprint(
        title="Test Video",
        target_audience="Beginners",
        estimated_total_duration=60,
        segments=[
            ScriptSegment(segment_id=1, narrator_text="Hello world", visual_cue="Intro")
        ]
    )

@pytest.mark.asyncio
@patch("backend.app.pipeline.orchestrator.SceneDirector")
@patch("backend.app.pipeline.orchestrator.ScenePlanner")
@patch("backend.app.pipeline.orchestrator.process_scene_elements", new_callable=AsyncMock)
@patch("backend.app.pipeline.orchestrator.AlignmentService")
@patch("backend.app.pipeline.orchestrator.generate_voiceover", new_callable=AsyncMock)
@patch("backend.app.pipeline.orchestrator.generate_script", new_callable=AsyncMock)
@patch("backend.app.pipeline.orchestrator.asyncio.to_thread", new_callable=AsyncMock)
async def test_process_video_job_success(
    mock_to_thread, mock_generate_script, mock_generate_voiceover, mock_alignment_service, mock_process_scene, mock_planner_cls, mock_director_cls, mock_script_data
):
    """Test that the fully integrated pipeline successfully finishes."""
    
    # 1. Setup Supabase Mocks
    mock_supabase = MagicMock()
    mock_table = MagicMock()
    mock_update = MagicMock()
    mock_eq = MagicMock()
    
    mock_supabase.table.return_value = mock_table
    mock_table.update.return_value = mock_update
    mock_update.eq.return_value = mock_eq
    mock_eq.execute = MagicMock() 

    # 2. Setup Agent Mocks
    # Stage 1: Mock the LLM Script Agent
    mock_generate_script.return_value = mock_script_data

    # Stage 2: Mock Scene Planner & Director
    mock_planner = MagicMock()
    mock_plan = MagicMock()
    mock_plan.model_dump.return_value = {"scenes": [], "video_id": "test-job-123", "title": "Test Video", "total_duration_seconds": 60.0}
    mock_planner.plan_scenes = AsyncMock(return_value=mock_plan)
    mock_planner_cls.return_value = mock_planner

    mock_director = MagicMock()
    mock_report = MagicMock()
    mock_report.passed = True
    mock_report.overall_score = 95
    mock_director.evaluate = AsyncMock(return_value=mock_report)
    mock_director_cls.return_value = mock_director
    
    # Stage 3: Mock the Voiceover Service
    mock_generate_voiceover.return_value = {"local_path": "fake_audio.wav"}

    # Stage 5: Mock Omar's Asset Service
    mock_process_scene.return_value = {"assets": []}

    # 3. Setup Asyncio Thread Mocks (For WhisperX Alignment)
    mock_to_thread.side_effect = [
        {"word_timestamps": []}                         # Stage 4: WhisperX Alignment
    ]

    job_id = "test-job-123"
    prompt = "Test prompt"
    
    # 4. Run the pipeline
    await process_video_job(prompt, job_id=job_id, supabase_client=mock_supabase)

    # 5. Verify it marked the job as completed
    completed_call = {"status": "completed", "video_url": f"/renders/{job_id}.html"}
    update_args = [call.args[0] for call in mock_table.update.call_args_list]
    
    assert completed_call in update_args, "Pipeline did not reach completed state!"

@pytest.mark.asyncio
@patch("backend.app.pipeline.orchestrator.generate_script", new_callable=AsyncMock)
async def test_process_video_job_failure(mock_generate_script):
    """Test that the orchestrator catches an AI crash and securely updates the DB."""
    
    mock_supabase = MagicMock()
    mock_table = MagicMock()
    mock_update = MagicMock()
    mock_eq = MagicMock()
    
    mock_supabase.table.return_value = mock_table
    mock_table.update.return_value = mock_update
    mock_update.eq.return_value = mock_eq
    mock_eq.execute = MagicMock() 
    
    # Force the Script Agent to crash on Stage 1
    mock_generate_script.side_effect = Exception("LiteLLM API Timeout!")
    
    job_id = "test-job-fail"
    prompt = "Fail prompt"
    
    await process_video_job(prompt, job_id=job_id, supabase_client=mock_supabase)
    
    # Verify the failure was caught and logged to Supabase safely with the stage name
    failed_call = {"status": "failed", "error_message": "[script_generation] LiteLLM API Timeout!"}
    update_args = [call.args[0] for call in mock_table.update.call_args_list]
    
    assert failed_call in update_args, "Pipeline did not properly record the failure state!"
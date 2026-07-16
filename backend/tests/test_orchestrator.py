import pytest
from unittest.mock import MagicMock, patch
from backend.app.pipeline.orchestrator import process_video_job

@pytest.mark.asyncio
@patch("backend.app.pipeline.orchestrator.asyncio.to_thread")
async def test_process_video_job_success(mock_to_thread):
    """Test that the 8-stage pipeline successfully finishes."""
    
    # 1. Setup Supabase Mocks (so we don't hit the real DB during tests)
    mock_supabase = MagicMock()
    mock_table = MagicMock()
    mock_update = MagicMock()
    mock_eq = MagicMock()
    
    mock_supabase.table.return_value = mock_table
    mock_table.update.return_value = mock_update
    mock_update.eq.return_value = mock_eq
    mock_eq.execute = MagicMock() 

    # 2. Setup CrewAI Mocks (simulate the 8 sequential outputs from the agents)
    # This prevents the test from actually trying to call OpenAI
    mock_to_thread.side_effect = [
        {"title": "Script", "segments": []},             # Stage 1: Transcript
        {"scenes": []},                                  # Stage 2: Planner
        {"audio_path": "/tmp/audio.wav"},                # Stage 3: Voiceover
        {"word_timestamps": []},                         # Stage 4: Alignment
        {"assets": []},                                  # Stage 5: Assets
        {"composition_map": "ready"},                    # Stage 6: Composition
        {"status": "animation_map_ready"},               # Stage 7: Animation
        "https://s3.bucket/final_educational_video.mp4"  # Stage 8: Render
    ]

    job_id = "test-job-123"
    prompt = "Test prompt"
    
    # 3. Run the pipeline
    await process_video_job(job_id, prompt, mock_supabase)

    # 4. Verify it marked the job as completed with the final MP4 URL
    completed_call = {"status": "completed", "video_url": "https://s3.bucket/final_educational_video.mp4"}
    
    # Extract all the dictionary arguments passed to supabase.table().update()
    update_args = [call.args[0] for call in mock_table.update.call_args_list]
    
    assert completed_call in update_args, "Pipeline did not reach completed state!"

    # 5. Verify all 8 status updates were made (one per stage + completed)
    status_updates = [a.get("status") for a in update_args if "status" in a]
    expected_statuses = [
        "generating_script", "planning_scenes", "generating_audio",
        "aligning_timestamps", "fetching_assets", "composing_scenes",
        "animating", "rendering", "completed"
    ]
    assert status_updates == expected_statuses, (
        f"Status progression mismatch!\nExpected: {expected_statuses}\nGot:      {status_updates}"
    )


@pytest.mark.asyncio
@patch("backend.app.pipeline.orchestrator.asyncio.to_thread")
async def test_process_video_job_failure(mock_to_thread):
    """Test that the orchestrator catches an AI crash and securely updates the DB."""
    
    mock_supabase = MagicMock()
    mock_table = MagicMock()
    mock_update = MagicMock()
    mock_eq = MagicMock()
    
    mock_supabase.table.return_value = mock_table
    mock_table.update.return_value = mock_update
    mock_update.eq.return_value = mock_eq
    mock_eq.execute = MagicMock() 
    
    # Force CrewAI to crash on the very first stage
    mock_to_thread.side_effect = Exception("CrewAI API Key Missing!")
    
    job_id = "test-job-fail"
    prompt = "Fail prompt"
    
    await process_video_job(job_id, prompt, mock_supabase)
    
    # Verify the failure was caught and logged to Supabase safely
    # Error message now includes the stage name prefix
    update_args = [call.args[0] for call in mock_table.update.call_args_list]
    
    failed_updates = [a for a in update_args if a.get("status") == "failed"]
    assert len(failed_updates) == 1, "Pipeline did not properly record the failure state in the DB!"
    assert "[transcript]" in failed_updates[0]["error_message"], (
        "Error message should include the stage name that failed!"
    )


@pytest.mark.asyncio
@patch("backend.app.pipeline.orchestrator.asyncio.to_thread")
async def test_process_video_job_mid_pipeline_failure(mock_to_thread):
    """Test that a failure at Stage 5 (assets) records the correct failing stage."""
    
    mock_supabase = MagicMock()
    mock_table = MagicMock()
    mock_update = MagicMock()
    mock_eq = MagicMock()
    
    mock_supabase.table.return_value = mock_table
    mock_table.update.return_value = mock_update
    mock_update.eq.return_value = mock_eq
    mock_eq.execute = MagicMock()
    
    # Stages 1-4 succeed, Stage 5 (assets) fails
    mock_to_thread.side_effect = [
        {"title": "Script", "segments": []},     # Stage 1: OK
        {"scenes": []},                          # Stage 2: OK
        {"audio_path": "/tmp/audio.wav"},        # Stage 3: OK
        {"word_timestamps": []},                 # Stage 4: OK
        Exception("Image generation API limit"), # Stage 5: FAIL
    ]
    
    job_id = "test-job-mid-fail"
    prompt = "Mid-pipeline failure test"
    
    await process_video_job(job_id, prompt, mock_supabase)
    
    update_args = [call.args[0] for call in mock_table.update.call_args_list]
    
    failed_updates = [a for a in update_args if a.get("status") == "failed"]
    assert len(failed_updates) == 1, "Should record exactly one failure"
    assert "[assets]" in failed_updates[0]["error_message"], (
        "Error should identify 'assets' as the failing stage"
    )
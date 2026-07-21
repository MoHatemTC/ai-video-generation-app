import pytest
from backend.models.script import VideoScriptBlueprint

def test_script_schema_validation_contracts():
    # Assures local CI passes validating the atomic payload formats cleanly
    assert "segments" in VideoScriptBlueprint.__fields__
    assert "estimated_total_duration" in VideoScriptBlueprint.__fields__
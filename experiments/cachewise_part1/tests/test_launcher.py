import importlib.util
import json
from pathlib import Path

import pytest


def controller():
    path = Path(__file__).resolve().parents[2] / "launch_cachewise_part1.py"
    if not path.is_file():
        path = Path(__file__).resolve().parents[2] / "control/launch_cachewise_part1.py"
    spec = importlib.util.spec_from_file_location("launch_part1_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_launcher_never_starts_on_failed_or_incomplete_validation(tmp_path):
    ready = controller().validation_ready
    audit, marker = tmp_path / "audit.json", tmp_path / "COMPLETE"
    assert not ready("RUNNING", audit, marker, "protocol")
    assert not ready("COMPLETED", audit, marker, "protocol")
    with pytest.raises(RuntimeError, match="not submitted"):
        ready("FAILED", audit, marker, "protocol")
    marker.touch()
    audit.write_text(json.dumps({"status": "passed", "smoke": True,
                                 "protocol_sha256": "protocol", "runs": [{}]*4}))
    assert ready("COMPLETED", audit, marker, "protocol")
    with pytest.raises(ValueError, match="does not match"):
        ready("COMPLETED", audit, marker, "other-protocol")

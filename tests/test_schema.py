import json
from pathlib import Path

from defiagent_x_lite.domain import WorkflowPlan


def test_committed_schema_matches_model() -> None:
    path = Path("src/defiagent_x_lite/schemas/workflow-plan-v1.schema.json")
    assert json.loads(path.read_text(encoding="utf-8")) == WorkflowPlan.model_json_schema()

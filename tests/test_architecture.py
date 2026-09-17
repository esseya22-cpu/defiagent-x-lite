from pathlib import Path


def test_guard_does_not_import_grader() -> None:
    guard_root = Path("src/defiagent_x_lite/guards")
    text = "\n".join(path.read_text(encoding="utf-8") for path in guard_root.glob("*.py"))
    assert "import grader" not in text
    assert "from ..grader" not in text


def test_grader_does_not_import_guard_or_policy() -> None:
    text = Path("src/defiagent_x_lite/grader.py").read_text(encoding="utf-8")
    assert "import guard" not in text
    assert "from .guards" not in text
    assert "from .policy" not in text


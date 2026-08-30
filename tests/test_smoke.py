import importlib

def test_python_package_importable() -> None:
    module = importlib.import_module("defiagent_x_lite")
    assert module.__name__ == "defiagent_x_lite"

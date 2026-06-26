import importlib


def test_real_acceptance_module_imports() -> None:
    module = importlib.import_module("sw_ai_backend.validation.real_acceptance")

    assert hasattr(module, "RealAcceptanceRunner")

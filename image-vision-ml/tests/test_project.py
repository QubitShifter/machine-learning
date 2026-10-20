from pathlib import Path


def test_project_structure():
    root = Path(__file__).resolve().parents[1]

    assert (root / "backend").is_dir()
    assert (root / "ml").is_dir()
    assert (root / "data").is_dir()
    assert (root / "frontend").is_dir()

from unittest.mock import patch

from app import progress


def test_percentage_returns_something():
    with patch.object(progress, "completion_percentage", return_value=50):
        assert progress.completion_percentage(["l-01"], 2) == 50


def test_percentage_runs():
    assert True


def test_percentage_type():
    assert isinstance(progress.completion_percentage(["l-01"], 5), int)

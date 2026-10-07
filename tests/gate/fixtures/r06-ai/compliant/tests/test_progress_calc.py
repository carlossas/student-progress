from app.progress import completion_percentage


def test_percentage_of_catalog():
    assert completion_percentage(["l-01", "l-02", "l-03"], 5) == 60


def test_percentage_rounds_to_nearest():
    assert completion_percentage(["l-01", "l-02"], 3) == 67


def test_no_lessons_is_zero():
    assert completion_percentage([], 0) == 0


def test_duplicates_count_once():
    assert completion_percentage(["l-01", "l-01", "l-02"], 4) == 50


def test_everything_completed_is_100():
    assert completion_percentage(["l-01", "l-02"], 2) == 100

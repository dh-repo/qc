from app.main import add, multiply


def test_add() -> None:
    assert add(1, 2) == 3
    assert add(0, 0) == 0


def test_multiply() -> None:
    assert multiply(2, 3) == 6

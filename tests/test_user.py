import pytest

from src.utils.user import User


def test_user_to_dict_roundtrip_fields() -> None:
    user = User(1, "alice", "secret", "admin")
    d = user.to_dict()
    assert d == {"id": 1, "username": "alice", "password": "secret", "role": "admin"}


def test_user_getitem_valid_and_invalid() -> None:
    user = User(2, "bob", "x", "user")
    assert user["username"] == "bob"
    with pytest.raises(KeyError):
        _ = user["missing_attr"]


def test_user_setitem_valid_and_invalid() -> None:
    user = User(3, "c", "p", "user")
    user["username"] = "carol"
    assert user.username == "carol"
    with pytest.raises(KeyError):
        user["unknown"] = 1


def test_user_modify_optional_fields() -> None:
    user = User(4, "d", "pw", "user")
    user.modify(username="dan", password="newpw")
    assert user.username == "dan"
    assert user.password == "newpw"
    user.modify()
    assert user.username == "dan"

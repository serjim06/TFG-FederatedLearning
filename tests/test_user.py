import pytest

from src.utils.user import User


def test_user_to_dict_roundtrip_fields() -> None:
    user = User(1, "alice", "admin", "hash_a", "hash_r")
    d = user.to_dict()
    assert d == {
        "id": 1,
        "username": "alice",
        "role": "admin",
        "password_hash": "hash_a",
        "recovery_phrase_hash": "hash_r",
        "creation_date": None,
        "last_login": None,
        "last_train": None,
    }


def test_user_getitem_valid_and_invalid() -> None:
    user = User(2, "bob", "user")
    assert user["username"] == "bob"
    with pytest.raises(KeyError):
        _ = user["missing_attr"]


def test_user_setitem_valid_and_invalid() -> None:
    user = User(3, "c", "user")
    user["username"] = "carol"
    assert user.username == "carol"
    with pytest.raises(KeyError):
        user["unknown"] = 1


def test_user_modify_optional_fields() -> None:
    user = User(4, "d", "user")
    user.modify(username="dan", password_hash="new_hash", recovery_phrase_hash="new_phrase")
    assert user.username == "dan"
    assert user.password_hash == "new_hash"
    assert user.recovery_phrase_hash == "new_phrase"
    user.modify()
    assert user.username == "dan"

# coding=utf-8

import pytest

from foris.ubus.sessions import UbusSession, SessionDestroyed, SessionNotFound, SessionReadOnly

TIMEOUT = 60


class NonSerializable:
    pass


@pytest.fixture
def session_fixture():
    session = UbusSession(TIMEOUT)
    session["test1"] = 1
    session["test2"] = "2"
    session["test3"] = True
    session.save()
    yield session.session_id
    session.destroy()


def test_create_session():
    session = UbusSession(TIMEOUT)
    assert session.expires_in == TIMEOUT
    assert len(session) == 0
    assert [e for e in session] == []
    session.destroy()


def test_obtain_session(session_fixture):
    session = UbusSession(TIMEOUT, session_fixture)
    assert session.expires_in == TIMEOUT
    assert len(session) == 3
    assert sorted([e for e in session]) == ["test1", "test2", "test3"]
    assert session["test1"] == 1
    assert session["test2"] == "2"
    assert session["test3"]
    assert session.get("test3", False)


def test_save():
    session = UbusSession(TIMEOUT)
    session["test1"] = 1
    session["test2"] = 2
    session["test3"] = 3
    session.save()

    session = UbusSession(TIMEOUT, session_id=session.session_id)
    assert len(session) == 3
    assert sorted([e for e in session]) == ["test1", "test2", "test3"]
    assert [session[s] for s in sorted([e for e in session])] == [1, 2, 3]
    assert session["test1"] == 1
    assert session["test2"] == 2
    assert session["test3"] == 3
    assert "test1" in session
    assert "test2" in session
    assert "test3" in session

    del session["test2"]
    session["test1"] = 0
    session["test4"] = 4
    session["test5"] = 5
    session.save()

    session = UbusSession(TIMEOUT, session_id=session.session_id)
    assert len(session) == 4
    assert sorted([e for e in session]) == ["test1", "test3", "test4", "test5"]
    assert [session[s] for s in sorted([e for e in session])] == [0, 3, 4, 5]
    assert session["test1"] == 0
    assert session["test2"] is None
    assert session["test3"] == 3
    assert session["test4"] == 4
    assert session["test5"] == 5
    assert session.get("test2") is None
    assert session.get("test2", True)
    assert session.get("test5", False) == 5

    assert "test1" in session
    assert "test2" not in session
    assert "test3" in session
    assert "test4" in session
    assert "test5" in session

    session.destroy()


def test_destroy(session_fixture):
    session = UbusSession(TIMEOUT, session_fixture)
    session.destroy()

    with pytest.raises(SessionDestroyed):
        session.save()

    with pytest.raises(SessionDestroyed):
        session.destroy()

    with pytest.raises(SessionDestroyed):
        session["test1"]

    with pytest.raises(SessionDestroyed):
        session["test2"] = 5

    with pytest.raises(SessionDestroyed):
        del session["test3"]

    with pytest.raises(SessionDestroyed):
        [e for e in session]

    with pytest.raises(SessionDestroyed):
        "test1" in session

    with pytest.raises(SessionDestroyed):
        len(session)

    with pytest.raises(SessionNotFound):
        UbusSession(TIMEOUT, session_fixture)


def test_incorrect_data(session_fixture):
    session = UbusSession(TIMEOUT, session_fixture)

    # wrong key
    with pytest.raises(TypeError):
        session[6] = {}
    with pytest.raises(TypeError):
        session[None] = {}
    with pytest.raises(TypeError):
        session[False] = {}
    with pytest.raises(UnicodeDecodeError):
        session["ř"] = {}

    # wrong data
    with pytest.raises(TypeError):
        session["key"] = NonSerializable
    with pytest.raises(TypeError):
        session["key"] = [NonSerializable]
    with pytest.raises(TypeError):
        session["key"] = {"key": NonSerializable}
    session["key"] = {u"ř": 6}

    session.save()


def test_readonly():
    session = UbusSession(TIMEOUT, UbusSession.ANONYMOUS)

    assert session.session_id == UbusSession.ANONYMOUS
    assert session.expires_in == 0
    assert session.readonly is False
    session.readonly = True

    len(session)
    [e for e in session]
    assert session["key"] is None
    assert "qwerty" not in session

    with pytest.raises(SessionReadOnly):
        session.save()

    with pytest.raises(SessionReadOnly):
        session.destroy()

    with pytest.raises(SessionReadOnly):
        session["key"] = "value"

    with pytest.raises(SessionReadOnly):
        del session["key"]

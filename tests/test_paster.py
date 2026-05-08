from __future__ import annotations

import pytest

from voxless.config import PasteConfig
from voxless.paster import Paster


class _FakeController:
    def __init__(self) -> None:
        self.events: list[str] = []

    def pressed(self, key):
        outer = self

        class _Ctx:
            def __enter__(self_inner):
                outer.events.append(f"down:{getattr(key, 'name', str(key))}")
                return self_inner

            def __exit__(self_inner, *_):
                outer.events.append(f"up:{getattr(key, 'name', str(key))}")
                return False

        return _Ctx()

    def press(self, key):
        self.events.append(f"press:{key}")

    def release(self, key):
        self.events.append(f"release:{key}")


@pytest.fixture
def fake_clipboard(monkeypatch):
    state = {"value": "PREVIOUS"}

    def _copy(text):
        state["value"] = text

    def _paste():
        return state["value"]

    monkeypatch.setattr("voxless.paster.pyperclip.copy", _copy)
    monkeypatch.setattr("voxless.paster.pyperclip.paste", _paste)
    return state


def test_paste_sets_clipboard_and_sends_cmd_v(fake_clipboard) -> None:
    ctrl = _FakeController()
    p = Paster(PasteConfig(paste_delay_ms=0, restore_clipboard=False), controller=ctrl)
    p.paste("hello")
    assert fake_clipboard["value"] == "hello"
    assert any("press:v" in e for e in ctrl.events)
    assert any("down:cmd" in e for e in ctrl.events)


def test_paste_disabled_only_sets_clipboard(fake_clipboard) -> None:
    ctrl = _FakeController()
    p = Paster(PasteConfig(auto_paste=False), controller=ctrl)
    p.paste("hi")
    assert fake_clipboard["value"] == "hi"
    assert ctrl.events == []


def test_empty_text_is_noop(fake_clipboard) -> None:
    ctrl = _FakeController()
    p = Paster(PasteConfig(), controller=ctrl)
    p.paste("")
    assert fake_clipboard["value"] == "PREVIOUS"
    assert ctrl.events == []

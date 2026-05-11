"""Verify the watchdog can recover even when the worker is wedged.

These tests do not start audio devices; they exercise the App's recovery
primitives directly.
"""

from __future__ import annotations

import queue
import time

from voxless.app import App
from voxless.config import Config


def _make_app() -> App:
    cfg = Config()
    app = App(cfg)
    # Don't start hotkey/worker/watchdog threads — we drive recovery directly.
    return app


def test_force_recover_drains_queue_and_resets_state() -> None:
    app = _make_app()
    # Simulate a stuck recording: state is "recording", record_started_at set,
    # and a backlog of stale release events queued.
    app._state = "recording"
    app._record_started_at = time.monotonic() - 120.0
    for _ in range(5):
        app._events.put("release")
    app._target_app = ("macos", 1234, "Test")

    app._force_recover("test")

    assert app._state == "idle"
    assert app._record_started_at is None
    assert app._target_app is None
    # All queued events must be drained — otherwise they'd cause phantom
    # recordings once the worker wakes up.
    assert app._events.empty()


def test_recorder_abort_clears_recording_flag() -> None:
    app = _make_app()
    # Simulate the recorder believing it's recording, without ever having
    # opened an audio stream (so abort() can't hang on PortAudio).
    app._recorder._is_recording = True
    app._recorder._chunks = []
    app._recorder.abort()
    assert app._recorder._is_recording is False


def test_replace_worker_respawns_dead_thread() -> None:
    app = _make_app()
    # Kill the worker spawned by __init__ so we can verify respawn.
    app._stop.set()
    app._events.put("shutdown")
    app._worker.join(timeout=2.0)
    assert not app._worker.is_alive()
    old_worker = app._worker
    # Re-arm: a respawn must work even if _stop was set during the previous
    # lifecycle (we reset it like a real recovery would).
    app._stop = type(app._stop)()
    app._replace_worker_if_dead()
    assert app._worker is not old_worker
    assert app._worker.is_alive()
    # Clean up so the new thread doesn't outlive the test.
    app._stop.set()
    app._events.put("shutdown")
    app._worker.join(timeout=2.0)


def test_replace_worker_does_not_respawn_live_thread() -> None:
    app = _make_app()
    # __init__ already spawned a live worker.
    app._worker_heartbeat = time.monotonic()
    pre = app._worker
    assert pre.is_alive()
    app._replace_worker_if_dead()
    assert app._worker is pre
    # Clean up.
    app._stop.set()
    app._events.put("shutdown")
    app._worker.join(timeout=2.0)

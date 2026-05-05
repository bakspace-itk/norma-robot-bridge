# -*- coding: utf-8 -*-
"""Tests for FakeRobotService - sikrer at fake'en overholder kontrakten
som NormaRobotService eksponerer over for command-handlers og dispatcher.
"""

from __future__ import print_function, unicode_literals

import os
import tempfile

import pytest

from norma_bridge.robot.fakes import FakeRobotService, DEFAULT_GESTURES


# -------- say --------

def test_say_returnerer_kontrakt_dict():
    svc = FakeRobotService()
    result = svc.say("Hej Norma")
    assert set(result.keys()) == {"spoken_text", "gesture", "interaction_count"}
    assert result["spoken_text"] == "Hej Norma"
    assert result["interaction_count"] == 1


def test_say_eksplicit_gesture_overskriver_cycling():
    svc = FakeRobotService()
    result = svc.say("test", gesture="my/gesture")
    assert result["gesture"] == "my/gesture"


def test_say_uden_gesture_cykler_paa_lige_interaktioner():
    svc = FakeRobotService(gestures=("g0", "g1", "g2"))

    # interaction 1 (ulige -> None)
    r1 = svc.say("a")
    assert r1["gesture"] is None

    # interaction 2 (lige -> idx 2 % 3 = 2 -> g2)
    r2 = svc.say("b")
    assert r2["gesture"] == "g2"

    # interaction 3 (ulige -> None)
    r3 = svc.say("c")
    assert r3["gesture"] is None

    # interaction 4 (lige -> idx 4 % 3 = 1 -> g1)
    r4 = svc.say("d")
    assert r4["gesture"] == "g1"


def test_say_uden_gestures_konfigureret_returnerer_none():
    svc = FakeRobotService(gestures=())
    result = svc.say("hej")
    assert result["gesture"] is None


def test_say_inkrementerer_interaction_count():
    svc = FakeRobotService()
    svc.say("a")
    svc.say("b")
    svc.say("c")
    assert svc.get_status()["interaction_count"] == 3


def test_say_logger_history():
    svc = FakeRobotService()
    svc.say("hej", gesture="wave")
    assert svc.history == [
        {"op": "say", "text": "hej", "gesture": "wave", "interaction_count": 1}
    ]


# -------- play_gesture --------

def test_play_gesture_returnerer_kontrakt_dict():
    svc = FakeRobotService()
    result = svc.play_gesture("animations/Hey")
    assert result == {"played": "animations/Hey"}


def test_play_gesture_uden_navn_kaster_value_error():
    svc = FakeRobotService()
    with pytest.raises(ValueError):
        svc.play_gesture("")
    with pytest.raises(ValueError):
        svc.play_gesture(None)


def test_play_gesture_inkrementerer_ikke_interaction_count():
    """Kun say() taeller som interaktion - matcher legacy-adfaerden."""
    svc = FakeRobotService()
    svc.play_gesture("animations/Hey")
    assert svc.get_status()["interaction_count"] == 0


# -------- show_tablet_image --------

def test_show_tablet_image_med_eksisterende_fil():
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        f.write(b"fake png bytes")
        path = f.name
    try:
        svc = FakeRobotService()
        result = svc.show_tablet_image(path)
        assert result == {"shown_image": os.path.abspath(path)}
    finally:
        os.unlink(path)


def test_show_tablet_image_med_manglende_fil_kaster_io_error():
    svc = FakeRobotService()
    with pytest.raises(IOError):
        svc.show_tablet_image("/nonexistent/path/to/image.png")


def test_show_tablet_image_med_tom_sti_kaster_io_error():
    svc = FakeRobotService()
    with pytest.raises(IOError):
        svc.show_tablet_image("")


# -------- show_tablet_html --------

def test_show_tablet_html_returnerer_byte_laengde():
    svc = FakeRobotService()
    result = svc.show_tablet_html("<h1>Hej</h1>")
    assert result == {"html_length": len("<h1>Hej</h1>".encode("utf-8"))}


def test_show_tablet_html_med_unicode_taeller_byte_laengde():
    """æøå er to bytes hver i UTF-8 - ikke tegn-laengden."""
    svc = FakeRobotService()
    text = "æøå"
    result = svc.show_tablet_html(text)
    assert result == {"html_length": len(text.encode("utf-8"))}
    assert result["html_length"] == 6  # 3 tegn x 2 bytes


def test_show_tablet_html_med_none_kaster_value_error():
    svc = FakeRobotService()
    with pytest.raises(ValueError):
        svc.show_tablet_html(None)


# -------- show_tablet_url --------

def test_show_tablet_url_returnerer_shown_url():
    svc = FakeRobotService()
    assert svc.show_tablet_url("http://example.com/page") == {
        "shown_url": "http://example.com/page"
    }


def test_show_tablet_url_med_tom_streng_kaster_value_error():
    svc = FakeRobotService()
    with pytest.raises(ValueError):
        svc.show_tablet_url("")


def test_show_tablet_url_med_none_kaster_value_error():
    svc = FakeRobotService()
    with pytest.raises(ValueError):
        svc.show_tablet_url(None)


# -------- hide_tablet --------

def test_hide_tablet_returnerer_hidden_true():
    svc = FakeRobotService()
    assert svc.hide_tablet() == {"hidden": True}


# -------- get_status --------

def test_get_status_returnerer_default_felter():
    svc = FakeRobotService()
    status = svc.get_status()
    assert status == {
        "ip": "fake.robot.local",
        "port": 9559,
        "interaction_count": 0,
    }


def test_get_status_reflekterer_konfigureret_ip_og_port():
    svc = FakeRobotService(robot_ip="10.0.0.5", robot_port=12345)
    status = svc.get_status()
    assert status["ip"] == "10.0.0.5"
    assert status["port"] == 12345


# -------- thread-sikkerhed --------

def test_say_under_concurrent_kald_giver_konsistent_taeller():
    """RLock skal sikre at interaction_count ikke racer.

    Vi koerer 50 trade der hver kalder say() en gang, og verificerer at
    den endelige taeller er 50 og at alle interaction_count-vaerdier er unikke.
    """
    import threading as t
    svc = FakeRobotService()
    errors = []

    def worker():
        try:
            svc.say("concurrent")
        except Exception as e:
            errors.append(e)

    threads = [t.Thread(target=worker) for _ in range(50)]
    for thr in threads:
        thr.start()
    for thr in threads:
        thr.join()

    assert errors == []
    assert svc.get_status()["interaction_count"] == 50
    counts = [h["interaction_count"] for h in svc.history if h["op"] == "say"]
    assert sorted(counts) == list(range(1, 51))


# -------- default-gesture-listen --------

def test_default_gesture_liste_har_10_elementer():
    """Matcher antallet i legacy-koden (norma-archive/Norma_Output.py:42-53)."""
    assert len(DEFAULT_GESTURES) == 10

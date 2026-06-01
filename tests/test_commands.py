# -*- coding: utf-8 -*-
"""Tests for command-handlers i ``api/commands.py``.

Vi tester via den globale registry (``commands.py`` registrerer paa import)
mod en FakeRobotService. Det dobbelte formaal: validere baade dispatcher-
kontrakten og kommandoernes parameter-handling.
"""

from __future__ import print_function, unicode_literals

import os
import tempfile

import pytest

from pepper_bridge.api.dispatcher import registry
import pepper_bridge.api.commands  # noqa: F401 - import for at registrere
from pepper_bridge.robot.fakes import FakeRobotService


@pytest.fixture
def svc():
    return FakeRobotService(robot_ip="10.0.0.1", robot_port=9559)


# -------- registry-indhold --------

def test_alle_forventede_kommandoer_er_registreret():
    expected = {
        "say",
        "play_gesture",
        "show_tablet_image",
        "show_tablet_html",
        "show_tablet_url",
        "hide_tablet",
        "get_status",
    }
    assert expected.issubset(set(registry.names()))


# -------- say --------

def test_say_dispatcher_med_text():
    s = FakeRobotService()
    result = registry.dispatch(s, "say", {"text": "hej"})
    assert result["spoken_text"] == "hej"
    assert result["interaction_count"] == 1


def test_say_med_eksplicit_gesture():
    s = FakeRobotService()
    result = registry.dispatch(s, "say", {"text": "hej", "gesture": "wave"})
    assert result["gesture"] == "wave"


def test_say_uden_text_kaster_value_error(svc):
    with pytest.raises(ValueError) as exc_info:
        registry.dispatch(svc, "say", {})
    assert "params.text" in str(exc_info.value)


def test_say_med_none_text_kaster_value_error(svc):
    with pytest.raises(ValueError):
        registry.dispatch(svc, "say", {"text": None})


def test_say_med_tom_text_er_lovligt(svc):
    """Tom streng er gyldigt input - kun None udloeser fejl (matcher legacy)."""
    result = registry.dispatch(svc, "say", {"text": ""})
    assert result["spoken_text"] == ""


# -------- play_gesture --------

def test_play_gesture_med_kanonisk_param(svc):
    result = registry.dispatch(svc, "play_gesture", {"gesture_name": "hello"})
    assert result == {"played": "hello"}


def test_play_gesture_med_legacy_alias_gesture(svc):
    """Bagudkompatibilitet: 'gesture' accepteres i stedet for 'gesture_name'."""
    result = registry.dispatch(svc, "play_gesture", {"gesture": "hello"})
    assert result == {"played": "hello"}


def test_play_gesture_uden_navn_kaster_value_error(svc):
    with pytest.raises(ValueError) as exc_info:
        registry.dispatch(svc, "play_gesture", {})
    assert "gesture_name" in str(exc_info.value)


def test_play_gesture_med_tom_streng_kaster_value_error(svc):
    with pytest.raises(ValueError):
        registry.dispatch(svc, "play_gesture", {"gesture_name": ""})


# -------- show_tablet_image --------

def test_show_tablet_image_med_eksisterende_fil(svc):
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        f.write(b"x")
        path = f.name
    try:
        result = registry.dispatch(svc, "show_tablet_image", {"image_path": path})
        assert result == {"shown_image": os.path.abspath(path)}
    finally:
        os.unlink(path)


def test_show_tablet_image_uden_path_kaster_value_error(svc):
    with pytest.raises(ValueError) as exc_info:
        registry.dispatch(svc, "show_tablet_image", {})
    assert "image_path" in str(exc_info.value)


def test_show_tablet_image_med_tom_path_kaster_value_error(svc):
    with pytest.raises(ValueError):
        registry.dispatch(svc, "show_tablet_image", {"image_path": ""})


def test_show_tablet_image_med_manglende_fil_propagerer_io_error(svc):
    """Filsystem-fejl er IKKE klient-fejl - lad det boble op som IOError."""
    with pytest.raises(IOError):
        registry.dispatch(svc, "show_tablet_image", {"image_path": "/findes/ikke.png"})


# -------- show_tablet_html --------

def test_show_tablet_html_med_kanonisk_param(svc):
    result = registry.dispatch(svc, "show_tablet_html", {"html": "<h1>Hej</h1>"})
    assert result == {"html_length": len("<h1>Hej</h1>")}


def test_show_tablet_html_med_legacy_alias_html_content(svc):
    """Bagudkompatibilitet: 'html_content' accepteres."""
    result = registry.dispatch(svc, "show_tablet_html", {"html_content": "<p>x</p>"})
    assert result == {"html_length": len("<p>x</p>")}


def test_show_tablet_html_med_tom_streng_er_lovligt(svc):
    result = registry.dispatch(svc, "show_tablet_html", {"html": ""})
    assert result == {"html_length": 0}


def test_show_tablet_html_uden_html_kaster_value_error(svc):
    with pytest.raises(ValueError) as exc_info:
        registry.dispatch(svc, "show_tablet_html", {})
    assert "params.html" in str(exc_info.value)


def test_show_tablet_html_med_none_kaster_value_error(svc):
    with pytest.raises(ValueError):
        registry.dispatch(svc, "show_tablet_html", {"html": None})


# -------- show_tablet_url --------

def test_show_tablet_url_med_url(svc):
    result = registry.dispatch(svc, "show_tablet_url", {"url": "http://x.local"})
    assert result == {"shown_url": "http://x.local"}


def test_show_tablet_url_uden_url_kaster_value_error(svc):
    with pytest.raises(ValueError) as exc_info:
        registry.dispatch(svc, "show_tablet_url", {})
    assert "url" in str(exc_info.value)


def test_show_tablet_url_med_tom_streng_kaster_value_error(svc):
    with pytest.raises(ValueError):
        registry.dispatch(svc, "show_tablet_url", {"url": ""})


# -------- hide_tablet --------

def test_hide_tablet_uden_params(svc):
    result = registry.dispatch(svc, "hide_tablet", {})
    assert result == {"hidden": True}


def test_hide_tablet_ignorerer_uventede_params(svc):
    """Klienten maa gerne sende ekstra params - de ignoreres."""
    result = registry.dispatch(svc, "hide_tablet", {"foo": "bar"})
    assert result == {"hidden": True}


# -------- get_status --------

def test_get_status_returnerer_ip_port_count(svc):
    result = registry.dispatch(svc, "get_status", {})
    assert result == {"ip": "10.0.0.1", "port": 9559, "interaction_count": 0}


# -------- generelle dispatcher-egenskaber via globalen --------

def test_ukendt_kommando_via_global_registry(svc):
    with pytest.raises(ValueError) as exc_info:
        registry.dispatch(svc, "doesnt_exist", {})
    assert "Ukendt kommando" in str(exc_info.value)

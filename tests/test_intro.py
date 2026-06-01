# -*- coding: utf-8 -*-
"""Tests for intro.py - opstarts-intro mod en service.

Vi tester mod ``FakeRobotService`` saa hele intro-flowet kan verificeres
uden NAOqi.
"""

from __future__ import print_function, unicode_literals

import os
import tempfile

import pytest

from pepper_bridge.robot.fakes import FakeRobotService
from pepper_bridge.robot.intro import IntroConfig, run_intro


# -------- IntroConfig --------

def test_intro_config_alle_felter_default_til_none():
    cfg = IntroConfig()
    assert cfg.animation_tag is None
    assert cfg.image_url is None
    assert cfg.image_path is None
    assert cfg.welcome_text is None


def test_intro_config_fra_dict_laeser_alle_felter():
    cfg = IntroConfig.from_dict({
        "animation_tag": "cloud",
        "image_url": "http://ui.example.local/intro",
        "image_path": "/tmp/intro.png",
        "welcome_text": "Hej",
    })
    assert cfg.animation_tag == "cloud"
    assert cfg.image_url == "http://ui.example.local/intro"
    assert cfg.image_path == "/tmp/intro.png"
    assert cfg.welcome_text == "Hej"


def test_intro_config_fra_dict_med_partial_data():
    cfg = IntroConfig.from_dict({"welcome_text": "Hej"})
    assert cfg.welcome_text == "Hej"
    assert cfg.animation_tag is None


def test_intro_config_fra_dict_med_none_returnerer_none():
    assert IntroConfig.from_dict(None) is None
    assert IntroConfig.from_dict({}) is None


# -------- run_intro: ingen config --------

def test_run_intro_med_none_config_er_no_op():
    svc = FakeRobotService()
    results = run_intro(svc, None)
    assert results == []
    assert svc.history == []


def test_run_intro_med_helt_tom_config_kalder_intet():
    svc = FakeRobotService()
    results = run_intro(svc, IntroConfig())
    assert results == []
    assert svc.history == []


# -------- run_intro: enkelte trin --------

def test_run_intro_kun_animation():
    svc = FakeRobotService()
    results = run_intro(svc, IntroConfig(animation_tag="cloud"))
    assert results == [("animation", "ok")]
    assert svc.history == [{"op": "play_gesture", "gesture_name": "cloud"}]


def test_run_intro_kun_velkomst():
    svc = FakeRobotService()
    results = run_intro(svc, IntroConfig(welcome_text="Hello world"))
    assert results == [("welcome", "ok")]
    # say tracker text + interaction_count + cycled gesture
    assert len(svc.history) == 1
    assert svc.history[0]["op"] == "say"
    assert svc.history[0]["text"] == "Hello world"


def test_run_intro_kun_image_url():
    svc = FakeRobotService()
    results = run_intro(svc, IntroConfig(image_url="http://x.local"))
    assert results == [("tablet_url", "ok")]
    assert svc.history == [{"op": "show_tablet_url", "url": "http://x.local"}]


# -------- run_intro: image_url har forrang over image_path --------

def test_run_intro_image_url_vinder_over_image_path():
    """Hvis baade url og path er sat, kald kun show_tablet_url."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        f.write(b"fake")
        path = f.name
    try:
        svc = FakeRobotService()
        results = run_intro(svc, IntroConfig(
            image_url="http://x.local",
            image_path=path,
        ))
        assert results == [("tablet_url", "ok")]
        # show_tablet_image maa IKKE vaere kaldt
        ops = [h["op"] for h in svc.history]
        assert "show_tablet_image" not in ops
        assert "show_tablet_url" in ops
    finally:
        os.unlink(path)


def test_run_intro_image_path_bruges_naar_url_mangler():
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        f.write(b"fake")
        path = f.name
    try:
        svc = FakeRobotService()
        results = run_intro(svc, IntroConfig(image_path=path))
        assert results == [("tablet_image", "ok")]
        assert svc.history[0]["op"] == "show_tablet_image"
    finally:
        os.unlink(path)


# -------- run_intro: fuld sekvens --------

def test_run_intro_fuld_sekvens_i_korrekt_raekkefoelge():
    """animation -> tablet -> welcome (legacy raekkefoelge)."""
    svc = FakeRobotService()
    cfg = IntroConfig(
        animation_tag="cloud",
        image_url="http://ui.example.local/intro",
        welcome_text="Hello world",
    )
    results = run_intro(svc, cfg)
    assert results == [
        ("animation", "ok"),
        ("tablet_url", "ok"),
        ("welcome", "ok"),
    ]
    ops = [h["op"] for h in svc.history]
    assert ops == ["play_gesture", "show_tablet_url", "say"]


# -------- run_intro: fejlhandtering --------

def test_run_intro_animation_fejl_stopper_ikke_resten():
    """Hvis play_gesture fejler skal tablet og welcome stadig koeres.

    Det er den eneste sted i bridge hvor ``try/except`` er bevidst tilladt -
    intro maa ikke vaelte hele service'en.
    """
    svc = FakeRobotService()
    # FakeRobotService kaster ValueError hvis gesture er tom -> bruger en
    # MagicMock-style erstatning er overkill her. Vi monkey-patcher i stedet.
    original = svc.play_gesture

    def boom(name):
        raise RuntimeError("anim eksploderede")

    svc.play_gesture = boom

    cfg = IntroConfig(
        animation_tag="cloud",
        image_url="http://x.local",
        welcome_text="Hej",
    )
    results = run_intro(svc, cfg)

    # Animation fejlede, men de naeste to lykkedes
    assert results[0][0] == "animation"
    assert "fejl" in results[0][1]
    assert results[1] == ("tablet_url", "ok")
    assert results[2] == ("welcome", "ok")

    svc.play_gesture = original  # rens op


def test_run_intro_tablet_fejl_stopper_ikke_velkomst():
    """show_tablet_url fejler -> welcome_text skal stadig siges."""
    svc = FakeRobotService()

    def boom(url):
        raise RuntimeError("tablet eksploderede")

    svc.show_tablet_url = boom

    cfg = IntroConfig(
        image_url="http://x.local",
        welcome_text="Hej",
    )
    results = run_intro(svc, cfg)
    assert "fejl" in results[0][1]
    assert results[1] == ("welcome", "ok")


# -------- run_intro: custom logger --------

def test_run_intro_bruger_custom_logger_til_fejl():
    """Tester at en injiceret logger faar warnings (i stedet for modul-defaulten)."""
    import logging

    svc = FakeRobotService()
    svc.play_gesture = lambda name: (_ for _ in ()).throw(RuntimeError("boom"))

    captured = []

    class StubLogger(object):
        def warning(self, msg, *args):
            captured.append(msg % args if args else msg)
        def debug(self, msg, *args):
            pass

    run_intro(svc, IntroConfig(animation_tag="cloud"), logger=StubLogger())
    assert len(captured) == 1
    assert "cloud" in captured[0]
    assert "boom" in captured[0]

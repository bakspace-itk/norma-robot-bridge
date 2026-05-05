# -*- coding: utf-8 -*-
"""Tests for config-loader.

Verificerer precedence-rakkefoelgen: defaults < INI < ENV. CLI-args
testes via test_main_smoke.py og argparse direkte.
"""

from __future__ import print_function, unicode_literals

import os
import tempfile

import pytest

from norma_bridge.config import (
    BridgeConfig,
    load_config,
    ENV_ROBOT_IP,
    ENV_ROBOT_PORT,
    ENV_BRIDGE_HOST,
    ENV_BRIDGE_PORT,
    ENV_LOG_LEVEL,
)
from norma_bridge.robot.gestures import DEFAULT_GESTURES


# -------- defaults --------

def test_load_uden_ini_eller_env_giver_defaults():
    cfg = load_config(env={})
    assert cfg.robot_ip == "192.168.1.156"
    assert cfg.robot_port == 9559
    assert cfg.host == ""
    assert cfg.port == 8080
    assert cfg.gestures == DEFAULT_GESTURES
    assert cfg.intro is None
    assert cfg.log_level == "INFO"


def test_load_med_manglende_ini_fil_advarer_men_fortsaetter(caplog):
    cfg = load_config(ini_path="/findes/ikke.ini", env={})
    assert cfg.robot_ip == "192.168.1.156"
    # warning logget
    assert any("findes ikke" in rec.message for rec in caplog.records)


# -------- ENV overrides --------

def test_env_robot_ip_overstyrer_default():
    cfg = load_config(env={ENV_ROBOT_IP: "10.0.0.5"})
    assert cfg.robot_ip == "10.0.0.5"


def test_env_robot_port_konverteres_til_int():
    cfg = load_config(env={ENV_ROBOT_PORT: "12345"})
    assert cfg.robot_port == 12345
    assert isinstance(cfg.robot_port, int)


def test_env_bridge_host_og_port_overstyrer():
    cfg = load_config(env={
        ENV_BRIDGE_HOST: "0.0.0.0",
        ENV_BRIDGE_PORT: "9090",
    })
    assert cfg.host == "0.0.0.0"
    assert cfg.port == 9090


def test_env_log_level_overstyrer():
    cfg = load_config(env={ENV_LOG_LEVEL: "DEBUG"})
    assert cfg.log_level == "DEBUG"


# -------- INI helpers --------

@pytest.fixture
def write_ini(tmp_path):
    """Returnerer en hjaelper der skriver INI-indhold til en temp-fil."""
    def _write(content):
        path = tmp_path / "test.ini"
        path.write_text(content, encoding="utf-8")
        return str(path)
    return _write


# -------- INI overrides --------

def test_ini_overstyrer_defaults(write_ini):
    ini = write_ini("""
[robot]
ip = 10.0.0.99
port = 9999

[server]
host = 0.0.0.0
port = 7070

[logging]
level = WARNING
""")
    cfg = load_config(ini_path=ini, env={})
    assert cfg.robot_ip == "10.0.0.99"
    assert cfg.robot_port == 9999
    assert cfg.host == "0.0.0.0"
    assert cfg.port == 7070
    assert cfg.log_level == "WARNING"


def test_ini_med_partielle_sektioner_bevarer_defaults_for_resten(write_ini):
    """En sektion der kun saetter ét felt skal ikke nulstille de andre."""
    ini = write_ini("[robot]\nip = 10.0.0.1\n")
    cfg = load_config(ini_path=ini, env={})
    assert cfg.robot_ip == "10.0.0.1"
    assert cfg.robot_port == 9559  # default bevaret
    assert cfg.port == 8080  # default bevaret


def test_ini_gestures_parses_som_komma_separeret(write_ini):
    ini = write_ini("[gestures]\nlist = a, b , c,d\n")
    cfg = load_config(ini_path=ini, env={})
    assert cfg.gestures == ("a", "b", "c", "d")


def test_ini_tom_gestures_falder_tilbage_til_default(write_ini):
    ini = write_ini("[gestures]\nlist = \n")
    cfg = load_config(ini_path=ini, env={})
    assert cfg.gestures == DEFAULT_GESTURES


def test_ini_uden_gestures_sektion_giver_default(write_ini):
    ini = write_ini("[robot]\nip = 1.2.3.4\n")
    cfg = load_config(ini_path=ini, env={})
    assert cfg.gestures == DEFAULT_GESTURES


# -------- INI intro --------

def test_ini_intro_med_alle_felter(write_ini):
    ini = write_ini("""
[intro]
animation_tag = cloud
image_url = http://norma-ui.local/intro
welcome_text = Hej Norma
""")
    cfg = load_config(ini_path=ini, env={})
    assert cfg.intro is not None
    assert cfg.intro.animation_tag == "cloud"
    assert cfg.intro.image_url == "http://norma-ui.local/intro"
    assert cfg.intro.welcome_text == "Hej Norma"
    assert cfg.intro.image_path is None


def test_ini_intro_med_tomme_felter_bliver_none(write_ini):
    """Hvis alle intro-felter er tomme strings, skal intro vaere None."""
    ini = write_ini("""
[intro]
animation_tag =
image_url =
welcome_text =
""")
    cfg = load_config(ini_path=ini, env={})
    assert cfg.intro is None


def test_ini_uden_intro_sektion_giver_none(write_ini):
    ini = write_ini("[robot]\nip = 1.2.3.4\n")
    cfg = load_config(ini_path=ini, env={})
    assert cfg.intro is None


# -------- precedence: ENV vinder over INI --------

def test_env_vinder_over_ini_for_robot_ip(write_ini):
    ini = write_ini("[robot]\nip = 10.0.0.1\nport = 9559\n")
    cfg = load_config(ini_path=ini, env={ENV_ROBOT_IP: "192.168.99.99"})
    assert cfg.robot_ip == "192.168.99.99"
    assert cfg.robot_port == 9559  # INI bevares hvor ENV ikke overstyrer


def test_env_vinder_over_ini_for_alle_overlappende_felter(write_ini):
    ini = write_ini("""
[robot]
ip = 10.0.0.1
port = 9000

[server]
host = 1.1.1.1
port = 8000

[logging]
level = WARNING
""")
    cfg = load_config(ini_path=ini, env={
        ENV_ROBOT_IP: "2.2.2.2",
        ENV_ROBOT_PORT: "9999",
        ENV_BRIDGE_HOST: "3.3.3.3",
        ENV_BRIDGE_PORT: "7777",
        ENV_LOG_LEVEL: "DEBUG",
    })
    assert cfg.robot_ip == "2.2.2.2"
    assert cfg.robot_port == 9999
    assert cfg.host == "3.3.3.3"
    assert cfg.port == 7777
    assert cfg.log_level == "DEBUG"


# -------- BridgeConfig direkte --------

def test_bridge_config_repr_indeholder_noegletal():
    cfg = BridgeConfig(robot_ip="1.2.3.4", port=9090)
    text = repr(cfg)
    assert "1.2.3.4" in text
    assert "9090" in text


def test_bridge_config_default_gestures_er_tuple():
    """Tuples er immutable - forhindrer at klienter muterer den globale default."""
    cfg = BridgeConfig()
    assert isinstance(cfg.gestures, tuple)

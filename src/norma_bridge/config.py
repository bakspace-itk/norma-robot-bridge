# -*- coding: utf-8 -*-
"""Konfiguration for norma-bridge.

Precedence (lavest til hojest):
    1. Defaults i koden
    2. INI-fil (hvis stien er angivet via --config eller her)
    3. Miljovariabler (NORMA_*)
    4. CLI-args (haandteret i main.py)

INI er valgt over YAML for at undgaa PyYAML-afhaengighed paa robot-maskinen,
hvor pip-installation ikke altid er enkel.

Eksempel paa INI-fil ligger i ``config/default.ini``.
"""

from __future__ import print_function, unicode_literals

import logging
import os

try:
    # Py 3
    from configparser import ConfigParser, NoSectionError, NoOptionError
except ImportError:
    # Py 2.7
    from ConfigParser import ConfigParser, NoSectionError, NoOptionError

from norma_bridge.robot.gestures import DEFAULT_GESTURES
from norma_bridge.robot.intro import IntroConfig


_log = logging.getLogger(__name__)


# ENV-variabel-navne. Aendringer her skal afspejles i config/default.ini-kommentarer.
ENV_ROBOT_IP = "NORMA_ROBOT_IP"
ENV_ROBOT_PORT = "NORMA_ROBOT_PORT"
ENV_BRIDGE_HOST = "NORMA_BRIDGE_HOST"
ENV_BRIDGE_PORT = "NORMA_BRIDGE_PORT"
ENV_LOG_LEVEL = "NORMA_LOG_LEVEL"


class BridgeConfig(object):
    """Konsolideret konfiguration for bridge'en."""

    def __init__(self,
                 robot_ip="192.168.1.156",
                 robot_port=9559,
                 host="",
                 port=8080,
                 gestures=DEFAULT_GESTURES,
                 intro=None,
                 log_level="INFO"):
        self.robot_ip = robot_ip
        self.robot_port = robot_port
        self.host = host
        self.port = port
        self.gestures = tuple(gestures) if gestures else ()
        self.intro = intro  # IntroConfig eller None
        self.log_level = log_level

    def __repr__(self):
        return (
            "BridgeConfig(robot=%s:%d, server=%s:%d, "
            "gestures=%d items, intro=%s, log_level=%s)"
        ) % (
            self.robot_ip, self.robot_port,
            self.host or "0.0.0.0", self.port,
            len(self.gestures),
            "set" if self.intro is not None else "none",
            self.log_level,
        )


def _get(parser, section, option, default):
    """Slaa option op i parser. Returner default (uaendret type) hvis missing."""
    try:
        return parser.get(section, option)
    except (NoSectionError, NoOptionError):
        return default


def _parse_gestures(raw):
    """Konverter komma-separeret streng til tuple af strippede tags."""
    if not raw:
        return DEFAULT_GESTURES
    items = tuple(s.strip() for s in raw.split(",") if s.strip())
    return items if items else DEFAULT_GESTURES


def _parse_intro(parser):
    """Byg IntroConfig fra [intro]-sektion. Returner None hvis alle felter er tomme."""
    fields = {
        "animation_tag": _get(parser, "intro", "animation_tag", "") or None,
        "image_url": _get(parser, "intro", "image_url", "") or None,
        "image_path": _get(parser, "intro", "image_path", "") or None,
        "welcome_text": _get(parser, "intro", "welcome_text", "") or None,
    }
    if not any(fields.values()):
        return None
    return IntroConfig(**fields)


def load_config(ini_path=None, env=None):
    """Indlaes konfiguration med precedence defaults < INI < ENV.

    Argumenter:
        ini_path: sti til INI-fil. Hvis None eller filen ikke findes,
                  bruges kun defaults + ENV.
        env: dict-lignende objekt som ``os.environ``. Default: ``os.environ``.
             Injicerbart for tests.

    Returnerer:
        ``BridgeConfig`` med alle felter udfyldt.
    """
    env = env if env is not None else os.environ
    cfg = BridgeConfig()

    # ---- INI overrides ----
    if ini_path:
        if not os.path.exists(ini_path):
            _log.warning("Config-fil findes ikke: %s (bruger defaults + ENV)", ini_path)
        else:
            parser = ConfigParser()
            parser.read([ini_path])  # Py 2/3-kompatibel
            cfg.robot_ip = _get(parser, "robot", "ip", cfg.robot_ip)
            cfg.robot_port = int(_get(parser, "robot", "port", cfg.robot_port))
            cfg.host = _get(parser, "server", "host", cfg.host)
            cfg.port = int(_get(parser, "server", "port", cfg.port))
            cfg.gestures = _parse_gestures(_get(parser, "gestures", "list", None))
            cfg.intro = _parse_intro(parser)
            cfg.log_level = _get(parser, "logging", "level", cfg.log_level)

    # ---- ENV overrides ----
    if ENV_ROBOT_IP in env:
        cfg.robot_ip = env[ENV_ROBOT_IP]
    if ENV_ROBOT_PORT in env:
        cfg.robot_port = int(env[ENV_ROBOT_PORT])
    if ENV_BRIDGE_HOST in env:
        cfg.host = env[ENV_BRIDGE_HOST]
    if ENV_BRIDGE_PORT in env:
        cfg.port = int(env[ENV_BRIDGE_PORT])
    if ENV_LOG_LEVEL in env:
        cfg.log_level = env[ENV_LOG_LEVEL]

    return cfg

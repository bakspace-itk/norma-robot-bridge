# -*- coding: utf-8 -*-
"""Tests for main.py - CLI parsing og service-konstruktion.

build_service() skal fail fast naar robot_ip mangler i ikke-fake-mode,
men tolerere det i fake-mode.
"""

from __future__ import print_function, unicode_literals

import pytest

from pepper_bridge.config import BridgeConfig
from pepper_bridge.main import build_service, parse_args
from pepper_bridge.robot.fakes import FakeRobotService


# -------- parse_args: nye --robot-ip / --robot-port flags --------

def test_parse_args_robot_ip_og_port_defaulter_til_none():
    args = parse_args([])
    assert args.robot_ip is None
    assert args.robot_port is None


def test_parse_args_robot_ip_overstyrer_default():
    args = parse_args(["--robot-ip", "10.0.0.5"])
    assert args.robot_ip == "10.0.0.5"


def test_parse_args_robot_port_konverteres_til_int():
    args = parse_args(["--robot-port", "12345"])
    assert args.robot_port == 12345
    assert isinstance(args.robot_port, int)


# -------- build_service: fail fast naar ip mangler --------

def test_build_service_fejler_hurtigt_uden_ip_i_real_mode():
    cfg = BridgeConfig()  # robot_ip=None
    with pytest.raises(SystemExit) as exc_info:
        build_service(cfg, use_fake=False)
    assert "Robot-IP mangler" in str(exc_info.value)
    assert "--robot-ip" in str(exc_info.value)
    assert "PEPPER_ROBOT_IP" in str(exc_info.value)


def test_build_service_fake_mode_tolererer_manglende_ip():
    cfg = BridgeConfig()  # robot_ip=None
    service = build_service(cfg, use_fake=True)
    assert isinstance(service, FakeRobotService)

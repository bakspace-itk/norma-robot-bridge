# -*- coding: utf-8 -*-
"""Entry point for pepper-bridge.

Eksempler:
    # Mod fysisk robot - auto-loader config/local.ini hvis den findes
    python -m pepper_bridge.main

    # Mod fysisk robot med eksplicit IP (overstyrer config og ENV)
    python -m pepper_bridge.main --robot-ip 192.168.1.42

    # Mod fysisk robot med eksplicit config-fil
    python -m pepper_bridge.main --config config/local.ini

    # Lokal udvikling uden NAOqi (FakeRobotService)
    python -m pepper_bridge.main --fake --port 8080

    # Kombination: fake-mode med specifik intro-test
    python -m pepper_bridge.main --fake --no-intro
"""

from __future__ import print_function, unicode_literals

import argparse
import logging
import sys

from pepper_bridge.config import load_config, find_default_ini
from pepper_bridge.api.handlers import make_handler
from pepper_bridge.api.server import serve
from pepper_bridge.robot.intro import run_intro
from pepper_bridge.robot.fakes import FakeRobotService


_log = logging.getLogger(__name__)


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        prog="pepper-bridge",
        description="HTTP-bridge der eksponerer NAOqi for Pepper/NAO.",
    )
    p.add_argument(
        "--config", metavar="PATH",
        help="Sti til INI config-fil. Hvis udeladt: defaults + miljovariabler.",
    )
    p.add_argument(
        "--host", help="Bind-host. Overstyrer config og PEPPER_BRIDGE_HOST.",
    )
    p.add_argument(
        "--port", type=int,
        help="Bind-port. Overstyrer config og PEPPER_BRIDGE_PORT.",
    )
    p.add_argument(
        "--robot-ip", metavar="IP",
        help="IP-adresse til Pepper/NAO. Overstyrer config og PEPPER_ROBOT_IP.",
    )
    p.add_argument(
        "--robot-port", type=int, metavar="PORT",
        help="NAOqi-port. Overstyrer config og PEPPER_ROBOT_PORT.",
    )
    p.add_argument(
        "--fake", action="store_true",
        help="Brug FakeRobotService - ingen NAOqi-paakrav. Til lokal udvikling.",
    )
    p.add_argument(
        "--no-intro", action="store_true",
        help="Spring opstarts-intro over (animation, tablet, velkomst).",
    )
    p.add_argument(
        "--log-level", metavar="LEVEL",
        help="DEBUG/INFO/WARNING/ERROR. Overstyrer config og PEPPER_LOG_LEVEL.",
    )
    return p.parse_args(argv)


def setup_logging(level):
    """Konfigurer roden af logging-traet. Accepterer baade str og int level."""
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def build_service(cfg, use_fake):
    """Konstruer enten en rigtig eller fake service afhaengigt af flag.

    PepperRobotService importeres lazy saa --fake-mode kan koere paa Py 3
    uden at NAOqi er installeret.
    """
    if use_fake:
        _log.info("Bruger FakeRobotService (--fake)")
        return FakeRobotService(
            robot_ip=cfg.robot_ip,
            robot_port=cfg.robot_port,
            gestures=cfg.gestures,
        )
    if cfg.robot_ip is None:
        raise SystemExit(
            "Robot-IP mangler. Angiv en af foelgende:\n"
            "  --robot-ip <IP>                  (CLI)\n"
            "  PEPPER_ROBOT_IP=<IP>              (miljovariabel)\n"
            "  [robot] ip = <IP> i en INI-fil   (--config eller config/local.ini)"
        )
    from pepper_bridge.robot.service import PepperRobotService
    _log.info("Forbinder til NAOqi paa %s:%d", cfg.robot_ip, cfg.robot_port)
    return PepperRobotService(
        cfg.robot_ip, cfg.robot_port, gestures=cfg.gestures,
    )


def main(argv=None):
    args = parse_args(argv)

    ini_path = args.config if args.config is not None else find_default_ini()
    cfg = load_config(ini_path)

    # CLI-args overstyrer alt andet
    if args.host is not None:
        cfg.host = args.host
    if args.port is not None:
        cfg.port = args.port
    if args.robot_ip is not None:
        cfg.robot_ip = args.robot_ip
    if args.robot_port is not None:
        cfg.robot_port = args.robot_port
    if args.log_level:
        cfg.log_level = args.log_level

    setup_logging(cfg.log_level)
    if ini_path is None:
        _log.info("Ingen config-fil indlaest (kun defaults + ENV + CLI)")
    elif args.config is None:
        _log.info("Auto-loadede config-fil: %s", ini_path)
    else:
        _log.info("Indlaest config-fil: %s", ini_path)
    _log.info("Pepper bridge starter: %s", cfg)

    service = build_service(cfg, args.fake)

    if args.no_intro:
        _log.info("Intro sprunget over (--no-intro)")
    elif cfg.intro is None:
        _log.info("Ingen intro defineret i config")
    else:
        _log.info("Koerer intro")
        for step, status in run_intro(service, cfg.intro):
            _log.info("  intro %s: %s", step, status)

    handler_cls = make_handler(service)
    serve(handler_cls, cfg.host, cfg.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())

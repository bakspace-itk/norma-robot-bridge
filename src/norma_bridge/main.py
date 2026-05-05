# -*- coding: utf-8 -*-
"""Entry point for norma-bridge.

Eksempler:
    # Mod fysisk robot, default config
    python -m norma_bridge.main

    # Mod fysisk robot med eksplicit config-fil
    python -m norma_bridge.main --config config/local.ini

    # Lokal udvikling uden NAOqi (FakeRobotService)
    python -m norma_bridge.main --fake --port 8080

    # Kombination: fake-mode med specifik intro-test
    python -m norma_bridge.main --fake --no-intro
"""

from __future__ import print_function, unicode_literals

import argparse
import logging
import sys

from norma_bridge.config import load_config
from norma_bridge.api.handlers import make_handler
from norma_bridge.api.server import serve
from norma_bridge.robot.intro import run_intro
from norma_bridge.robot.fakes import FakeRobotService


_log = logging.getLogger(__name__)


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        prog="norma-bridge",
        description="HTTP-bridge der eksponerer NAOqi for Pepper/NAO.",
    )
    p.add_argument(
        "--config", metavar="PATH",
        help="Sti til INI config-fil. Hvis udeladt: defaults + miljovariabler.",
    )
    p.add_argument(
        "--host", help="Bind-host. Overstyrer config og NORMA_BRIDGE_HOST.",
    )
    p.add_argument(
        "--port", type=int,
        help="Bind-port. Overstyrer config og NORMA_BRIDGE_PORT.",
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
        help="DEBUG/INFO/WARNING/ERROR. Overstyrer config og NORMA_LOG_LEVEL.",
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

    NormaRobotService importeres lazy saa --fake-mode kan koere paa Py 3
    uden at NAOqi er installeret.
    """
    if use_fake:
        _log.info("Bruger FakeRobotService (--fake)")
        return FakeRobotService(
            robot_ip=cfg.robot_ip,
            robot_port=cfg.robot_port,
            gestures=cfg.gestures,
        )
    from norma_bridge.robot.service import NormaRobotService
    _log.info("Forbinder til NAOqi paa %s:%d", cfg.robot_ip, cfg.robot_port)
    return NormaRobotService(
        cfg.robot_ip, cfg.robot_port, gestures=cfg.gestures,
    )


def main(argv=None):
    args = parse_args(argv)
    cfg = load_config(args.config)

    # CLI-args overstyrer alt andet
    if args.host is not None:
        cfg.host = args.host
    if args.port is not None:
        cfg.port = args.port
    if args.log_level:
        cfg.log_level = args.log_level

    setup_logging(cfg.log_level)
    _log.info("Norma bridge starter: %s", cfg)

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

# -*- coding: utf-8 -*-
"""Startup-intro flow.

Designvalg:

- ``run_intro`` er en pure funktion - ingen klasse, ingen state.
- Konfigurationen er data-drevet via ``IntroConfig``: hvert trin er valgfrit
  og kan deaktiveres ved at saette feltet til None.
- Hvert trin har sit eget try/except saa en fejl i intro-animationen ikke
  forhindrer velkomst-tts'en.
- Foretrukken intro-billed-mekanisme: ``image_url`` (peges paa et eksternt UI via
  ``show_tablet_url``). ``image_path`` bevares som fallback for data-URI-flow.
"""

from __future__ import print_function, unicode_literals

import logging


_log = logging.getLogger(__name__)


class IntroConfig(object):
    """Konfiguration af opstarts-intro. Alle felter er valgfrie.

    Argumenter:
        animation_tag: gesture-tag der afspilles foerst (fx "cloud").
        image_url: URL som tablet-WebView pejes paa (foretrukne flow).
        image_path: lokal billed-sti vist via legacy data-URI (fallback).
        welcome_text: sætning der siges via TTS som sidste trin.

    Hvis baade ``image_url`` og ``image_path`` er sat, vinder ``image_url``.
    """

    def __init__(self, animation_tag=None, image_url=None,
                 image_path=None, welcome_text=None):
        self.animation_tag = animation_tag
        self.image_url = image_url
        self.image_path = image_path
        self.welcome_text = welcome_text

    @classmethod
    def from_dict(cls, data):
        """Konstruer en IntroConfig fra et dict (typisk indlaest fra config-fil).

        Returnerer None hvis ``data`` er None eller tomt.
        """
        if not data:
            return None
        return cls(
            animation_tag=data.get("animation_tag"),
            image_url=data.get("image_url"),
            image_path=data.get("image_path"),
            welcome_text=data.get("welcome_text"),
        )


def run_intro(service, config, logger=None):
    """Koer startup-intro mod en allerede konstrueret service.

    Argumenter:
        service: en ``PepperRobotService`` eller ``FakeRobotService``.
        config: en ``IntroConfig`` eller None (springes intro over).
        logger: valgfri logger til fejl-rapportering. Default: modul-logger.

    Returnerer:
        En liste af (trin, status) tuples saa kalderen kan inspicere hvad
        der lykkedes - nyttigt til logs og smoketests.

    Hvert trin koeres uafhaengigt - en fejl i ét trin forhindrer ikke de
    foelgende.
    """
    log = logger or _log
    results = []

    if config is None:
        log.debug("Intro skipped: ingen config")
        return results

    if config.animation_tag:
        try:
            service.play_gesture(config.animation_tag)
            results.append(("animation", "ok"))
        except Exception as e:
            log.warning("Intro-animation '%s' fejlede: %s", config.animation_tag, e)
            results.append(("animation", "fejl: %s" % e))

    # image_url har forrang over image_path.
    if config.image_url:
        try:
            service.show_tablet_url(config.image_url)
            results.append(("tablet_url", "ok"))
        except Exception as e:
            log.warning("Intro-tablet-url '%s' fejlede: %s", config.image_url, e)
            results.append(("tablet_url", "fejl: %s" % e))
    elif config.image_path:
        try:
            service.show_tablet_image(config.image_path)
            results.append(("tablet_image", "ok"))
        except Exception as e:
            log.warning("Intro-tablet-image '%s' fejlede: %s", config.image_path, e)
            results.append(("tablet_image", "fejl: %s" % e))

    if config.welcome_text:
        try:
            service.say(config.welcome_text)
            results.append(("welcome", "ok"))
        except Exception as e:
            log.warning("Intro-velkomst fejlede: %s", e)
            results.append(("welcome", "fejl: %s" % e))

    return results

# -*- coding: utf-8 -*-
"""Command-handlers - HTTP-API'ets entry points.

Hver funktion modtager ``(service, params)`` og returnerer en dict der bliver
serialiseret som JSON-svar. Funktionerne er bevidst tynde indpakninger om
``NormaRobotService``-metoderne - validering af obligatoriske parametre sker
HER (ikke i service'en) saa fejlen kan konverteres til HTTP 400.

At importere dette modul registrerer alle handlers paa den globale ``registry``
i ``dispatcher.py``. Det er bivirkningen vi accepterer for at have et
self-contained command-modul.
"""

from __future__ import print_function, unicode_literals

from norma_bridge.api.dispatcher import registry


@registry.register("say")
def cmd_say(service, params):
    text = params.get("text")
    if text is None:
        raise ValueError("params.text mangler")
    return service.say(text, params.get("gesture"))


@registry.register("play_gesture")
def cmd_play_gesture(service, params):
    # Bevarer legacy-bagudkompatibilitet: 'gesture_name' (kanonisk) eller 'gesture'.
    name = params.get("gesture_name") or params.get("gesture")
    if not name:
        raise ValueError("params.gesture_name mangler")
    return service.play_gesture(name)


@registry.register("show_tablet_image")
def cmd_show_tablet_image(service, params):
    path = params.get("image_path")
    if not path:
        raise ValueError("params.image_path mangler")
    return service.show_tablet_image(path)


@registry.register("show_tablet_html")
def cmd_show_tablet_html(service, params):
    # Legacy-bagudkompatibilitet: 'html' (kanonisk) eller 'html_content'.
    html = params.get("html")
    if html is None:
        html = params.get("html_content")
    if html is None:
        raise ValueError("params.html mangler")
    return service.show_tablet_html(html)


@registry.register("show_tablet_url")
def cmd_show_tablet_url(service, params):
    url = params.get("url")
    if not url:
        raise ValueError("params.url mangler")
    return service.show_tablet_url(url)


@registry.register("hide_tablet")
def cmd_hide_tablet(service, params):
    return service.hide_tablet()


@registry.register("get_status")
def cmd_get_status(service, params):
    return service.get_status()

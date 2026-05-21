# -*- coding: utf-8 -*-
"""NormaRobotService - tradsikker NAOqi-wrapper.

Refaktoreret fra ``_legacy.py`` linjer 67-149. Aendringer ift. legacy:

- ``__init__`` er en ren constructor. Intro-flowet er flyttet til ``intro.py``.
- Tablet-HTML/data-URI bruger ``tablet.py``-helpers (ingen lokal duplikering).
- Gesture-cycling kalder ``gestures.cycle_gesture`` (ingen lokal duplikering).
- Logning routes gennem stdlib ``logging`` i stedet for ``print()``.
- Ny offentlig metode ``show_tablet_url`` til at pege tabletten paa en URL.

Den offentlige API matcher 1:1 ``FakeRobotService``-kontrakten i ``fakes.py``.
Hvis du aendrer en metodes return-vaerdi her, skal du aendre den paa fake'en
i samme commit.
"""

from __future__ import print_function, unicode_literals

import logging
import os
import threading

try:
    from naoqi import ALProxy
except ImportError:
    # Tillader at modulet kan importeres paa en udviklermaskine uden NAOqi.
    # Constructor hejser eksplicit fejl naar nogen forsoeger at instantiere.
    ALProxy = None

from norma_bridge.robot.gestures import DEFAULT_GESTURES, cycle_gesture
from norma_bridge.robot import tablet


_log = logging.getLogger(__name__)


try:
    _text_type = unicode  # Py 2.7
except NameError:
    _text_type = str  # Py 3 (kun for import-renhed; aldrig kaldt der)


def _to_naoqi_str(value):
    # unicode_literals goer projektets strenge til unicode, men NAOqi's
    # SWIG-binding rejecter unicode med 'Wrong number or type of arguments'.
    if isinstance(value, bytes):
        return value
    if isinstance(value, _text_type):
        return value.encode("utf-8")
    return str(value)


class NormaRobotService(object):
    """Tradsikker wrapper omkring NAOqi-proxies (TTS, animation, tablet).

    Argumenter:
        robot_ip: IP-adresse paa robotten (fx "192.168.1.156").
        robot_port: NAOqi-port. Default 9559.
        gestures: sekvens af gesture-tags brugt af cycling-logikken i ``say()``.
            Default er ``DEFAULT_GESTURES``. Kan overrides via config.

    Hejser:
        RuntimeError hvis NAOqi ikke kan importeres (vi koerer ikke paa en
        robot-maskine eller har ikke installeret SDK'et).
    """

    def __init__(self, robot_ip, robot_port=9559, gestures=DEFAULT_GESTURES):
        if ALProxy is None:
            raise RuntimeError(
                "NAOqi ALProxy ikke tilgaengelig. NormaRobotService kraever "
                "Python 2.7 + NAOqi SDK. Brug FakeRobotService til lokal test."
            )
        self.robot_ip = robot_ip
        self.robot_port = robot_port
        self._gestures = tuple(gestures) if gestures else ()
        self._interaction_count = 0
        self._lock = threading.RLock()
        # NAOqi-proxies. Disse blokerer indtil forbindelsen er etableret.
        # Module-navne og IP encodes til bytes - NAOqi's SWIG-binding accepterer ikke unicode.
        ip_bytes = _to_naoqi_str(robot_ip)
        self._tts = ALProxy(_to_naoqi_str("ALTextToSpeech"), ip_bytes, robot_port)
        self._anim = ALProxy(_to_naoqi_str("ALAnimationPlayer"), ip_bytes, robot_port)
        self._tablet = ALProxy(_to_naoqi_str("ALTabletService"), ip_bytes, robot_port)

    # ------------- intern hjaelper -------------
    def _ensure_unicode(self, text):
        """Konverter input til unicode (bevarer Py 2/3-kompatibilitet)."""
        if text is None:
            return u""
        if isinstance(text, bytes):
            return text.decode("utf-8", errors="replace")
        return text

    def _to_tts_bytes(self, utext):
        """ALTextToSpeech.say forventer UTF-8 bytes paa Py 2.7."""
        return utext.encode("utf-8")

    def _hide_tablet_safe(self):
        """Forsoeg at skjule webview foer der vises noget nyt.

        Fejl er bevidst ignoreret - hvis der ikke var noget vist i forvejen
        kaster NAOqi en exception, og det er ufarligt.
        """
        try:
            self._tablet.hideWebview()
        except Exception as e:
            _log.debug("hideWebview ignoreret: %s", e)

    # ------------- offentlige metoder -------------
    def say(self, text, gesture=None):
        """Sig ``text`` via TTS, evt. ledsaget af en gesture.

        Hvis ``gesture`` er None bruges cycling-logikken (hver anden interaktion
        faar en gesture fra ``self._gestures``).
        """
        with self._lock:
            utext = self._ensure_unicode(text)
            self._interaction_count += 1
            self._tts.say(self._to_tts_bytes(utext))
            chosen_gesture = gesture or cycle_gesture(
                self._interaction_count, self._gestures
            )
            if chosen_gesture:
                try:
                    self._anim.runTag(_to_naoqi_str(chosen_gesture))
                except Exception as e:
                    _log.warning("Gesture-fejl (%s): %s", chosen_gesture, e)
            return {
                "spoken_text": utext,
                "gesture": chosen_gesture,
                "interaction_count": self._interaction_count,
            }

    def play_gesture(self, gesture_name):
        """Afspil en named gesture/animation. Hejser ValueError hvis tom."""
        with self._lock:
            if not gesture_name:
                raise ValueError("gesture_name mangler")
            self._anim.runTag(_to_naoqi_str(gesture_name))
            return {"played": gesture_name}

    def show_tablet_image(self, image_path):
        """Vis et lokalt billede paa tabletten (legacy data-URI flow).

        Hejser IOError hvis filen ikke findes.
        """
        with self._lock:
            html = tablet.image_path_to_html(image_path)
            uri, _ = tablet.html_to_data_uri(html)
            self._hide_tablet_safe()
            self._tablet.showWebview(_to_naoqi_str(uri))
            return {"shown_image": os.path.abspath(image_path)}

    def show_tablet_html(self, html_content):
        """Vis en HTML-streng paa tabletten (legacy data-URI flow).

        Hejser ValueError hvis ``html_content`` er None.
        """
        with self._lock:
            uri, byte_length = tablet.html_to_data_uri(html_content)
            self._hide_tablet_safe()
            self._tablet.showWebview(_to_naoqi_str(uri))
            return {"html_length": byte_length}

    def show_tablet_url(self, url):
        """Peg tablet-WebView paa en URL. Foretrukket flow til norma-ui."""
        with self._lock:
            if not url:
                raise ValueError("url mangler")
            self._hide_tablet_safe()
            self._tablet.showWebview(_to_naoqi_str(url))
            return {"shown_url": url}

    def hide_tablet(self):
        """Skjul tabletten."""
        with self._lock:
            self._tablet.hideWebview()
            return {"hidden": True}

    def get_status(self):
        """Returner status som ``{ip, port, interaction_count}``."""
        with self._lock:
            return {
                "ip": self.robot_ip,
                "port": self.robot_port,
                "interaction_count": self._interaction_count,
            }

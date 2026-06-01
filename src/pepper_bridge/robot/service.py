# -*- coding: utf-8 -*-
"""PepperRobotService - tradsikker NAOqi-wrapper.

Den offentlige API matcher 1:1 ``FakeRobotService``-kontrakten i ``fakes.py``.
Hvis du aendrer en metodes return-vaerdi her, skal du aendre den paa fake'en
i samme commit.
"""

from __future__ import print_function, unicode_literals

import logging
import os
import threading
import time

try:
    from naoqi import ALProxy
except ImportError:
    # Tillader at modulet kan importeres paa en udviklermaskine uden NAOqi.
    # Constructor hejser eksplicit fejl naar nogen forsoeger at instantiere.
    ALProxy = None

from pepper_bridge.robot.gestures import DEFAULT_GESTURES, cycle_gesture
from pepper_bridge.robot import tablet


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


# NAOqi-fejl med disse markers behandles som transient og udloeser proxy-recreate.
# Hold listen lille og praecis - vi vil ikke fange genuine programmer-fejl.
_TRANSIENT_NAOQI_MARKERS = (
    "module destroyed",
)


def _is_transient_naoqi_error(exc):
    if not isinstance(exc, RuntimeError):
        return False
    msg = str(exc).lower()
    return any(marker in msg for marker in _TRANSIENT_NAOQI_MARKERS)


# Mapping fra proxy-attribut til NAOqi-modul-navn. Bruges af _recreate_proxy.
_PROXY_MODULES = {
    "_tts": "ALTextToSpeech",
    "_anim": "ALAnimationPlayer",
    "_tablet": "ALTabletService",
}


class PepperRobotService(object):
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
                "NAOqi ALProxy ikke tilgaengelig. PepperRobotService kraever "
                "Python 2.7 + NAOqi SDK. Brug FakeRobotService til lokal test."
            )
        self.robot_ip = robot_ip
        self.robot_port = robot_port
        self._gestures = tuple(gestures) if gestures else ()
        self._interaction_count = 0
        self._lock = threading.RLock()
        # NAOqi-proxies. Initial konstruktion blokerer indtil forbindelse.
        # _recreate_proxy haandterer baade foerste-konstruktion og senere reconnect.
        self._tts = None
        self._anim = None
        self._tablet = None
        for attr in _PROXY_MODULES:
            self._recreate_proxy(attr)

    # ------------- intern hjaelper -------------

    def _recreate_proxy(self, attr_name):
        """Konstruer (eller genopret) en NAOqi-proxy ved attribut-navn.

        Kalderen er ansvarlig for at vaere indenfor ``self._lock`` (eller at
        koere i constructor for foerste-konstruktion). Modul-navn og IP
        encodes til bytes - NAOqi's SWIG-binding accepterer ikke unicode.
        """
        module_name = _PROXY_MODULES[attr_name]
        new_proxy = ALProxy(
            _to_naoqi_str(module_name),
            _to_naoqi_str(self.robot_ip),
            self.robot_port,
        )
        setattr(self, attr_name, new_proxy)

    def _safe_call(self, proxy_attr, method_name, *args):
        """Kald metode paa NAOqi-proxy med automatisk reconnect ved transient fejl.

        Hvis forbindelsen er gaaet tabt (typisk fordi NAOqi-modulet er restartet
        eller robotten har mistet wifi midlertidigt), genoprettes proxy'en og
        kaldet retries een gang. Andre fejl propageres uaendret.

        Kalderen er ansvarlig for at vaere indenfor ``self._lock``.
        """
        proxy = getattr(self, proxy_attr)
        try:
            return getattr(proxy, method_name)(*args)
        except RuntimeError as e:
            if not _is_transient_naoqi_error(e):
                raise
            _log.warning(
                "Transient NAOqi-fejl paa %s.%s: %s - genopretter proxy og retry",
                proxy_attr, method_name, e,
            )
            self._recreate_proxy(proxy_attr)
            return getattr(getattr(self, proxy_attr), method_name)(*args)

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
            self._safe_call("_tablet", "hideWebview")
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
            self._safe_call("_tts", "say", self._to_tts_bytes(utext))
            chosen_gesture = gesture or cycle_gesture(
                self._interaction_count, self._gestures
            )
            if chosen_gesture:
                try:
                    self._safe_call("_anim", "runTag", _to_naoqi_str(chosen_gesture))
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
            self._safe_call("_anim", "runTag", _to_naoqi_str(gesture_name))
            return {"played": gesture_name}

    def show_tablet_image(self, image_path):
        """Vis et lokalt billede paa tabletten (legacy data-URI flow).

        Hejser IOError hvis filen ikke findes.
        """
        with self._lock:
            html = tablet.image_path_to_html(image_path)
            uri, _ = tablet.html_to_data_uri(html)
            self._hide_tablet_safe()
            self._safe_call("_tablet", "showWebview", _to_naoqi_str(uri))
            return {"shown_image": os.path.abspath(image_path)}

    def show_tablet_html(self, html_content):
        """Vis en HTML-streng paa tabletten (legacy data-URI flow).

        Hejser ValueError hvis ``html_content`` er None.
        """
        with self._lock:
            uri, byte_length = tablet.html_to_data_uri(html_content)
            self._hide_tablet_safe()
            self._safe_call("_tablet", "showWebview", _to_naoqi_str(uri))
            return {"html_length": byte_length}

    def show_tablet_url(self, url):
        """Peg tablet-WebView paa en URL. Foretrukket flow til ekstern WebView-side."""
        with self._lock:
            if not url:
                raise ValueError("url mangler")
            # We might not need the sleep and wakeups, but it works
            self._safe_call("_tablet", "wakeUp")
            time.sleep(1)

            self._hide_tablet_safe()
            time.sleep(1)
            
            self._safe_call("_tablet", "showWebview", _to_naoqi_str(url))
            return {"shown_url": url}

    def hide_tablet(self):
        """Skjul tabletten."""
        with self._lock:
            self._safe_call("_tablet", "hideWebview")
            return {"hidden": True}

    def get_status(self):
        """Returner status som ``{ip, port, interaction_count}``."""
        with self._lock:
            return {
                "ip": self.robot_ip,
                "port": self.robot_port,
                "interaction_count": self._interaction_count,
            }

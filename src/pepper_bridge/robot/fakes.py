# -*- coding: utf-8 -*-
"""FakeRobotService - in-memory implementering af PepperRobotService.

Bruges til unit-tests, kontrakttests og lokal HTTP-server-koersel uden
NAOqi/robot (``pepper-bridge --fake``).

Skal matche return-vaerdier 1:1 med den rigtige PepperRobotService. Hvis du
aendrer kontrakten paa den ene, skal du aendre den paa den anden i samme commit.
"""

from __future__ import print_function, unicode_literals

import os
import threading

from pepper_bridge.robot.gestures import DEFAULT_GESTURES, cycle_gesture


class FakeRobotService(object):
    """In-memory fake der overholder PepperRobotService's offentlige API.

    Hver kommando appender en post til ``self.history`` saa tests kan asserte
    paa rakkefoelgen og argumenterne. Returnerer dicts med samme noegler som
    den rigtige service.

    Trådsikker via RLock - matcher den rigtige service's beskyttelsesmoenster.
    """

    def __init__(self, robot_ip="fake.robot.local", robot_port=9559,
                 gestures=DEFAULT_GESTURES):
        self.robot_ip = robot_ip
        self.robot_port = robot_port
        self._gestures = tuple(gestures) if gestures else ()
        self._interaction_count = 0
        self._lock = threading.RLock()
        # Test-hjaelpere
        self.history = []  # list of dicts: {'op': str, ...}

    # ------------------ offentlige service-metoder ------------------
    def say(self, text, gesture=None):
        with self._lock:
            self._interaction_count += 1
            chosen_gesture = gesture or cycle_gesture(
                self._interaction_count, self._gestures
            )
            entry = {
                "op": "say",
                "text": text,
                "gesture": chosen_gesture,
                "interaction_count": self._interaction_count,
            }
            self.history.append(entry)
            return {
                "spoken_text": text,
                "gesture": chosen_gesture,
                "interaction_count": self._interaction_count,
            }

    def play_gesture(self, gesture_name):
        with self._lock:
            if not gesture_name:
                raise ValueError("gesture_name mangler")
            self.history.append({"op": "play_gesture", "gesture_name": gesture_name})
            return {"played": gesture_name}

    def show_tablet_image(self, image_path):
        with self._lock:
            if not image_path or not os.path.exists(image_path):
                raise IOError("Billedfil ikke fundet: %s" % (image_path,))
            abs_path = os.path.abspath(image_path)
            self.history.append({"op": "show_tablet_image", "image_path": abs_path})
            return {"shown_image": abs_path}

    def show_tablet_html(self, html_content):
        with self._lock:
            if html_content is None:
                raise ValueError("html_content mangler")
            if isinstance(html_content, bytes):
                html_bytes = html_content
            else:
                html_bytes = html_content.encode("utf-8")
            self.history.append({"op": "show_tablet_html", "length": len(html_bytes)})
            return {"html_length": len(html_bytes)}

    def show_tablet_url(self, url):
        with self._lock:
            if not url:
                raise ValueError("url mangler")
            self.history.append({"op": "show_tablet_url", "url": url})
            return {"shown_url": url}

    def hide_tablet(self):
        with self._lock:
            self.history.append({"op": "hide_tablet"})
            return {"hidden": True}

    def get_status(self):
        with self._lock:
            return {
                "ip": self.robot_ip,
                "port": self.robot_port,
                "interaction_count": self._interaction_count,
            }

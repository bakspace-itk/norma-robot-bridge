# -*- coding: utf-8 -*-
"""HTTP request handler bygget som factory.

``make_handler(service)`` returnerer en ``BaseHTTPRequestHandler``-subklasse
bundet til en konkret service. Dispatch-logikken ligger i
``api/dispatcher.py`` + ``api/commands.py``.

Fejl-koder:
- ``ValueError`` (ukendt kommando, manglende parametre) -> 400
- ``IOError``/``OSError`` (klient-angivet sti findes ikke) -> 400
- Alt andet (NAOqi-fejl, intern bug) -> 500
- Ukendte ruter -> 404
"""

from __future__ import print_function, unicode_literals

import json
import logging

try:
    # Python 2.7
    from BaseHTTPServer import BaseHTTPRequestHandler
except ImportError:
    # Python 3
    from http.server import BaseHTTPRequestHandler

from pepper_bridge.api.dispatcher import registry
import pepper_bridge.api.commands  # noqa: F401 - import for at registrere handlers


_log = logging.getLogger(__name__)


def make_handler(service):
    """Returner en ``BaseHTTPRequestHandler``-subklasse bundet til en konkret service.

    Eliminerer den globale ``ApiHandler.service``-klassevariabel fra legacy.
    Hvert kald giver en ny klasse - flere bridge-instanser kan koere samtidig
    i samme proces hvis det skulle behoeves.

    Argumenter:
        service: en ``PepperRobotService`` eller ``FakeRobotService``.

    Returnerer:
        En klasse der kan bruges som ``HTTPServer(server_address, klassen)``.
    """

    class ApiHandler(BaseHTTPRequestHandler):
        # Lukkebundet til service-instansen - ikke en klassevariabel der kan
        # ovverskrives udefra.
        _service = service

        # ---- helpers ----
        def _send_json(self, status_code, payload):
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _send_error(self, status_code, message):
            self._send_json(status_code, {"status": "error", "message": message})

        def _send_success(self, data):
            self._send_json(200, {"status": "success", "data": data})

        def _read_body(self):
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0:
                return b""
            return self.rfile.read(length)

        def _handle_dispatch(self, command, params):
            """Faelles fejlhaandtering for dispatch-kald."""
            try:
                result = registry.dispatch(self._service, command, params)
                self._send_success(result)
            except ValueError as e:
                # Klient-fejl: ukendt kommando, manglende/ugyldige parametre
                self._send_error(400, str(e))
            except (IOError, OSError) as e:
                # Klient-angivet sti findes ikke (fx show_tablet_image)
                self._send_error(400, str(e))
            except Exception as e:
                # NAOqi-fejl, intern bug, etc.
                _log.exception("Intern fejl i dispatch af %r", command)
                self._send_error(500, str(e))

        # ---- HTTP-metoder ----
        def do_POST(self):
            if self.path != "/api/command":
                return self._send_error(404, "Not Found")

            raw = self._read_body()
            try:
                payload = json.loads(raw.decode("utf-8")) if raw else {}
            except (ValueError, UnicodeDecodeError) as e:
                return self._send_error(400, "Ugyldig JSON: %s" % e)

            if not isinstance(payload, dict):
                return self._send_error(400, "Body skal vaere et JSON-objekt")

            self._handle_dispatch(payload.get("command"), payload.get("params"))

        def do_GET(self):
            if self.path == "/api/status":
                # Genbrug get_status-kommandoen saa den lever ét sted.
                return self._handle_dispatch("get_status", None)
            self._send_error(404, "Not Found")

        # ---- logging ----
        def log_message(self, fmt, *args):
            # Default-implementeringen skriver til stderr - vi vil have det
            # gennem vores logger.
            _log.info("%s - %s", self.address_string(), fmt % args)

    return ApiHandler

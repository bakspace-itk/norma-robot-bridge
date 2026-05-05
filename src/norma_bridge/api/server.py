# -*- coding: utf-8 -*-
"""Threaded HTTP-server.

Refaktoreret fra ``_legacy.py:ThreadedHTTPServer`` (linjer 235-237) og
``run_server`` (linjer 325-342).

NormaRobotService er trådsikker (RLock), saa serveren kan haandtere flere
samtidige requests. Hver kommando er hurtig (TTS-kaldet bloker mens robotten
taler, men det er ikke vores problem at parallelisere det - lad NAOqi
serialisere selv).
"""

from __future__ import print_function, unicode_literals

import logging

try:
    # Python 2.7
    from BaseHTTPServer import HTTPServer
    from SocketServer import ThreadingMixIn
except ImportError:
    # Python 3
    from http.server import HTTPServer
    from socketserver import ThreadingMixIn


_log = logging.getLogger(__name__)


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """HTTP-server der haandterer hver request i sin egen tråd.

    ``daemon_threads = True`` saa serveren kan lukkes selv om en langsom
    request (fx en hangende TTS) stadig koerer.
    """

    daemon_threads = True
    # Tillader hurtig genstart efter Ctrl+C uden TIME_WAIT-foredrag.
    allow_reuse_address = True


def serve(handler_cls, host="", port=8080):
    """Start serveren og bloker indtil ``KeyboardInterrupt``.

    Argumenter:
        handler_cls: handler-klassen fra ``make_handler(service)``.
        host: interface der lyttes paa. Default tom = alle interfaces.
        port: TCP-port. Default 8080.
    """
    httpd = ThreadedHTTPServer((host, port), handler_cls)
    _log.info("Norma bridge lytter paa %s:%d", host or "0.0.0.0", port)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        _log.info("Stopper bridge (Ctrl+C)")
    finally:
        httpd.server_close()

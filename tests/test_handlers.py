# -*- coding: utf-8 -*-
"""Integration-tests for HTTP-handler + threaded server.

Vi starter en rigtig server paa en ledig localhost-port mod en
``FakeRobotService`` og kalder den med stdlib-urllib (saa testene ikke
kraver requests). Det verificerer baade routing, JSON-parsing,
fejl-status-koder og at threading-serveren overhovedet starter.
"""

from __future__ import print_function, unicode_literals

import json
import os
import socket
import tempfile
import threading

import pytest

try:
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError
except ImportError:  # Py 2
    from urllib2 import Request, urlopen, HTTPError

from pepper_bridge.api.handlers import make_handler
from pepper_bridge.api.server import ThreadedHTTPServer
from pepper_bridge.robot.fakes import FakeRobotService


# -------- HTTP-helpers -------- #

def _http(method, url, payload=None):
    """Mini-helper til at kalde test-serveren. Returnerer (status_code, json_body).

    Bemaerk: ``method``-parameteren er kun til laesbarhed - urllib udleder
    GET/POST automatisk ud fra om ``data`` er angivet eller ej. (Eksplicit
    ``method``-kwarg findes ikke i Py 2.7's urllib2.)
    """
    body = None
    headers = {}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = Request(url, data=body, headers=headers)
    try:
        resp = urlopen(req, timeout=2)
        return resp.getcode(), json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))


def _http_raw(method, url, raw_body, content_type="application/json"):
    """Send et raw byte-body (til JSON-parse-fejl-tests)."""
    headers = {"Content-Type": content_type}
    req = Request(url, data=raw_body, headers=headers)
    try:
        resp = urlopen(req, timeout=2)
        return resp.getcode(), resp.read()
    except HTTPError as e:
        return e.code, e.read()


# -------- fixtures -------- #

@pytest.fixture
def svc():
    return FakeRobotService(robot_ip="127.0.0.1", robot_port=9559)


@pytest.fixture
def server(svc):
    """Spin en ThreadedHTTPServer op paa en ledig port. Tear down efter test."""
    handler_cls = make_handler(svc)
    httpd = ThreadedHTTPServer(("127.0.0.1", 0), handler_cls)
    port = httpd.server_address[1]
    thr = threading.Thread(target=httpd.serve_forever, name="bridge-test")
    thr.daemon = True
    thr.start()
    base_url = "http://127.0.0.1:%d" % port
    try:
        yield base_url, svc
    finally:
        httpd.shutdown()
        httpd.server_close()
        thr.join(timeout=2)


# -------- GET /api/status -------- #

def test_get_status_returnerer_200_med_service_status(server):
    base, svc = server
    code, body = _http("GET", base + "/api/status")
    assert code == 200
    assert body == {
        "status": "success",
        "data": {"ip": "127.0.0.1", "port": 9559, "interaction_count": 0},
    }


def test_get_status_reflekterer_say_kald(server):
    base, svc = server
    _http("POST", base + "/api/command", {"command": "say", "params": {"text": "hej"}})
    code, body = _http("GET", base + "/api/status")
    assert body["data"]["interaction_count"] == 1


# -------- POST /api/command --------

def test_post_say_returnerer_succes(server):
    base, svc = server
    code, body = _http(
        "POST", base + "/api/command",
        {"command": "say", "params": {"text": "Hello world"}},
    )
    assert code == 200
    assert body["status"] == "success"
    assert body["data"]["spoken_text"] == "Hello world"


def test_post_med_unicode_haandterer_aeoeaa(server):
    """UTF-8 round-trip - request, dispatch og response skal alle bevare aeoeaa."""
    base, svc = server
    code, body = _http(
        "POST", base + "/api/command",
        {"command": "say", "params": {"text": "Hej æøå"}},
    )
    assert code == 200
    assert body["data"]["spoken_text"] == "Hej æøå"


def test_post_play_gesture_med_legacy_alias(server):
    base, svc = server
    code, body = _http(
        "POST", base + "/api/command",
        {"command": "play_gesture", "params": {"gesture": "hello"}},
    )
    assert code == 200
    assert body["data"] == {"played": "hello"}


def test_post_show_tablet_url(server):
    base, svc = server
    code, body = _http(
        "POST", base + "/api/command",
        {"command": "show_tablet_url", "params": {"url": "http://x.local"}},
    )
    assert code == 200
    assert body["data"] == {"shown_url": "http://x.local"}


def test_post_uden_params_paa_kommandoer_uden_params(server):
    """hide_tablet og get_status maa ikke kraeve at klienten sender 'params'."""
    base, _ = server
    code, body = _http("POST", base + "/api/command", {"command": "hide_tablet"})
    assert code == 200
    assert body["data"] == {"hidden": True}


# -------- POST 400-fejl --------

def test_post_med_ukendt_kommando_giver_400(server):
    base, _ = server
    code, body = _http(
        "POST", base + "/api/command",
        {"command": "doesnt_exist", "params": {}},
    )
    assert code == 400
    assert body["status"] == "error"
    assert "Ukendt" in body["message"]


def test_post_say_uden_text_giver_400(server):
    base, _ = server
    code, body = _http("POST", base + "/api/command", {"command": "say", "params": {}})
    assert code == 400
    assert "params.text" in body["message"]


def test_post_med_tom_command_giver_400(server):
    base, _ = server
    code, body = _http("POST", base + "/api/command", {"command": "", "params": {}})
    assert code == 400


def test_post_uden_command_giver_400(server):
    base, _ = server
    code, body = _http("POST", base + "/api/command", {"params": {}})
    assert code == 400


def test_post_med_ugyldig_json_giver_400(server):
    base, _ = server
    code, body = _http_raw("POST", base + "/api/command", b"not json at all{{")
    assert code == 400
    payload = json.loads(body.decode("utf-8"))
    assert "Ugyldig JSON" in payload["message"]


def test_post_med_array_body_giver_400(server):
    """Body skal vaere et JSON-objekt - ikke en liste eller streng."""
    base, _ = server
    code, body = _http_raw("POST", base + "/api/command", b'["not", "an", "object"]')
    assert code == 400


def test_post_show_tablet_image_med_manglende_fil_giver_400(server):
    base, _ = server
    code, body = _http(
        "POST", base + "/api/command",
        {"command": "show_tablet_image", "params": {"image_path": "/findes/ikke.png"}},
    )
    assert code == 400
    assert "ikke fundet" in body["message"]


def test_post_show_tablet_image_med_eksisterende_fil_giver_200(server):
    base, _ = server
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        f.write(b"x")
        path = f.name
    try:
        code, body = _http(
            "POST", base + "/api/command",
            {"command": "show_tablet_image", "params": {"image_path": path}},
        )
        assert code == 200
        assert body["data"]["shown_image"].endswith(os.path.basename(path))
    finally:
        os.unlink(path)


# -------- POST 500-fejl --------

def test_post_med_intern_fejl_giver_500():
    """En uventet exception fra service-laget skal blive 500, ikke 400."""

    class BoomService(object):
        def get_status(self):
            raise RuntimeError("intern eksplosion")

    handler_cls = make_handler(BoomService())
    httpd = ThreadedHTTPServer(("127.0.0.1", 0), handler_cls)
    port = httpd.server_address[1]
    thr = threading.Thread(target=httpd.serve_forever)
    thr.daemon = True
    thr.start()
    try:
        code, body = _http("GET", "http://127.0.0.1:%d/api/status" % port)
        assert code == 500
        assert body["status"] == "error"
        assert "intern eksplosion" in body["message"]
    finally:
        httpd.shutdown()
        httpd.server_close()
        thr.join(timeout=2)


# -------- 404 / metode-routing --------

def test_get_paa_ukendt_path_giver_404(server):
    base, _ = server
    code, body = _http("GET", base + "/api/something_else")
    assert code == 404


def test_post_paa_ukendt_path_giver_404(server):
    base, _ = server
    code, body = _http("POST", base + "/api/foo", {})
    assert code == 404


def test_get_paa_command_path_giver_404(server):
    """/api/command er kun POST - GET skal give 404."""
    base, _ = server
    code, body = _http("GET", base + "/api/command")
    assert code == 404


# -------- factory-pattern -------- #

def test_make_handler_binder_service_via_closure_ikke_klassevariabel():
    """Regression: legacy havde 'service = None' som klassevariabel.

    Nu skal hvert kald til make_handler returnere en NY klasse bundet til
    sin egen service - ingen delt globaltilstand.
    """
    svc1 = FakeRobotService(robot_ip="1.1.1.1")
    svc2 = FakeRobotService(robot_ip="2.2.2.2")
    handler1 = make_handler(svc1)
    handler2 = make_handler(svc2)

    assert handler1 is not handler2
    # Hver klasse har sin egen lukkebundne service
    assert handler1._service is svc1
    assert handler2._service is svc2


def test_make_handler_kan_bruges_med_to_servere_samtidig():
    """To bridges paa to forskellige porte med hver sin service - ingen interferens."""
    svc1 = FakeRobotService(robot_ip="1.1.1.1", robot_port=9001)
    svc2 = FakeRobotService(robot_ip="2.2.2.2", robot_port=9002)

    httpd1 = ThreadedHTTPServer(("127.0.0.1", 0), make_handler(svc1))
    httpd2 = ThreadedHTTPServer(("127.0.0.1", 0), make_handler(svc2))

    t1 = threading.Thread(target=httpd1.serve_forever)
    t2 = threading.Thread(target=httpd2.serve_forever)
    t1.daemon = True
    t2.daemon = True
    t1.start()
    t2.start()
    try:
        url1 = "http://127.0.0.1:%d/api/status" % httpd1.server_address[1]
        url2 = "http://127.0.0.1:%d/api/status" % httpd2.server_address[1]
        code1, body1 = _http("GET", url1)
        code2, body2 = _http("GET", url2)
        assert body1["data"]["ip"] == "1.1.1.1"
        assert body2["data"]["ip"] == "2.2.2.2"
    finally:
        httpd1.shutdown(); httpd1.server_close(); t1.join(timeout=2)
        httpd2.shutdown(); httpd2.server_close(); t2.join(timeout=2)

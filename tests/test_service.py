# -*- coding: utf-8 -*-
"""Tests for NormaRobotService med mocked NAOqi.

Verificerer at den rigtige service-klasse:

- har samme offentlige API (return-vaerdier, exceptions) som FakeRobotService
- ikke koerer intro-flow i constructor (legacy bug)
- bruger de udtrukne tablet-/gesture-helpers
- routes alle NAOqi-kald gennem RLock-beskyttede metoder

Vi mocker ``ALProxy`` paa modul-niveau saa testene kan koere paa Py 3 uden
NAOqi installeret.
"""

from __future__ import print_function, unicode_literals

import os
import sys
import tempfile

import pytest

try:
    from unittest.mock import MagicMock, patch, call
except ImportError:  # Py 2
    from mock import MagicMock, patch, call  # noqa


# -------- fixtures --------

@pytest.fixture
def proxies():
    """Tre mock-proxies, returneret i den rakkefolge ALProxy bliver kaldt:
    ALTextToSpeech, ALAnimationPlayer, ALTabletService.
    """
    tts = MagicMock(name="ALTextToSpeech")
    anim = MagicMock(name="ALAnimationPlayer")
    tab = MagicMock(name="ALTabletService")
    return tts, anim, tab


@pytest.fixture
def service(proxies):
    """Konstruer en NormaRobotService med mockede ALProxy-konstruktioner.

    Vi patcher modul-globalen ``norma_bridge.robot.service.ALProxy`` saa
    constructorens kald af ``ALProxy(name, ip, port)`` returnerer vores mocks.
    """
    tts, anim, tab = proxies

    def fake_proxy(name, ip, port):
        # Service encoder modul-navne til bytes for NAOqi - decode tilbage til
        # dict-opslag, saa testen ikke skal bruge baade unicode- og bytes-noegler.
        key = name.decode("utf-8") if isinstance(name, bytes) else name
        return {
            "ALTextToSpeech": tts,
            "ALAnimationPlayer": anim,
            "ALTabletService": tab,
        }[key]

    with patch("norma_bridge.robot.service.ALProxy", side_effect=fake_proxy):
        from norma_bridge.robot.service import NormaRobotService
        svc = NormaRobotService("10.0.0.1", 9559, gestures=("a", "b", "c"))
        yield svc


# -------- _to_naoqi_str --------

def test_to_naoqi_str_encoder_unicode_til_utf8_bytes():
    from norma_bridge.robot.service import _to_naoqi_str
    assert _to_naoqi_str("ALTextToSpeech") == b"ALTextToSpeech"
    assert _to_naoqi_str(u"æøå") == b"\xc3\xa6\xc3\xb8\xc3\xa5"


def test_to_naoqi_str_lader_bytes_vaere():
    from norma_bridge.robot.service import _to_naoqi_str
    assert _to_naoqi_str(b"already-bytes") == b"already-bytes"


# -------- constructor --------

def test_init_kaster_runtime_error_naar_naoqi_mangler():
    """Hvis ALProxy er None (NAOqi ikke importerbar) skal init fejle eksplicit."""
    with patch("norma_bridge.robot.service.ALProxy", None):
        from norma_bridge.robot.service import NormaRobotService
        with pytest.raises(RuntimeError) as exc_info:
            NormaRobotService("10.0.0.1", 9559)
        assert "NAOqi" in str(exc_info.value)


def test_init_opretter_tre_alproxy_instanser_med_korrekt_ip_og_port(proxies):
    """Constructor skal kalde ALProxy(navn, ip, port) tre gange."""
    tts, anim, tab = proxies

    def fake_proxy(name, ip, port):
        key = name.decode("utf-8") if isinstance(name, bytes) else name
        return {"ALTextToSpeech": tts, "ALAnimationPlayer": anim, "ALTabletService": tab}[key]

    with patch("norma_bridge.robot.service.ALProxy", side_effect=fake_proxy) as mock_proxy:
        from norma_bridge.robot.service import NormaRobotService
        NormaRobotService("10.0.0.1", 9559)

    # NAOqi's SWIG-binding kraever bytes for char*-argumenter; service encoder
    # baade modul-navn og IP til UTF-8.
    expected = [
        call(b"ALTextToSpeech", b"10.0.0.1", 9559),
        call(b"ALAnimationPlayer", b"10.0.0.1", 9559),
        call(b"ALTabletService", b"10.0.0.1", 9559),
    ]
    assert mock_proxy.call_args_list == expected


def test_init_kalder_ikke_intro_eller_anden_robot_handling(proxies, service):
    """Refaktor-bug-regression: legacy kaldte _startup_intro() i __init__.

    Den ny service skal kun konstruere proxies og initialisere state - INGEN
    runTag, say, eller showWebview maa vaere kaldt.
    """
    tts, anim, tab = proxies
    assert tts.say.call_count == 0
    assert anim.runTag.call_count == 0
    assert tab.showWebview.call_count == 0
    assert tab.hideWebview.call_count == 0


def test_init_starter_med_interaction_count_nul(service):
    assert service.get_status()["interaction_count"] == 0


# -------- say --------

def test_say_kalder_tts_med_utf8_bytes(proxies, service):
    tts, _, _ = proxies
    service.say("æøå")
    tts.say.assert_called_once()
    arg = tts.say.call_args[0][0]
    assert isinstance(arg, bytes)
    assert arg == "æøå".encode("utf-8")


def test_say_returnerer_kontrakt_dict(service):
    result = service.say("hej")
    assert set(result.keys()) == {"spoken_text", "gesture", "interaction_count"}
    assert result["spoken_text"] == "hej"
    assert result["interaction_count"] == 1


def test_say_inkrementerer_interaction_count(service):
    service.say("a")
    service.say("b")
    service.say("c")
    assert service.get_status()["interaction_count"] == 3


def test_say_med_eksplicit_gesture_kalder_runtag(proxies, service):
    _, anim, _ = proxies
    service.say("hej", gesture="my/gesture")
    anim.runTag.assert_called_once_with(b"my/gesture")


def test_say_uden_gesture_cykler_paa_lige_taeller(proxies, service):
    _, anim, _ = proxies
    # interaction 1 (ulige) -> ingen gesture
    service.say("a")
    # interaction 2 (lige) -> idx 2 % 3 = 2 -> "c"
    result = service.say("b")
    assert result["gesture"] == "c"
    anim.runTag.assert_called_once_with(b"c")


def test_say_gesture_fejl_stopper_ikke_tts(proxies, service):
    """Hvis runTag fejler, skal say() stadig returnere normalt (legacy-adfaerd)."""
    tts, anim, _ = proxies
    anim.runTag.side_effect = RuntimeError("anim eksploderede")
    result = service.say("hej", gesture="boom")
    assert result["spoken_text"] == "hej"
    assert result["gesture"] == "boom"
    tts.say.assert_called_once()


# -------- play_gesture --------

def test_play_gesture_kalder_runtag(proxies, service):
    _, anim, _ = proxies
    result = service.play_gesture("animations/Hey")
    anim.runTag.assert_called_once_with(b"animations/Hey")
    assert result == {"played": "animations/Hey"}


def test_play_gesture_uden_navn_kaster_value_error(proxies, service):
    _, anim, _ = proxies
    with pytest.raises(ValueError):
        service.play_gesture("")
    with pytest.raises(ValueError):
        service.play_gesture(None)
    anim.runTag.assert_not_called()


def test_play_gesture_inkrementerer_ikke_interaction_count(service):
    service.play_gesture("animations/Hey")
    assert service.get_status()["interaction_count"] == 0


# -------- show_tablet_image --------

@pytest.fixture
def tiny_png():
    """1x1 transparent PNG."""
    data = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4"
        b"\x89\x00\x00\x00\rIDATx\x9cc\xfc\xff\xff?\x00\x05\xfe\x02\xfe"
        b"\xa75\x81\x84\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        f.write(data)
        path = f.name
    yield path
    os.unlink(path)


def test_show_tablet_image_kalder_showwebview_med_data_uri(proxies, service, tiny_png):
    _, _, tab = proxies
    result = service.show_tablet_image(tiny_png)
    assert result == {"shown_image": os.path.abspath(tiny_png)}
    tab.showWebview.assert_called_once()
    uri = tab.showWebview.call_args[0][0]
    assert uri.startswith(b"data:text/html;base64,")


def test_show_tablet_image_kalder_hidewebview_foerst(proxies, service, tiny_png):
    _, _, tab = proxies
    service.show_tablet_image(tiny_png)
    # hideWebview skal vaere kaldt FOER showWebview.
    methods = [c[0] for c in tab.method_calls]
    assert methods.index("hideWebview") < methods.index("showWebview")


def test_show_tablet_image_med_manglende_fil_kaster_io_error(proxies, service):
    _, _, tab = proxies
    with pytest.raises(IOError):
        service.show_tablet_image("/findes/ikke.png")
    # Hverken hide eller show maa vaere kaldt naar billed-validering fejler.
    tab.showWebview.assert_not_called()


def test_show_tablet_image_ignorerer_hidewebview_fejl(proxies, service, tiny_png):
    """hideWebview fejler hvis intet er vist - det maa ikke stoppe show."""
    _, _, tab = proxies
    tab.hideWebview.side_effect = RuntimeError("intet at skjule")
    result = service.show_tablet_image(tiny_png)
    tab.showWebview.assert_called_once()
    assert "shown_image" in result


# -------- show_tablet_html --------

def test_show_tablet_html_kalder_showwebview_med_data_uri(proxies, service):
    _, _, tab = proxies
    result = service.show_tablet_html("<h1>Hej</h1>")
    assert result == {"html_length": len("<h1>Hej</h1>")}
    uri = tab.showWebview.call_args[0][0]
    assert uri.startswith(b"data:text/html;base64,")


def test_show_tablet_html_med_none_kaster_value_error(proxies, service):
    _, _, tab = proxies
    with pytest.raises(ValueError):
        service.show_tablet_html(None)
    tab.showWebview.assert_not_called()


# -------- show_tablet_url --------

def test_show_tablet_url_kalder_showwebview_direkte(proxies, service):
    """Bemaerk: URL'en sendes uaendret indholdsmaessigt - INGEN data-URI-konvertering.
    URL'en encodes dog til bytes ved NAOqi-graensefladen.
    """
    _, _, tab = proxies
    url = "http://norma-ui.local:8000/dialog"
    result = service.show_tablet_url(url)
    tab.showWebview.assert_called_once_with(url.encode("utf-8"))
    assert result == {"shown_url": url}


def test_show_tablet_url_med_tom_streng_kaster_value_error(proxies, service):
    _, _, tab = proxies
    with pytest.raises(ValueError):
        service.show_tablet_url("")
    with pytest.raises(ValueError):
        service.show_tablet_url(None)
    tab.showWebview.assert_not_called()


# -------- hide_tablet --------

def test_hide_tablet_kalder_hidewebview(proxies, service):
    _, _, tab = proxies
    result = service.hide_tablet()
    tab.hideWebview.assert_called_once_with()
    assert result == {"hidden": True}


# -------- get_status --------

def test_get_status_returnerer_ip_port_count(service):
    service.say("a")  # bumper count til 1
    status = service.get_status()
    assert status == {"ip": "10.0.0.1", "port": 9559, "interaction_count": 1}


# -------- thread-sikkerhed --------

def test_concurrent_say_kalder_tradsikkert(proxies, service):
    """RLock skal serialisere kald saa interaction_count ikke racer."""
    import threading
    errors = []

    def worker():
        try:
            service.say("concurrent")
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(30)]
    for thr in threads:
        thr.start()
    for thr in threads:
        thr.join()

    assert not errors
    assert service.get_status()["interaction_count"] == 30

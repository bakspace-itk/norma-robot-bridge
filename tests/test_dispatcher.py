# -*- coding: utf-8 -*-
"""Tests for CommandRegistry - registrering og dispatch.

Disse tests bruger en frisk ``CommandRegistry()`` pr. test for at undgaa
forurening fra modul-globalen.
"""

from __future__ import print_function, unicode_literals

import pytest

from pepper_bridge.api.dispatcher import CommandRegistry


# -------- register --------

def test_register_tilfoejer_handler_til_navn():
    reg = CommandRegistry()

    @reg.register("foo")
    def handler(service, params):
        return {"ok": True}

    assert "foo" in reg.names()


def test_register_normaliserer_navn_til_lowercase_og_stripper():
    reg = CommandRegistry()

    @reg.register("  FOO  ")
    def handler(service, params):
        return {}

    assert reg.names() == ["foo"]


def test_register_med_tomt_navn_kaster_value_error():
    reg = CommandRegistry()
    with pytest.raises(ValueError):
        reg.register("")
    with pytest.raises(ValueError):
        reg.register(None)
    with pytest.raises(ValueError):
        reg.register("   ")


def test_register_med_dubletter_kaster_value_error():
    reg = CommandRegistry()

    @reg.register("foo")
    def first(service, params):
        return {"version": 1}

    with pytest.raises(ValueError) as exc_info:
        @reg.register("foo")
        def second(service, params):
            return {"version": 2}

    assert "allerede registreret" in str(exc_info.value)


def test_register_returnerer_funktionen_uaendret():
    """Decorator skal videregive funktionen saa den stadig kan kaldes direkte."""
    reg = CommandRegistry()

    @reg.register("foo")
    def handler(service, params):
        return {"called": True}

    # Funktionen kan stadig kaldes direkte (handler er ikke wrapper'et).
    assert handler(None, {}) == {"called": True}


# -------- dispatch --------

def test_dispatch_kalder_registreret_handler_med_service_og_params():
    reg = CommandRegistry()
    captured = {}

    @reg.register("say")
    def cmd_say(service, params):
        captured["service"] = service
        captured["params"] = params
        return {"ok": True}

    result = reg.dispatch("svc-instance", "say", {"text": "hej"})
    assert result == {"ok": True}
    assert captured["service"] == "svc-instance"
    assert captured["params"] == {"text": "hej"}


def test_dispatch_normaliserer_navn_lowercase_og_strip():
    reg = CommandRegistry()

    @reg.register("say")
    def handler(service, params):
        return {"hit": True}

    assert reg.dispatch(None, "  SAY  ", {}) == {"hit": True}


def test_dispatch_med_none_params_giver_tomt_dict_til_handler():
    reg = CommandRegistry()
    received = {}

    @reg.register("foo")
    def handler(service, params):
        received["params"] = params
        return {}

    reg.dispatch(None, "foo", None)
    assert received["params"] == {}


def test_dispatch_med_ukendt_kommando_kaster_value_error():
    reg = CommandRegistry()
    with pytest.raises(ValueError) as exc_info:
        reg.dispatch(None, "ukendt", {})
    assert "Ukendt" in str(exc_info.value)
    assert "ukendt" in str(exc_info.value)


def test_dispatch_med_tomt_navn_kaster_value_error():
    reg = CommandRegistry()
    with pytest.raises(ValueError) as exc_info:
        reg.dispatch(None, "", {})
    assert "command" in str(exc_info.value).lower()


def test_dispatch_med_none_navn_kaster_value_error():
    reg = CommandRegistry()
    with pytest.raises(ValueError):
        reg.dispatch(None, None, {})


def test_dispatch_videresender_handler_exception():
    """En exception fra handleren skal boble op uaendret - dispatcher
    fanger ikke fejl, det er handler-lagets job."""
    reg = CommandRegistry()

    @reg.register("boom")
    def handler(service, params):
        raise RuntimeError("intern fejl")

    with pytest.raises(RuntimeError) as exc_info:
        reg.dispatch(None, "boom", {})
    assert "intern fejl" in str(exc_info.value)


# -------- names --------

def test_names_returnerer_sorteret_liste():
    reg = CommandRegistry()
    for name in ["zoo", "alpha", "mike"]:
        @reg.register(name)
        def handler(service, params, _name=name):
            return {"name": _name}
    assert reg.names() == ["alpha", "mike", "zoo"]


def test_names_paa_tom_registry_returnerer_tom_liste():
    assert CommandRegistry().names() == []

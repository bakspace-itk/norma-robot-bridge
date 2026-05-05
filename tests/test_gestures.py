# -*- coding: utf-8 -*-
"""Tests for gestures.py - cycling-logik + default tag-liste.

Verificerer at den udtrukne pure funktion ``cycle_gesture`` overholder
samme kontrakt som den oprindelige ``_cycle_gesture_name``-metode i
legacy-monolitten (norma-archive/Norma_Output.py:152-157).
"""

from __future__ import print_function, unicode_literals

from norma_bridge.robot.gestures import (
    DEFAULT_GESTURES,
    cycle_gesture,
)


# ---------- DEFAULT_GESTURES ----------

def test_default_gesture_liste_har_10_elementer():
    """Matcher antallet i legacy-monolitten."""
    assert len(DEFAULT_GESTURES) == 10


def test_default_gesture_liste_indeholder_legacy_tags():
    """Disse tags var hardkodet i legacy. Reader skal kunne genkende dem."""
    assert "hello" in DEFAULT_GESTURES
    assert "happy" in DEFAULT_GESTURES
    assert "bow" in DEFAULT_GESTURES


def test_default_gesture_liste_er_immutable():
    """Tuple - ikke list. Forhindrer at klienter muterer den globale konstant."""
    assert isinstance(DEFAULT_GESTURES, tuple)


# ---------- cycle_gesture: ulige tæller ----------

def test_cycle_gesture_paa_ulige_taeller_er_none():
    assert cycle_gesture(1, DEFAULT_GESTURES) is None
    assert cycle_gesture(3, DEFAULT_GESTURES) is None
    assert cycle_gesture(99, DEFAULT_GESTURES) is None


# ---------- cycle_gesture: lige tæller ----------

def test_cycle_gesture_paa_lige_taeller_returnerer_indekseret_gesture():
    gestures = ("a", "b", "c")
    assert cycle_gesture(0, gestures) == "a"
    assert cycle_gesture(2, gestures) == "c"


def test_cycle_gesture_wrapper_med_modulo():
    """Naar tælleren overstiger listens laengde wrappes der rundt."""
    gestures = ("a", "b", "c")
    # 4 % 3 = 1 -> "b"
    assert cycle_gesture(4, gestures) == "b"
    # 6 % 3 = 0 -> "a"
    assert cycle_gesture(6, gestures) == "a"


def test_cycle_gesture_med_default_liste():
    """Sekvensen 0, 2, 4 skal matche legacy-listens første tre lige indeks."""
    assert cycle_gesture(0) == DEFAULT_GESTURES[0]  # "hello"
    assert cycle_gesture(2) == DEFAULT_GESTURES[2]  # "calm"
    assert cycle_gesture(4) == DEFAULT_GESTURES[4]  # "beseech"


# ---------- cycle_gesture: tom liste ----------

def test_cycle_gesture_med_tom_tuple_er_none():
    assert cycle_gesture(0, ()) is None
    assert cycle_gesture(2, ()) is None
    assert cycle_gesture(7, ()) is None


def test_cycle_gesture_med_none_liste_er_none():
    assert cycle_gesture(0, None) is None


# ---------- regression: matcher legacy-adfærd ----------

def test_cycle_gesture_matcher_legacy_taenkte_sekvens():
    """En typisk samtale-sekvens. Hver gesture-vaerdi ER kontrakten -
    aendrer den, aendrer du robotens synlige adfaerd.
    """
    expected = [
        (0, "hello"),       # interaktion 0 (lige) -> hello
        (1, None),          # interaktion 1 (ulige) -> ingen
        (2, "calm"),        # interaktion 2 (lige) -> calm
        (3, None),
        (4, "beseech"),
        (5, None),
        (10, "hello"),      # 10 % 10 = 0 -> wrap til hello
        (12, "calm"),       # 12 % 10 = 2 -> wrap til calm
    ]
    for count, expected_gesture in expected:
        assert cycle_gesture(count) == expected_gesture, \
            "interaction_count=%d gav forkert gesture" % count

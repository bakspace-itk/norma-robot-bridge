# -*- coding: utf-8 -*-
"""Tests for tablet-helpers (HTML/data-URI-konvertering).

Verificerer at de tre legacy-kodestier (intro, show_tablet_image,
show_tablet_html) nu producerer ensartet output via fælles funktioner.
"""

from __future__ import print_function, unicode_literals

import base64
import os
import re
import tempfile

import pytest

from norma_bridge.robot.tablet import (
    image_path_to_html,
    html_to_data_uri,
)


# Mindste gyldige PNG (1x1 transparent pixel).
_TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4"
    b"\x89\x00\x00\x00\rIDATx\x9cc\xfc\xff\xff?\x00\x05\xfe\x02\xfe"
    b"\xa75\x81\x84\x00\x00\x00\x00IEND\xaeB`\x82"
)


@pytest.fixture
def tiny_png_path():
    """Skriver en lille gyldig PNG til en temp-fil og returnerer stien."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        f.write(_TINY_PNG)
        path = f.name
    try:
        yield path
    finally:
        os.unlink(path)


# ---------- image_path_to_html ----------

def test_image_path_to_html_returnerer_komplet_html_dokument(tiny_png_path):
    html = image_path_to_html(tiny_png_path)
    assert html.startswith("<html>")
    assert html.endswith("</html>")
    assert "<img" in html
    assert "data:image/png;base64," in html


def test_image_path_to_html_indeholder_korrekt_base64_af_filen(tiny_png_path):
    html = image_path_to_html(tiny_png_path)
    # Træk base64-strengen ud og dekod den — den skal matche fil-indholdet.
    match = re.search(r'data:image/png;base64,([A-Za-z0-9+/=]+)"', html)
    assert match is not None, "Kunne ikke finde base64 i HTML: %r" % html[:200]
    decoded = base64.b64decode(match.group(1))
    assert decoded == _TINY_PNG


def test_image_path_to_html_inkluderer_viewport_og_centrering(tiny_png_path):
    """Skabelonen skal matche legacy-introens layout (centreret, viewport-skaleret)."""
    html = image_path_to_html(tiny_png_path)
    assert "viewport" in html
    assert "initial-scale=2.0" in html
    assert "display:flex" in html
    assert "justify-content:center" in html
    assert "align-items:center" in html


def test_image_path_to_html_med_manglende_fil_kaster_io_error():
    with pytest.raises(IOError) as exc_info:
        image_path_to_html("/findes/ikke.png")
    assert "ikke fundet" in str(exc_info.value)


def test_image_path_to_html_med_tom_sti_kaster_io_error():
    with pytest.raises(IOError):
        image_path_to_html("")


def test_image_path_to_html_med_none_kaster_io_error():
    with pytest.raises(IOError):
        image_path_to_html(None)


# ---------- html_to_data_uri ----------

def test_html_to_data_uri_basis_ascii():
    uri, length = html_to_data_uri("<h1>Hej</h1>")
    assert uri.startswith("data:text/html;base64,")
    assert length == len("<h1>Hej</h1>")


def test_html_to_data_uri_kan_dekodes_tilbage_til_oprindelig_html():
    original = "<html><body>test</body></html>"
    uri, _ = html_to_data_uri(original)
    b64 = uri.split(",", 1)[1]
    decoded = base64.b64decode(b64).decode("utf-8")
    assert decoded == original


def test_html_to_data_uri_unicode_taeller_byte_laengde_ikke_tegn():
    """æøå er 2 bytes hver i UTF-8 — vi rapporterer byte-længde, ikke tegn."""
    uri, length = html_to_data_uri("æøå")
    assert length == 6  # 3 tegn × 2 bytes
    decoded = base64.b64decode(uri.split(",", 1)[1]).decode("utf-8")
    assert decoded == "æøå"


def test_html_to_data_uri_med_bytes_input_dobbelt_encoder_ikke():
    """Hvis bytes leveres direkte, antages den allerede UTF-8 — ikke encod igen."""
    raw_bytes = "æøå".encode("utf-8")
    uri, length = html_to_data_uri(raw_bytes)
    assert length == 6
    decoded = base64.b64decode(uri.split(",", 1)[1])
    assert decoded == raw_bytes


def test_html_to_data_uri_med_none_kaster_value_error():
    with pytest.raises(ValueError) as exc_info:
        html_to_data_uri(None)
    assert "mangler" in str(exc_info.value)


def test_html_to_data_uri_med_tom_streng_er_lovligt():
    """Tom HTML er ikke pænt, men skal ikke fejle — det er klientens valg."""
    uri, length = html_to_data_uri("")
    assert length == 0
    assert uri.startswith("data:text/html;base64,")


# ---------- integration: image → HTML → data URI ----------

def test_round_trip_image_til_data_uri(tiny_png_path):
    """End-to-end: billed-sti → HTML-wrapper → data-URI → dekodet HTML →
    base64-billede → dekodet PNG-bytes — skal matche originalen."""
    html = image_path_to_html(tiny_png_path)
    uri, html_byte_length = html_to_data_uri(html)

    # 1. URI har korrekt prefix
    assert uri.startswith("data:text/html;base64,")

    # 2. Dekod HTML ud af URI
    decoded_html = base64.b64decode(uri.split(",", 1)[1]).decode("utf-8")
    assert decoded_html == html
    assert html_byte_length == len(html.encode("utf-8"))

    # 3. Dekod billed-base64 ud af HTML, verificér det er den oprindelige PNG
    img_match = re.search(r'data:image/png;base64,([A-Za-z0-9+/=]+)"', decoded_html)
    assert img_match is not None
    assert base64.b64decode(img_match.group(1)) == _TINY_PNG

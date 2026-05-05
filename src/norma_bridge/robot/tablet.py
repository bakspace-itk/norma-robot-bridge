# -*- coding: utf-8 -*-
"""HTML- og data-URI-helpers til ALTabletService.showWebview().

Peppers tablet kan ikke loade en lokal fil direkte; HTML og billeder skal
sendes som en ``data:text/html;base64`` URI. Denne fil samler den konvertering
der i den oprindelige monolit blev duplikeret tre steder:

- intro-flow (``_legacy.py:_startup_intro``, linjer 127-141)
- ``show_tablet_image`` (linjer 195-210)
- ``show_tablet_html`` (linjer 212-226)

Helperne er rene funktioner uden NAOqi-afhaengighed - de kan testes uden robot.
"""

from __future__ import print_function, unicode_literals

import base64
import os


# HTML-skabelon der centreret viser et billede tilpasset Peppers tablet.
# Viewport-skaleringen og 200%-max stoerrelser matcher den oprindelige intro-skabelon
# fra legacy-monolitten - de er empirisk afstemt med tabletens rendering-quirks.
# Bemaerk: ``%%`` escaper et bogstaveligt ``%`` ved %-formatering nedenfor.
# CSS-vaerdierne ``200%`` skal stadig vaere ``200%`` i den faerdige HTML.
_IMAGE_HTML_TEMPLATE = (
    "<html><head>"
    "<meta name=\"viewport\" content=\"width=device-width, initial-scale=2.0\"/>"
    "<style>body{margin:0;padding:0;height:100vh;display:flex;"
    "justify-content:center;align-items:center;background:#fff;}"
    "img{max-width:200%%;max-height:200%%;}</style>"
    "</head><body><img src=\"data:image/png;base64,%s\"/></body></html>"
)


def _b64_to_text(data):
    """base64.b64encode returnerer bytes i Py3, str i Py2. Returner altid en
    text-streng saa den kan formattes ind i en unicode-skabelon."""
    encoded = base64.b64encode(data)
    if isinstance(encoded, bytes):
        return encoded.decode("ascii")
    return encoded


def image_path_to_html(image_path):
    """Laes et billede fra disken og returner en HTML-streng der embedder det
    som base64 inline-img.

    Argumenter:
        image_path: sti til en PNG/JPG. Skal eksistere paa bridge-maskinen.

    Returnerer:
        unicode/str med komplet HTML-dokument.

    Hejser:
        IOError hvis ``image_path`` er tomt eller filen ikke findes.
    """
    if not image_path or not os.path.exists(image_path):
        raise IOError("Billedfil ikke fundet: %s" % (image_path,))
    with open(image_path, "rb") as f:
        data = f.read()
    return _IMAGE_HTML_TEMPLATE % _b64_to_text(data)


def html_to_data_uri(html):
    """Konverter en HTML-streng til en ``data:text/html;base64``-URI.

    Argumenter:
        html: HTML som unicode/str eller bytes. Hvis bytes antages den allerede
              at vaere UTF-8 encoded.

    Returnerer:
        (uri, byte_length) hvor uri er strengen klar til
        ``ALTabletService.showWebview(uri)`` og byte_length er antal UTF-8-bytes
        i den oprindelige HTML (anvendes til logging/response).

    Hejser:
        ValueError hvis ``html`` er None.
    """
    if html is None:
        raise ValueError("html mangler")
    if isinstance(html, bytes):
        html_bytes = html
    else:
        html_bytes = html.encode("utf-8")
    return "data:text/html;base64," + _b64_to_text(html_bytes), len(html_bytes)

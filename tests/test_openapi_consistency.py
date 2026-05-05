# -*- coding: utf-8 -*-
"""Tests der holder ``api-spec/openapi.yaml`` og koden synkrone.

Dette er IKKE en formel OpenAPI-validator (den ville kraeve et schema-validate
bibliotek). Det er en pragmatisk drift-detektor: hvis nogen tilfoejer en ny
kommando i ``commands.py`` men glemmer at opdatere ``openapi.yaml`` (eller
omvendt), faar de en rod test.

Specifikt verificerer vi:

- Spec'ens diskriminator-mapping indeholder praecis de samme kommandoer som
  ``CommandRegistry`` har registreret.
- Hvert request-schema har et ``command``-felt med en enum der matcher dets
  navn i mappingen.
- Spec'ens ``oneOf`` for response-data refererer til praecis 7 schemas (én
  pr. kommando).
"""

from __future__ import print_function, unicode_literals

import os

import pytest

# yaml er en runtime-dep for testene. PyYAML virker paa baade Py 2.7 og 3.
yaml = pytest.importorskip("yaml")

# Tving registrering af alle kommandoer
import norma_bridge.api.commands  # noqa: F401
from norma_bridge.api.dispatcher import registry


SPEC_PATH = os.path.join(
    os.path.dirname(__file__), "..", "api-spec", "openapi.yaml"
)


@pytest.fixture(scope="module")
def spec():
    with open(SPEC_PATH) as f:
        return yaml.safe_load(f)


# -------- grundlaeggende struktur --------

def test_spec_har_korrekt_openapi_version(spec):
    assert spec["openapi"].startswith("3.0")


def test_spec_har_to_paths(spec):
    """Bridge eksponerer praecis to paths: status og command."""
    assert set(spec["paths"].keys()) == {"/api/status", "/api/command"}


def test_status_path_har_kun_get(spec):
    assert set(spec["paths"]["/api/status"].keys()) == {"get"}


def test_command_path_har_kun_post(spec):
    assert set(spec["paths"]["/api/command"].keys()) == {"post"}


# -------- request-discriminator matcher koden --------

def test_discriminator_mapping_matcher_registry(spec):
    """Hver registreret kommando skal have et schema i discriminator-mappingen.

    Hvis dette test fejler, er enten ``commands.py`` eller ``openapi.yaml``
    blevet opdateret uden at den anden fulgte med.
    """
    spec_commands = set(
        spec["components"]["schemas"]["Command"]["discriminator"]["mapping"].keys()
    )
    code_commands = set(registry.names())
    assert spec_commands == code_commands, (
        "Diskriminator-mapping og registry er ikke synkrone.\n"
        "  i spec men ikke i kode: %s\n"
        "  i kode men ikke i spec: %s"
    ) % (spec_commands - code_commands, code_commands - spec_commands)


def test_hvert_request_schema_har_konsistent_command_enum(spec):
    """Schemaet for fx 'say' skal have command-enum: ['say']."""
    schemas = spec["components"]["schemas"]
    mapping = schemas["Command"]["discriminator"]["mapping"]
    for cmd_name, schema_ref in mapping.items():
        schema_key = schema_ref.rsplit("/", 1)[-1]
        assert schema_key in schemas, "Refererer til manglende schema: %s" % schema_key
        enum = schemas[schema_key]["properties"]["command"]["enum"]
        assert enum == [cmd_name], (
            "Schema %s har enum %s; forventede [%s]"
        ) % (schema_key, enum, cmd_name)


# -------- response-oneOf daekker alle kommandoer --------

def test_response_oneof_har_syv_referencer(spec):
    """Vi forventer praecis 7 response-data-schemas - én pr. kommando."""
    oneof = spec["components"]["schemas"]["CommandSuccessEnvelope"]["properties"]["data"]["oneOf"]
    assert len(oneof) == len(registry.names()), (
        "Antal response-schemas (%d) matcher ikke antal kommandoer (%d)"
    ) % (len(oneof), len(registry.names()))


def test_response_oneof_referencer_eksisterer(spec):
    """Alle ``$ref`` i response-oneOf peger paa eksisterende schemas."""
    schemas = spec["components"]["schemas"]
    oneof = schemas["CommandSuccessEnvelope"]["properties"]["data"]["oneOf"]
    for entry in oneof:
        ref = entry["$ref"]
        key = ref.rsplit("/", 1)[-1]
        assert key in schemas, "Daad reference: %s" % ref


# -------- envelope-skemaer matcher koden --------

def test_error_envelope_har_status_og_message(spec):
    """``ErrorEnvelope``-skemaet skal matche det handler.py producerer."""
    schema = spec["components"]["schemas"]["ErrorEnvelope"]
    assert schema["required"] == ["status", "message"]
    assert schema["properties"]["status"]["enum"] == ["error"]


def test_command_success_envelope_har_status_og_data(spec):
    schema = spec["components"]["schemas"]["CommandSuccessEnvelope"]
    assert "status" in schema["required"]
    assert "data" in schema["required"]
    assert schema["properties"]["status"]["enum"] == ["success"]


# -------- specifikke felter i response-data --------

def test_status_data_skema_matcher_get_status_kontrakt(spec):
    """``StatusData`` skal have praecis de tre felter ``get_status`` returnerer."""
    fields = set(spec["components"]["schemas"]["StatusData"]["required"])
    assert fields == {"ip", "port", "interaction_count"}


def test_say_response_skema_matcher_say_kontrakt(spec):
    fields = set(spec["components"]["schemas"]["SayResponseData"]["required"])
    assert fields == {"spoken_text", "gesture", "interaction_count"}

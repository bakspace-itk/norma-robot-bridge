# -*- coding: utf-8 -*-
"""Gesture-cycling-logik og default tag-liste.

Gesture-tags er korte navne der svarer til ``ALAnimationPlayer.runTag()`` -
ikke fulde animation-paths. Kan overstyres via config.
"""

from __future__ import print_function, unicode_literals


# Default gesture-tags. Disse er standard NAOqi-tags som typisk er
# tilgaengelige paa en fabriksny Pepper - kan overstyres via config.
DEFAULT_GESTURES = (
    "hello",
    "happy",
    "calm",
    "enthusiastic",
    "beseech",
    "cool",
    "bow",
    "body language",
    "exalted",
    "but",
)


def cycle_gesture(interaction_count, gestures=DEFAULT_GESTURES):
    """Vaelg en gesture-tag baseret paa interaktion-taelleren.

    Cycling-reglen er bevaret fra legacy:
    - Hver anden interaktion (``interaction_count`` lige) faar en gesture.
    - Ulige interaktioner faar None - dvs. ren tale uden bevaegelse.
    - Listen indekseres med ``interaction_count % len(gestures)`` saa den
      wrapper rundt.

    Argumenter:
        interaction_count: heltal >= 0. Typisk vaerdien af
            ``PepperRobotService._interaction_count`` efter inkrement.
        gestures: sekvens af tags. Default er ``DEFAULT_GESTURES``. Kan
            overrides via config naar bridge'ens config-loader er paa plads.

    Returnerer:
        En streng (gesture-tag) eller ``None``.
    """
    if not gestures:
        return None
    if interaction_count % 2 != 0:
        return None
    return gestures[interaction_count % len(gestures)]

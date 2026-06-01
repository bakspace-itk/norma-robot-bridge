# -*- coding: utf-8 -*-
# Python 2.7-kompatibel setup.py.
# Vi bruger setup.py (frem for kun pyproject.toml) fordi PEP 517/518 understoettes
# daarligt af Py 2.7 og NAOqi-miljoeet.
#
# Pakken er IKKE publiceret paa offentlig PyPI - NAOqi kan ikke deklareres som
# pip-dependency. Installeres typisk via:
#   pip install -e .                            # lokal udvikling
#   pip install git+https://.../pepper-robot-bridge.git@<ref>   # fra git

from setuptools import setup, find_packages


setup(
    name="pepper-robot-bridge",
    version="0.1.0",
    description="HTTP-bridge der eksponerer NAOqi (TTS, animationer, tablet) for Pepper/NAO over et JSON-API.",
    author="Aarhus Kommune",
    author_email="kriba@aarhus.dk",
    url="https://github.com/bakspace-itk/pepper-robot-bridge",
    license="MIT",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    include_package_data=True,
    python_requires=">=2.7,<3",
    install_requires=[
        # NAOqi SDK leveres ikke via pip - skal installeres separat paa robot-maskinen.
    ],
    extras_require={
        "test": [
            "pytest<5.0",  # sidste pytest-version med Py 2.7-stoette
            "mock<4.0",    # unittest.mock kom foerst i Py 3.3
            "PyYAML<6.0",  # bruges af tests/test_openapi_consistency.py
        ],
    },
    entry_points={
        "console_scripts": [
            "pepper-bridge = pepper_bridge.main:main",
        ],
    },
)

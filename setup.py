# -*- coding: utf-8 -*-
# Python 2.7-kompatibel setup.py.
# Vi bruger setup.py i stedet for pyproject.toml fordi PEP 517/518 understoettes
# daarligt af Py 2.7 og NAOqi-miljoeet.

from setuptools import setup, find_packages

setup(
    name="norma-robot-bridge",
    version="0.1.0",
    description="HTTP-bridge der eksponerer NAOqi-funktionalitet for Norma (Pepper/NAO).",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=2.7,<3",
    install_requires=[
        # NAOqi SDK leveres ikke via pip - skal installeres separat paa robot-maskinen.
    ],
    extras_require={
        "test": [
            "pytest<5.0",  # sidste pytest-version med Py 2.7-stoette
        ],
    },
    entry_points={
        "console_scripts": [
            "norma-bridge = norma_bridge.main:main",
        ],
    },
)

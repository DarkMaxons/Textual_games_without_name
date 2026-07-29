"""Compatibilité avec l'ancien script de conversion d'image.

L'ancien projet importait ``generate_ascii_image`` depuis ``piece_salon.py``.
Cette version conserve cette fonction, mais utilise le moteur générique capable
d'afficher n'importe quelle pièce.
"""

from __future__ import annotations

from pathlib import Path

from ascii_renderer import render_image


def generate_ascii_image(
    image_path: str | Path,
    *,
    width: int = 96,
    color: bool | None = None,
    fallback_key: str | None = None,
) -> str:
    """Convertit puis affiche une image en ASCII et retourne la chaîne produite."""

    ascii_image = render_image(
        image_path,
        width=width,
        color=color,
        fallback_key=fallback_key,
    )
    print(ascii_image)
    return ascii_image


if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    generate_ascii_image(root / "assets" / "rooms" / "salon.png", fallback_key="salon")

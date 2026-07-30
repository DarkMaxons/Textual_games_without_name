"""Rendu d'images en art ASCII pour La Maison aux Secrets.

Le module est volontairement indépendant du moteur du jeu. Il peut donc être
réutilisé dans d'autres projets et continue de fonctionner en mode texte si
Pillow n'est pas installé ou si une image est absente.
"""

from __future__ import annotations

import os
import shutil
import sys
from functools import lru_cache
from pathlib import Path

try:
    from PIL import Image, ImageEnhance, ImageOps
except ImportError:  # Le jeu reste jouable sans Pillow.
    Image = None  # type: ignore[assignment]
    ImageEnhance = None  # type: ignore[assignment]
    ImageOps = None  # type: ignore[assignment]


# Du pixel le plus sombre au plus clair. Le fond noir d'un terminal fait que les
# caractères denses fonctionnent mieux pour les hautes lumières.
ASCII_CHARS = ".:;$&X+;"
RESET = "\033[0m"

# Petites vignettes utilisées lorsqu'une illustration manque. Elles évitent
# surtout d'afficher par erreur l'image du salon dans toutes les pièces.
FALLBACK_ART: dict[str, str] = {
    "salon": r"""
       .----------------------.
       |      III  XII  I      |
       |        .------.       |
       |       (  3:15  )      |
       |        '------'       |
       |       /  ____  \      |
       |      /__/____\__\     |
       |   ________________    |
       |  /___SOFA________/|   |
       '----------------------'
""",
    "cuisine": r"""
       .----------------------.
       | [] [] []       (___)  |
       |-----------      | |   |
       |   ________      |_|   |
       |  | TABLE  |   [###]   |
       |  |________|   FRIGO   |
       '----------------------'
""",
    "couloir": r"""
       .----------------------.
       |\                    /|
       | \      [TABLEAU]    / |
       |  \                /  |
       |   \____      ____/   |
       |        |    |        |
       '--------|____|--------'
""",
    "bibliotheque": r"""
       .----------------------.
       |IIIIIIIIIIIIIIIIIIIIII|
       |IIII  LIVRES  IIIIIIII|
       |IIIIIIIIIIIIIIIIII /| |
       |IIIIIIIIIIIIIIIII / | |
       |_____[VITRINE]___/____|
       '----------------------'
""",
    "salle_a_manger": r"""
       .----------------------.
       |       .-====-.        |
       |      /  ||||  \       |
       |  ___/___||||___\___   |
       | |__________________|  |
       |   o   o   o   o      |
       '----------------------'
""",
    "vestibule": r"""
       .----------------------.
       |       ________       |
       |      |  __  __|      |
       |      | |  ||  |      |
       |      | |  ||  |      |
       |  Y   | |__||__|  /\  |
       '------|________|------'
""",
    "palier": r"""
       .----------------------.
       | [PORTRAITS]  [PORTR.] |
       |                      |
       |  ____          ____  |
       | |    |   /\   |    | |
       | |____|  /__\  |____| |
       '----------------------'
""",
    "chambre_maitre": r"""
       .----------------------.
       |   ____        |\  /|  |
       |  /___/|       | \/ |  |
       | | LIT ||      | /\ |  |
       | |_____|/      |/__\|  |
       |       [CHEVET]       |
       '----------------------'
""",
    "chambre_enfant": r"""
       .----------------------.
       |   *       .--------.  |
       |  /|\      | MUSIQUE|  |
       | /_|_\     '--------'  |
       |  ________________     |
       | | COFFRE A JOUETS |   |
       '----------------------'
""",
    "salle_de_bain": r"""
       .----------------------.
       |       .--------.      |
       |       | MIROIR |      |
       |       '--------'      |
       |  __________________   |
       | /      BAIGNOIRE   \  |
       '----------------------'
""",
    "grenier": r"""
             /\
            /  \
           /____\
          / []   \
         / [MALLE]\
        /__[]__[]_\
""",
    "cave": r"""
       .----------------------.
       | (O) (O)      [RADIO]  |
       | (O) (O)       .--.    |
       |            ___|__|___ |
       | [PANNEAU]  | PORTE  | |
       '------------|_______|--'
""",
    "atelier": r"""
       .----------------------.
       |  o--o   /\/\   [PLAN] |
       |---+------------------|
       |  ETAU   TOURNEVIS     |
       |______________________|
       '----------------------'
""",
    "bureau_secret": r"""
       .----------------------.
       | [DOSSIERS]   ______   |
       |             |COFFRE|  |
       |  __________ |______|  |
       | |  BUREAU  |  (O)     |
       '----------------------'
""",
    "jardin": r"""
       .      *       .   *
          .      /\
       *        /  \      .
          _____/____\____
         /   TERRE      /\
        /______________/  \
""",
    "serre": r"""
          .-^^^^^^^^^^^^-.
        .' /| /| /| /|   '.
       /  @  Y  @  Y  @    \
      | ROSE IRIS LYS PAVOT |
       \____________________/
""",
    "chapelle": r"""
       .----------------------.
       |        /\  /\         |
       |       /__\/__\        |
       |         ||           |
       |     ____||____       |
       |    |   AUTEL  |      |
       '----------------------'
""",
    "crypte": r"""
       .----------------------.
       |  ___          ___     |
       | /___\  .----. /___\    |
       | |   |  |MACH| |   |    |
       | |___|  '----' |___|    |
       |_______[SOCLE]__________|
       '------------------------'
""",
}


def terminal_width(default: int = 92) -> int:
    """Retourne une largeur d'affichage raisonnable pour le terminal."""

    columns = shutil.get_terminal_size((default, 30)).columns
    return max(42, min(112, columns - 2))


def color_supported() -> bool:
    """Détecte sommairement si les séquences ANSI sont appropriées."""

    if os.environ.get("NO_COLOR") is not None:
        return False
    if not getattr(sys.stdout, "isatty", lambda: False)():
        return False
    term = os.environ.get("TERM", "")
    return term.lower() != "dumb"


def _shade_code(value: int) -> str:
    # 232 à 255 correspondent à la rampe de gris ANSI 256 couleurs.
    shade = 232 + min(23, max(0, round(value / 255 * 23)))
    return f"\033[38;5;{shade}m"


@lru_cache(maxsize=128)
def _render_cached(path_string: str, width: int, color: bool) -> str:
    if Image is None:
        return "[Pillow n'est pas installé : illustration ASCII désactivée]"

    image_path = Path(path_string)
    if not image_path.exists():
        return ""

    with Image.open(image_path) as source:
        image = ImageOps.exif_transpose(source).convert("L")
        image = ImageOps.autocontrast(image, cutoff=1)
        image = ImageEnhance.Contrast(image).enhance(1.18)

        original_width, original_height = image.size
        ratio = original_height / max(1, original_width)
        # Un caractère de terminal est environ deux fois plus haut que large.
        height = max(8, int(ratio * width * 0.47))
        image = image.resize((width, height), Image.Resampling.LANCZOS)

        pixels = list(image.getdata())

    lines: list[str] = []
    for row_start in range(0, len(pixels), width):
        row = pixels[row_start : row_start + width]
        if not color:
            chars = [ASCII_CHARS[min(len(ASCII_CHARS) - 1, p * len(ASCII_CHARS) // 256)] for p in row]
            lines.append("".join(chars).rstrip())
            continue

        # On ne répète la séquence ANSI que lorsque la nuance change.
        fragments: list[str] = []
        previous_shade = -1
        for value in row:
            shade = 232 + min(23, max(0, round(value / 255 * 23)))
            if shade != previous_shade:
                fragments.append(f"\033[38;5;{shade}m")
                previous_shade = shade
            fragments.append(ASCII_CHARS[min(len(ASCII_CHARS) - 1, value * len(ASCII_CHARS) // 256)])
        fragments.append(RESET)
        lines.append("".join(fragments).rstrip())

    return "\n".join(lines).rstrip()


def render_image(
    image_path: str | Path,
    *,
    width: int | None = None,
    color: bool | None = None,
    fallback_key: str | None = None,
) -> str:
    """Convertit une image en chaîne ASCII.

    Args:
        image_path: chemin du PNG/JPEG à convertir.
        width: largeur en caractères. La largeur du terminal est utilisée sinon.
        color: active la rampe de gris ANSI. Détection automatique si ``None``.
        fallback_key: identifiant d'une vignette textuelle de secours.
    """

    requested_width = width or terminal_width()
    requested_width = max(36, min(120, int(requested_width)))
    use_color = color_supported() if color is None else bool(color)

    rendered = _render_cached(str(Path(image_path).resolve()), requested_width, use_color)
    if rendered:
        return rendered

    fallback = FALLBACK_ART.get(fallback_key or "", "")
    return fallback.strip("\n") or "[Illustration indisponible]"


def clear_cache() -> None:
    """Vide le cache, utile après remplacement d'une image pendant le jeu."""

    _render_cached.cache_clear()

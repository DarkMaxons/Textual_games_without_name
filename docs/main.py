"""La Maison aux Secrets — aventure textuelle à énigmes.

Lancement :
    python main.py

Le moteur est volontairement contenu dans un seul fichier pour rester facile à
modifier. Le rendu ASCII se trouve dans ``ascii_renderer.py`` et les images dans
``assets/rooms``.
"""

from __future__ import annotations

import json
import random
import re
import sys
import shutil
import textwrap
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ascii_renderer import color_supported, render_image, terminal_width

# En Python classique, __file__ indique le chemin de main.py.
# Dans PyScript, __file__ peut ne pas exister.
if "__file__" in globals():
    ROOT = Path(__file__).resolve().parent
else:
    ROOT = Path.cwd()

ROOM_ASSETS = ROOT / "assets" / "rooms"
DEFAULT_SAVE = ROOT / "sauvegarde_maison.json"
# Sert à ignorer les codes couleur ANSI lors du calcul de la longueur
ANSI_CODES = re.compile(r"\033\[[0-9;]*m")


# ---------------------------------------------------------------------------
# Utilitaires de texte
# ---------------------------------------------------------------------------

def texte_centre(texte, largeur=None):
    texte = str(texte)

    if largeur is None:
        largeur = terminal_width()

    texte_visible = ANSI_CODES.sub("", texte)
    espaces = max(0, (largeur - len(texte_visible)) // 2)

    return (" " * espaces) + texte


def print_centre(texte=""):
    for ligne in str(texte).split("\n"):
        print(texte_centre(ligne))

def normaliser(texte: str) -> str:
    """Normalise une commande sans perdre les chiffres ni l'ordre des mots."""

    texte = unicodedata.normalize("NFD", texte.lower())
    texte = "".join(char for char in texte if unicodedata.category(char) != "Mn")
    texte = texte.replace("’", " ").replace("'", " ").replace("-", " ")
    texte = re.sub(r"[^a-z0-9\s]", " ", texte)
    return re.sub(r"\s+", " ", texte).strip()


ARTICLES = {
    "le",
    "la",
    "les",
    "un",
    "une",
    "des",
    "du",
    "de",
    "d",
    "l",
    "au",
    "aux",
    "a",
    "dans",
    "vers",
}


def nettoyer_cible(texte: str) -> str:
    mots = normaliser(texte).split()
    while mots and mots[0] in ARTICLES:
        mots.pop(0)
    return " ".join(mots)


def extraire_chiffres(texte: str) -> str:
    return "".join(re.findall(r"\d", texte))


def cadre(titre: str, largeur: int = 72) -> str:
    largeur = max(36, largeur)
    ligne = "═" * max(4, largeur - 2)
    titre_centre = f" {titre} "
    if len(titre_centre) < largeur - 2:
        debut = (largeur - 2 - len(titre_centre)) // 2
        fin = largeur - 2 - len(titre_centre) - debut
        milieu = "═" * debut + titre_centre + "═" * fin
    else:
        milieu = titre_centre[: largeur - 2]
    return f"╔{milieu}╗\n╚{ligne}╝"


class Couleur:
    ROUGE = "\033[91m"
    VERT = "\033[92m"
    JAUNE = "\033[93m"
    BLEU = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    GRAS = "\033[1m"
    FAIBLE = "\033[2m"
    RESET = "\033[0m"

COULEURS_PROMPT = {
    "vert": Couleur.VERT,
    "bleu": Couleur.BLEU,
    "violet": Couleur.MAGENTA,
    "magenta": Couleur.MAGENTA,
    "rouge": Couleur.ROUGE,
    "jaune": Couleur.JAUNE,
    "cyan": Couleur.CYAN,
    "blanc": "\033[97m",
    "gris": "\033[90m",
    }


# ---------------------------------------------------------------------------
# Modèle du monde
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class Objet:
    identifiant: str
    nom: str
    description: str
    alias: tuple[str, ...] = ()
    portable: bool = True

    def toutes_les_formes(self) -> set[str]:
        formes = {normaliser(self.identifiant), nettoyer_cible(self.nom)}
        formes.update(nettoyer_cible(alias) for alias in self.alias)
        return {forme for forme in formes if forme}


@dataclass(slots=True)
class Sortie:
    destination: str
    condition: str | None = None
    message_bloque: str = "Le passage est inaccessible."
    visible_si: str | None = None


@dataclass(slots=True)
class Piece:
    identifiant: str
    nom: str
    description: str
    image: str
    objets: list[str] = field(default_factory=list)
    sorties: dict[str, Sortie] = field(default_factory=dict)
    elements: tuple[str, ...] = ()
    alias: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Moteur de jeu
# ---------------------------------------------------------------------------


class Jeu:
    VERSION_SAUVEGARDE = 3

    def __init__(
        self,
        *,
        afficher_ascii: bool = True,
        evenements_aleatoires: bool = True,
        graine: int | None = None,
    ) -> None:
        self.rng = random.Random(graine)
        self.evenements_aleatoires = evenements_aleatoires
        self.couleurs = color_supported()
        self.ascii_active = afficher_ascii
        self.ascii_couleur = self.couleurs
        self.ascii_largeur = min(96, terminal_width())
        self.couleur_prompt = "vert"

        self.objets = self._creer_objets()
        self.pieces = self._creer_pieces()
        self.piece_actuelle = "salon"
        self.inventaire: list[str] = []
        self.drapeaux: dict[str, bool] = self._drapeaux_initiaux()
        self.indices_decouverts: list[str] = []
        self.preuves_enquete: list[str] = []
        self.visitees: set[str] = {self.piece_actuelle}
        self.niveaux_indices: dict[str, int] = {}
        self.succes: set[str] = set()
        self.tours = 0
        self.tension = 0
        self.termine = False
        self.fin: str | None = None
        self._sortie: list[str] = []

    # ----- Construction -------------------------------------------------

    @staticmethod
    def _drapeaux_initiaux() -> dict[str, bool]:
        return {
            "icebox_open": False,
            "matches_found": False,
            "clock_wound": False,
            "clock_open": False,
            "library_case_open": False,
            "dining_candles_lit": False,
            "painting_switch_found": False,
            "cellar_revealed": False,
            "flashlight_ready": False,
            "attic_trunk_open": False,
            "music_box_repaired": False,
            "toy_chest_open": False,
            "panel_open": False,
            "power_restored": False,
            "radio_code_known": False,
            "office_unlocked": False,
            "office_safe_open": False,
            "letter_decoded": False,
            "garden_unlocked": False,
            "buried_letter_found": False,
            "greenhouse_solved": False,
            "bathroom_steam": False,
            "bathroom_clue": False,
            "crypt_open": False,
            "medallion_inserted": False,
            "machine_unlocked": False,

            # Intrigue policière principale.
            "polaroid_enhanced": False,
            "journal_compared": False,
            "buried_letter_compared": False,
            "cylinder_played": False,
            "machine_silenced": False,
            "report_attempted": False,

            "game_complete": False,
        }

    @staticmethod
    def _creer_objets() -> dict[str, Objet]:
        objets = [
            Objet(
                "note_recette",
                "note de recette",
                "Une feuille tachée de graisse. Quatre quantités sont écrites en toutes lettres.",
                ("recette", "note", "feuille de recette"),
            ),
            Objet(
                "pile_seche",
                "pile sèche",
                "Une grosse pile ancienne de 4,5 V. Elle paraît encore chargée.",
                ("pile", "batterie", "pile ancienne"),
            ),
            Objet(
                "cle_remontage",
                "clé de remontage",
                "Une petite clé carrée prévue pour remonter un mécanisme d'horlogerie.",
                ("cle horloge", "cle de l horloge", "petite cle"),
            ),
            Objet(
                "allumettes",
                "boîte d'allumettes",
                "Une boîte humide, mais quelques allumettes sont encore utilisables.",
                ("allumettes", "boite allumettes"),
            ),
            Objet(
                "sceau_solaire",
                "sceau solaire",
                "Un disque de bronze gravé d'un soleil à douze branches.",
                ("sceau de bronze", "disque solaire", "premier sceau"),
            ),
            Objet(
                "cle_laiton",
                "clé en laiton",
                "Une clé fine portant l'emblème d'un livre ouvert.",
                ("cle bibliotheque", "cle de vitrine", "cle doree"),
            ),
            Objet(
                "lampe_torche",
                "lampe torche",
                "Une lourde lampe en métal. Son compartiment à pile est vide.",
                ("lampe", "torche", "lampe electrique"),
            ),
            Objet(
                "journal_valombre",
                "journal d'Éléonore",
                "Le journal intime d'Éléonore Valombre, couvrant les derniers mois de 1987.",
                ("journal", "journal intime", "carnet d eleonore"),
            ),
            Objet(
                "disque_chiffrement",
                "disque de chiffrement",
                "Deux alphabets concentriques en cuivre, mobiles l'un par rapport à l'autre.",
                ("disque", "roue de chiffrement", "cadran de chiffrement", "decodeur"),
            ),
            Objet(
                "fusible",
                "fusible en porcelaine",
                "Un fusible ancien, intact, prévu pour un tableau électrique à vis.",
                ("fusible", "fusible ancien"),
            ),
            Objet(
                "manivelle_musique",
                "manivelle de boîte à musique",
                "Une minuscule manivelle terminée par une poignée d'ivoire.",
                ("manivelle", "manivelle musique", "cle boite a musique"),
            ),
            Objet(
                "sceau_ivoire",
                "sceau d'ivoire",
                "Un disque pâle gravé d'un croissant de lune et d'une enfant endormie.",
                ("sceau blanc", "deuxieme sceau", "sceau enfant"),
            ),
            Objet(
                "tournevis",
                "tournevis plat",
                "Un tournevis solide, noirci par la graisse des machines.",
                ("tournevis", "outil"),
            ),
            Objet(
                "medaillon",
                "médaillon d'Éléonore",
                "Un médaillon d'argent contenant le portrait miniature d'une jeune fille.",
                ("medaillon", "pendentif", "medaillon argent"),
            ),
            Objet(
                "cle_jardin",
                "clé du jardin",
                "Une longue clé de fer dont la poignée dessine une feuille de lierre.",
                ("cle jardin", "cle porte fenetre", "cle en fer"),
            ),
            Objet(
                "lettre_chiffree",
                "lettre chiffrée",
                "Une lettre couverte de groupes de lettres incohérents. Une roue de chiffrement pourrait aider.",
                ("lettre", "lettre codee", "document chiffre"),
            ),
            Objet(
                "pelle",
                "pelle rouillée",
                "Une pelle de jardinier encore assez robuste pour creuser.",
                ("pelle", "pelle de jardin"),
            ),
            Objet(
                "lettre_enterree",
                "lettre enterrée",
                "Une lettre protégée par une toile cirée, écrite d'une main tremblante.",
                ("lettre enterree", "lettre de marguerite", "temoignage"),
            ),
            Objet(
                "sceau_lunaire",
                "sceau végétal",
                "Un disque de pierre verte où une vigne enlace une étoile.",
                ("sceau vert", "troisieme sceau", "sceau de pierre", "sceau vegetal"),
            ),
            Objet(
                "pieces_or",
                "rouleau de pièces anciennes",
                "Quelques pièces d'or frappées aux armes des Valombre. Un secret purement facultatif.",
                ("pieces", "or", "tresor du coffre"),
            ),
            Objet(
                "flacon_digitaline",
                "flacon de digitaline",
                "Un flacon pharmaceutique presque vide, muni d'une étiquette nominative.",
                ("digitaline", "flacon", "medicament", "poison"),
            ),
            Objet(
                "ampoule_chloral",
                "ampoule de chloral",
                "Une ampoule brisée contenant encore quelques gouttes d'un puissant sédatif.",
                ("ampoule", "chloral", "sedatif", "somnifere"),
            ),
            Objet(
                "registre_domestique",
                "registre domestique",
                "Le registre des dépenses et des médicaments, tenu par la gouvernante.",
                ("registre", "livre de comptes", "cahier de marguerite", "comptes"),
            ),
            Objet(
                "polaroid_flou",
                "photographie instantanée floue",
                "Une photographie carrée prise dans la chapelle. La scène est brouillée par un mouvement violent.",
                ("polaroid", "photo floue", "photographie floue", "photo instantanee"),
            ),
            Objet(
                "couteau_chirurgical",
                "couteau chirurgical",
                "Un couteau de trousse médicale portant les initiales D.V. sur le manche.",
                ("couteau", "scalpel", "lame", "couteau de damien"),
            ),
            Objet(
                "lettre_mathilde",
                "lettre inachevée de Mathilde",
                "Une lettre jamais envoyée, froissée puis dissimulée dans la coiffeuse.",
                ("lettre de mathilde", "lettre inachevee", "brouillon de mathilde"),
            ),
            Objet(
                "fragment_tissu_vert",
                "fragment de tissu vert",
                "Un lambeau de laine verte accroché à un câble arraché.",
                ("tissu", "lambeau", "laine verte", "fragment vert"),
            ),
            Objet(
                "cylindre_urgence",
                "cylindre d'enregistrement d'urgence",
                "Un cylindre de cire daté du 15 octobre 1987, 3 h 10.",
                ("cylindre", "enregistrement", "cylindre urgence", "cire"),
            ),
        ]
        return {objet.identifiant: objet for objet in objets}

    @staticmethod
    def _creer_pieces() -> dict[str, Piece]:
        def img(nom: str) -> str:
            return str(ROOM_ASSETS / f"{nom}.png")

        pieces = {
            "salon": Piece(
                "salon",
                "Salon de l'horloge",
                "Le salon est une vaste pièce noyée dans l'odeur de cire froide. Un sofa de cuir fait face à une cheminée de marbre. Au-dessus, une horloge monumentale est arrêtée à 3 h 15. Une photographie de famille penche dans son cadre.",
                img("salon"),
                elements=("horloge", "cheminée", "sofa", "photographie de famille"),
                alias=("salon", "salon de l horloge"),
            ),
            "cuisine": Piece(
                "cuisine",
                "Cuisine",
                "La cuisine sent le métal humide et les herbes fanées. Une glacière électrique cadenassée occupe un angle. Une note est maintenue sur sa porte par un aimant en forme de rose.",
                img("cuisine"),
                objets=["note_recette"],
                elements=("glacière", "placards", "évier", "table"),
                alias=("cuisine",),
            ),
            "salle_a_manger": Piece(
                "salle_a_manger",
                "Salle à manger",
                "Une table interminable est dressée pour cinq personnes, mais le repas est resté intact. Cinq verres portent encore un dépôt séché. Des bougies noircies pendent au chandelier. Les portes-fenêtres du jardin sont fermées par une serrure de fer.",
                img("salle_a_manger"),
                elements=("table", "cinq verres", "serviettes", "bougies", "chandelier", "portes-fenêtres"),
                alias=("salle a manger", "salle", "salle a diner"),
            ),
            "vestibule": Piece(
                "vestibule",
                "Vestibule",
                "Le vestibule donne sur la porte d'entrée, que le vent plaque contre son chambranle. Des manteaux mangés par les mites pendent encore à une patère. Votre mallette d'enquête et le formulaire de rapport final reposent sur une console.",
                img("vestibule"),
                elements=("porte d'entrée", "patère", "porte-parapluies", "manteaux", "mallette d'enquête", "rapport final"),
                alias=("vestibule", "entree", "hall d entree"),
            ),
            "couloir": Piece(
                "couloir",
                "Grand couloir",
                "Le couloir traverse l'aile orientale. Un tableau représentant un homme sans visage domine la cage d'escalier. Le papier peint se décolle autour du cadre, comme si quelqu'un l'avait souvent déplacé.",
                img("couloir"),
                elements=("tableau", "escalier", "mur", "porte de la chapelle"),
                alias=("couloir", "grand couloir"),
            ),
            "bibliotheque": Piece(
                "bibliotheque",
                "Bibliothèque",
                "Des milliers de livres recouvrent les murs jusqu'au plafond. Une vitrine verrouillée protège un journal, un registre domestique et un étrange disque de cuivre. Un globe terrestre est figé sur l'Europe.",
                img("bibliotheque"),
                elements=("vitrine", "livres", "globe", "échelle"),
                alias=("bibliotheque",),
            ),
            "chapelle": Piece(
                "chapelle",
                "Chapelle privée",
                "La chapelle familiale est intacte malgré l'humidité. L'autel porte trois cavités circulaires, chacune d'une matière différente. Une dalle funéraire occupe le sol devant lui.",
                img("chapelle"),
                elements=("autel", "trois cavités", "vitrail", "dalle funéraire"),
                alias=("chapelle", "chapelle privee"),
            ),
            "palier": Piece(
                "palier",
                "Palier de l'étage",
                "Le palier dessert plusieurs chambres. Une suite de portraits retrace la famille Valombre. L'un d'eux, daté d'octobre 1987, a été lacéré au niveau du visage du père.",
                img("palier"),
                elements=("portraits", "rampe", "trappe du grenier", "portes"),
                alias=("palier", "etage", "palier de l etage"),
            ),
            "chambre_maitre": Piece(
                "chambre_maitre",
                "Chambre des maîtres",
                "Le lit à baldaquin est défait. Une lampe torche sans pile repose sur la table de chevet. La coiffeuse est couverte de lettres brûlées sur les bords ; un tiroir semble avoir été refermé à la hâte.",
                img("chambre_maitre"),
                objets=["lampe_torche"],
                elements=("lit", "coiffeuse", "armoire", "fenêtre"),
                alias=("chambre des maitres", "chambre maitre", "grande chambre"),
            ),
            "chambre_enfant": Piece(
                "chambre_enfant",
                "Chambre d'Éléonore",
                "Des étoiles peintes couvrent le plafond. Une boîte à musique sans manivelle attend sur une commode. Au pied du petit lit, un coffre à jouets est fermé par quatre molettes numérotées. Une odeur de produit photographique flotte encore dans la pièce.",
                img("chambre_enfant"),
                elements=("boîte à musique", "coffre à jouets", "dessins", "petit lit"),
                alias=("chambre enfant", "chambre d eleonore", "petite chambre"),
            ),
            "salle_de_bain": Piece(
                "salle_de_bain",
                "Salle de bain",
                "Une baignoire sur pieds occupe presque toute la pièce. Le grand miroir est piqué de taches noires. Le robinet gémit lorsque le vent secoue les tuyaux. L'armoire à pharmacie est entrouverte.",
                img("salle_de_bain"),
                elements=("miroir", "robinet", "baignoire", "armoire à pharmacie"),
                alias=("salle de bain", "sdb", "bain"),
            ),
            "grenier": Piece(
                "grenier",
                "Grenier",
                "Sous la charpente, des draps recouvrent des meubles difformes. Une malle cerclée de cuivre porte quatre chiffres mobiles. Des appareils d'enregistrement à cylindres sont empilés près d'un vieux phonographe.",
                img("grenier"),
                elements=("malle", "caisses", "phonographe", "cylindres", "cheval à bascule", "charpente"),
                alias=("grenier", "combles"),
            ),
            "cave": Piece(
                "cave",
                "Cave des machines",
                "La lumière de votre lampe découpe des voûtes ruisselantes. Un tableau électrique éventré alimente une vieille radio. À l'ouest, une porte blindée possède un clavier à quatre chiffres.",
                img("cave"),
                elements=("tableau électrique", "radio", "porte blindée", "tonneaux"),
                alias=("cave", "sous sol", "sous sol principal"),
            ),
            "atelier": Piece(
                "atelier",
                "Atelier mécanique",
                "Des engrenages, des bobines et des outils occupent chaque surface. Un plan technique montre une machine circulaire sous la chapelle. Un câble de mise à la terre a été tranché puis arraché. Un tournevis plat dépasse d'un étau.",
                img("atelier"),
                objets=["tournevis"],
                elements=("plan technique", "câble arraché", "établi", "étau", "engrenages"),
                alias=("atelier", "atelier mecanique"),
            ),
            "bureau_secret": Piece(
                "bureau_secret",
                "Bureau secret d'Auguste",
                "Le bureau est resté figé dans sa dernière nuit d'activité. Des notes parlent de mémoire, de deuil et d'une « chambre de résonance ». Un médaillon, une clé de jardin et une lettre chiffrée reposent près d'un petit coffre mural.",
                img("bureau_secret"),
                objets=["medaillon", "cle_jardin", "lettre_chiffree"],
                elements=("documents", "lettre chiffrée", "coffre mural", "bureau"),
                alias=("bureau", "bureau secret", "bureau d auguste"),
            ),
            "jardin": Piece(
                "jardin",
                "Jardin envahi",
                "La pluie a transformé les allées en boue. Une serre de verre se dresse à l'ouest. Près d'un vieux saule, la terre paraît avoir été remuée. Des traces de pas irrégulières se dirigent vers la serre, et une pelle rouillée est plantée dans le sol.",
                img("jardin"),
                objets=["pelle"],
                elements=("terre remuée", "traces de pas", "saule", "serre", "statue"),
                alias=("jardin", "exterieur"),
            ),
            "serre": Piece(
                "serre",
                "Serre aux quatre fleurs",
                "La serre abrite quatre jardinières encore vivantes malgré l'abandon : une rose, un iris, un lys et un pavot. Chaque pot peut coulisser sur un rail devant un socle de pierre verte.",
                img("serre"),
                elements=("rose", "iris", "lys", "pavot", "socle"),
                alias=("serre", "serre de verre"),
            ),
            "crypte": Piece(
                "crypte",
                "Crypte de résonance",
                "Sous la chapelle repose une machine annulaire reliée aux tombeaux par des fils de cuivre. Son centre comporte l'empreinte exacte d'un médaillon. Un cylindre de verre enferme une lueur semblable à un souffle.",
                img("crypte"),
                elements=("machine", "empreinte", "cylindre", "tombeaux", "trésor"),
                alias=("crypte", "chambre de resonance"),
            ),
        }

        # Rez-de-chaussée
        pieces["salon"].sorties = {
            "nord": Sortie("cuisine"),
            "est": Sortie("couloir"),
            "ouest": Sortie("salle_a_manger"),
            "sud": Sortie("vestibule"),
        }
        pieces["cuisine"].sorties = {"sud": Sortie("salon")}
        pieces["salle_a_manger"].sorties = {
            "est": Sortie("salon"),
            "sud": Sortie(
                "jardin",
                condition="garden_unlocked",
                message_bloque="Les portes-fenêtres sont verrouillées. Leur serrure réclame une longue clé de fer.",
            ),
        }
        pieces["vestibule"].sorties = {"nord": Sortie("salon")}
        pieces["couloir"].sorties = {
            "ouest": Sortie("salon"),
            "nord": Sortie("bibliotheque"),
            "est": Sortie("chapelle"),
            "haut": Sortie("palier"),
            "bas": Sortie(
                "cave",
                condition="flashlight_ready",
                visible_si="cellar_revealed",
                message_bloque="L'escalier descend dans une obscurité totale. Il vous faut une source de lumière fiable.",
            ),
        }
        pieces["bibliotheque"].sorties = {"sud": Sortie("couloir")}
        pieces["chapelle"].sorties = {
            "ouest": Sortie("couloir"),
            "sud": Sortie(
                "jardin",
                condition="garden_unlocked",
                message_bloque="La porte latérale vers le jardin est verrouillée de l'autre côté par la même serrure de lierre.",
            ),
            "bas": Sortie("crypte", visible_si="crypt_open"),
        }

        # Étage
        pieces["palier"].sorties = {
            "bas": Sortie("couloir"),
            "ouest": Sortie("chambre_maitre"),
            "est": Sortie("chambre_enfant"),
            "nord": Sortie("salle_de_bain"),
            "haut": Sortie("grenier"),
        }
        pieces["chambre_maitre"].sorties = {"est": Sortie("palier")}
        pieces["chambre_enfant"].sorties = {"ouest": Sortie("palier")}
        pieces["salle_de_bain"].sorties = {"sud": Sortie("palier")}
        pieces["grenier"].sorties = {"bas": Sortie("palier")}

        # Sous-sol et extérieur
        pieces["cave"].sorties = {
            "haut": Sortie("couloir"),
            "est": Sortie("atelier"),
            "ouest": Sortie("bureau_secret", visible_si="office_unlocked"),
        }
        pieces["atelier"].sorties = {"ouest": Sortie("cave")}
        pieces["bureau_secret"].sorties = {"est": Sortie("cave")}
        pieces["jardin"].sorties = {
            "nord": Sortie("salle_a_manger"),
            "ouest": Sortie("serre"),
            "est": Sortie("chapelle"),
        }
        pieces["serre"].sorties = {"est": Sortie("jardin")}
        pieces["crypte"].sorties = {"haut": Sortie("chapelle")}
        return pieces

    # ----- Affichage ----------------------------------------------------

    def _couleur(self, texte: str, code: str) -> str:
        return f"{code}{texte}{Couleur.RESET}" if self.couleurs else texte

    def dire(self, texte: str = "") -> None:
        self._sortie.append(texte)

    def rapport_affaire(self) -> str:
        return """
    RAPPORT DE GENDARMERIE — DOSSIER 87-10-15
    Disparition de la famille Valombre
    Domaine de Valombre — nuit du 15 au 16 octobre 1987
    Réouverture de l'enquête : 22 octobre 1991

    PERSONNES DISPARUES ET SIGNALEMENTS

    • Auguste Valombre, 48 ans
      Propriétaire du domaine et ingénieur en acoustique. Environ 1,83 m, cheveux
      blond cendré, droitier. Il travaillait depuis deux ans sur des appareils
      capables, selon lui, de « conserver une mémoire humaine ».

    • Mathilde Valombre, 44 ans
      Épouse d'Auguste. Environ 1,70 m, cheveux bruns, gauchère. Elle administrait
      le domaine et avait annoncé le départ prochain de toute la famille.

    • Damien Valombre, 22 ans
      Fils aîné. Environ 1,89 m, grand, blond, droitier. Étudiant en médecine à
      Genève. Il possédait une trousse contenant un couteau chirurgical gravé D.V.
      Il était revenu au domaine le jour même de la disparition.

    • Éléonore Valombre, 11 ans
      Fille cadette. Petite, cheveux châtains. Malade depuis plusieurs mois :
      malaises, ralentissement du pouls, troubles visuels et épisodes de confusion.
      Aucun diagnostic définitif n'avait été établi.

    • Marguerite Bellac, 56 ans
      Gouvernante depuis près de vingt ans. Environ 1,58 m, cheveux gris, légère
      boiterie de la jambe gauche. Elle portait habituellement un uniforme de laine
      vert sombre et gérait le garde-manger ainsi que les médicaments d'Éléonore.

    CONSTATATIONS INITIALES

    • La porte principale était verrouillée de l'intérieur.
    • Aucune fenêtre ne présentait de trace d'effraction.
    • La table était dressée pour cinq personnes ; le repas n'avait presque pas été
      touché.
    • L'électricité avait été coupée à 2 h 40.
    • Toutes les horloges étaient arrêtées à 3 h 15.
    • Un billet de train pour Genève, au nom de Damien, était daté du 16 octobre.
    • Une voisine avait aperçu, à travers une fenêtre de la chapelle, une grande
      silhouette blonde tenant un objet brillant.
    • Deux témoins avaient entendu une voix d'enfant après la coupure de courant.
    • La dalle de la chapelle résista aux recherches.
    • Aucun corps ne fut retrouvé.
    • Marguerite Bellac ne reparut jamais et ne fut jamais formellement interrogée.

    L'enquête fut classée en 1988. Elle est aujourd'hui rouverte après la réception
    anonyme d'une clé du domaine et d'une note : « La scène raconte encore tout. »

    MISSION

    Explorez la maison, consignez les preuves, distinguez les faits des fausses
    pistes et reconstituez la chronologie exacte. Votre rapport final ne pourra être
    déposé qu'une seule fois. Une accusation erronée entraînera la clôture
    définitive du dossier.
    """.strip()

    def introduction(self) -> str:
        titre = self._couleur(
            "LA MAISON AUX SECRETS",
            Couleur.VERT + Couleur.GRAS,
        )

        return f"""
    {cadre(titre, min(self.ascii_largeur, 82))}

    22 octobre 1991.

    Quatre ans après la disparition des Valombre, la gendarmerie vous confie la
    réouverture du dossier. Une clé anonyme permet enfin d'entrer dans le domaine,
    resté sous scellés. Votre mission n'est pas de confirmer la première théorie :
    elle est de construire une version des faits capable de résister à un tribunal.

    Vous devrez retrouver des objets, résoudre les mécanismes de la maison, comparer
    les écritures, vérifier les alibis et séparer les preuves des mises en scène.

    {self.rapport_affaire()}

    Commandes utiles :
      aide       commandes générales
      suspects   signalements des cinq disparus
      preuves    pièces à conviction déjà établies
      rapport    dossier de 1987
      rapport final
                  état du dossier avant votre unique conclusion
      conclure [votre phrase]
                  dépose votre version définitive des faits

    Vous ne disposerez que d'une seule tentative pour le rapport final.
    """.strip()

    def decrire_piece(self) -> str:
        piece = self.pieces[self.piece_actuelle]
        lignes: list[str] = [""]
        lignes.append(self._couleur(f"══ {piece.nom} ══", Couleur.CYAN + Couleur.GRAS))

        if self.ascii_active:
            lignes.append(
                render_image(
                    piece.image,
                    width=self.ascii_largeur,
                    color=self.ascii_couleur,
                    fallback_key=piece.identifiant,
                )
            )

        lignes.append(textwrap.fill(piece.description, width=min(100, self.ascii_largeur)))
        lignes.extend(self._description_etat(piece.identifiant))

        objets_visibles = [self.objets[obj].nom for obj in piece.objets]
        if objets_visibles:
            lignes.append(self._couleur("Objets visibles : ", Couleur.JAUNE) + ", ".join(objets_visibles) + ".")

        if piece.elements:
            lignes.append(self._couleur("Vous remarquez : ", Couleur.BLEU) + ", ".join(piece.elements) + ".")

        sorties = []
        for direction, sortie in piece.sorties.items():
            if sortie.visible_si and not self.drapeaux.get(sortie.visible_si, False):
                continue
            destination = self.pieces[sortie.destination].nom
            verrou = " (bloqué)" if sortie.condition and not self.drapeaux.get(sortie.condition, False) else ""
            sorties.append(f"{direction} → {destination}{verrou}")
        if sorties:
            lignes.append(self._couleur("Passages : ", Couleur.VERT) + " | ".join(sorties))

        return "\n".join(lignes)

    def _description_etat(self, room: str) -> list[str]:
        lignes: list[str] = []
        f = self.drapeaux
        if room == "salon":
            if f["clock_wound"] and not f["clock_open"]:
                lignes.append("Le mécanisme de l'horloge tourne de nouveau, mais ses aiguilles attendent d'être placées.")
            if f["clock_open"]:
                lignes.append("Un compartiment est ouvert dans le socle de l'horloge.")
        elif room == "cuisine" and f["icebox_open"]:
            lignes.append("Le cadenas de la glacière pend, ouvert, contre la porte.")
        elif room == "salle_a_manger":
            if f["dining_candles_lit"]:
                lignes.append("Les bougies révèlent les dépôts des verres et l'éclat d'une ampoule brisée.")
            if f["garden_unlocked"]:
                lignes.append("Les portes-fenêtres sont maintenant déverrouillées.")
        elif room == "vestibule" and f["machine_silenced"]:
            lignes.append("La porte d'entrée est libre. Votre rapport final attend dans la mallette.")
        elif room == "couloir" and f["cellar_revealed"]:
            lignes.append("Une portion du mur a pivoté, révélant un escalier vers la cave.")
        elif room == "bibliotheque" and f["library_case_open"]:
            lignes.append("La vitrine est ouverte ; le journal, le registre et le disque peuvent être pris.")
        elif room == "chambre_enfant":
            if f["music_box_repaired"]:
                lignes.append("La boîte à musique possède maintenant sa manivelle.")
            if f["toy_chest_open"]:
                lignes.append("Le coffre à jouets est ouvert ; une enveloppe photographique en dépassait.")
        elif room == "grenier":
            if f["attic_trunk_open"]:
                lignes.append("La grande malle est ouverte.")
            if f["cylinder_played"]:
                lignes.append("Le phonographe porte encore le cylindre de 3 h 10.")
        elif room == "cave":
            if f["panel_open"]:
                lignes.append("Le capot du tableau électrique a été retiré.")
            if f["power_restored"]:
                lignes.append("Une faible tension bourdonne dans les câbles ; la radio est alimentée.")
            if f["office_unlocked"]:
                lignes.append("La porte blindée de l'ouest est ouverte.")
        elif room == "atelier" and "sabotage_cable" in self.preuves_enquete:
            lignes.append("Le câble saboté et les fibres vertes sont désormais photographiés et consignés.")
        elif room == "bureau_secret" and f["letter_decoded"]:
            lignes.append("La lettre chiffrée porte désormais vos annotations de décodage.")
        elif room == "jardin":
            if f["buried_letter_found"]:
                lignes.append("Un trou sombre s'ouvre près du saule.")
            if "fuite_jardin" in self.preuves_enquete:
                lignes.append("Les empreintes irrégulières vers la serre sont balisées comme preuve.")
        elif room == "serre" and f["greenhouse_solved"]:
            lignes.append("Les jardinières sont alignées ; le socle de pierre est ouvert.")
        elif room == "chapelle" and f["crypt_open"]:
            lignes.append("La dalle funéraire a glissé, découvrant un escalier sous l'autel.")
        elif room == "crypte":
            if f["medallion_inserted"]:
                lignes.append("Le médaillon est enchâssé au centre de la machine.")
            if f["machine_unlocked"] and not f["machine_silenced"]:
                lignes.append("La machine peut restituer son dernier écho avant votre décision.")
            if f["machine_silenced"]:
                lignes.append("La machine est neutralisée ; le dossier peut maintenant être déposé.")
        return lignes

    def aide(self) -> str:
        return """
    Commandes principales
    ---------------------
      aller nord / sud / est / ouest / haut / bas
      aller cuisine                         le nom d'une pièce voisine fonctionne
      regarder                              réaffiche la pièce
      inspecter horloge                     examine le décor ou un objet
      prendre lampe                         ramasse un objet
      lire journal                          lit un document accessible
      utiliser pile sur lampe               emploie un objet sur une cible
      combiner pile avec lampe              variante pour deux objets
      comparer journal avec registre        confronte deux pièces à conviction
      ouvrir placards / allumer radio / écouter radio
      entrer code 7412                      saisit un code dans le mécanisme local
      régler horloge 3h15                   règle un mécanisme
      ordonner fleurs rose iris lys pavot   résout une énigme d'ordre
      placer sceaux sur autel               pose plusieurs objets

    Enquête
    -------
      suspects                              relit les signalements
      preuves                               affiche les preuves établies
      journal                               affiche les indices et déductions
      rapport                               relit le rapport initial
      rapport final                         vérifie si le dossier est prêt
      conclure [une phrase complète]        dépose l'unique conclusion définitive

    Confort
    -------
      inventaire | objectifs | indice | carte | succès
      sauvegarder [fichier] | charger [fichier]
      ascii on/off | ascii couleur/mono | largeur 80
      quitter

    Le parseur ignore les accents et accepte beaucoup de synonymes. Les énigmes ne
    nécessitent aucune connaissance extérieure. Une impression n'est pas une
    preuve : inspectez, utilisez la lampe et comparez les documents.
    """.strip()

    # ----- Résolution d'objets ------------------------------------------

    def _objet_correspondant(self, texte: str, candidats: list[str]) -> str | None:
        cible = nettoyer_cible(texte)
        if not cible:
            return None
        correspondances: list[tuple[int, str]] = []
        for identifiant in candidats:
            objet = self.objets[identifiant]
            for forme in objet.toutes_les_formes():
                if cible == forme or cible.endswith(forme) or forme in cible:
                    correspondances.append((len(forme), identifiant))
        if not correspondances:
            return None
        correspondances.sort(reverse=True)
        return correspondances[0][1]

    def _objet_inventaire(self, texte: str) -> str | None:
        return self._objet_correspondant(texte, self.inventaire)

    def _objet_piece(self, texte: str) -> str | None:
        return self._objet_correspondant(texte, self.pieces[self.piece_actuelle].objets)

    def _objet_accessible(self, texte: str) -> str | None:
        return self._objet_correspondant(
            texte,
            self.pieces[self.piece_actuelle].objets + self.inventaire,
        )

    def _possede(self, identifiant: str) -> bool:
        return identifiant in self.inventaire

    def _ajouter_dans_piece(self, room: str, *identifiants: str) -> None:
        for identifiant in identifiants:
            if identifiant not in self.pieces[room].objets and identifiant not in self.inventaire:
                self.pieces[room].objets.append(identifiant)

    def _retirer_inventaire(self, identifiant: str) -> None:
        if identifiant in self.inventaire:
            self.inventaire.remove(identifiant)

    def _decouvrir(self, cle: str, texte: str) -> None:
        if cle not in self.indices_decouverts:
            self.indices_decouverts.append(cle)
            self.dire(self._couleur("Indice ajouté au journal : ", Couleur.MAGENTA) + texte)

    def _succes(self, nom: str) -> None:
        if nom not in self.succes:
            self.succes.add(nom)
            self.dire(self._couleur(f"Succès débloqué : {nom}", Couleur.JAUNE + Couleur.GRAS))

    def _ajouter_preuve(self, cle: str, resume: str) -> None:
        if cle not in self.preuves_enquete:
            self.preuves_enquete.append(cle)
            self.dire(
                self._couleur("PIÈCE À CONVICTION AJOUTÉE : ", Couleur.ROUGE + Couleur.GRAS)
                + resume
            )

    @staticmethod
    def _catalogue_preuves() -> dict[str, tuple[str, str]]:
        return {
            "profils_famille": (
                "Signalements familiaux",
                "Damien est le seul homme très grand et blond ; Marguerite est petite, boite de la jambe gauche et porte du vert.",
            ),
            "ticket_damien": (
                "Billet de Damien",
                "Damien devait repartir le 16 octobre, mais une note indique qu'il refusait de partir sans Éléonore.",
            ),
            "digitaline": (
                "Digitaline administrée à Éléonore",
                "Un flacon presque vide a été retiré par M. Bellac alors que les symptômes d'Éléonore correspondent à un surdosage.",
            ),
            "sedatif_repas": (
                "Repas drogué",
                "Une ampoule de chloral a été brisée près de la place de Marguerite ; quatre verres portent le même dépôt sédatif.",
            ),
            "registre_ecriture": (
                "Écriture de Marguerite",
                "Le registre domestique fournit un échantillon fiable de l'écriture de Marguerite Bellac.",
            ),
            "journal_falsifie": (
                "Dernière page falsifiée",
                "La page accusant « D. » dans le journal d'Éléonore a été ajoutée par Marguerite.",
            ),
            "polaroid_ambigu": (
                "Photographie ambiguë",
                "Une grande silhouette blonde tient le couteau de Damien dans la chapelle.",
            ),
            "polaroid_detail": (
                "Photographie réexaminée",
                "Damien ne frappe pas : il comprime la blessure de Mathilde tandis qu'une petite silhouette en vert s'éloigne.",
            ),
            "couteau_damien": (
                "Couteau chirurgical D.V.",
                "Le couteau appartient à Damien, mais le sang et les fibres montrent qu'il a été saisi avec un gant de laine verte.",
            ),
            "lettre_mathilde": (
                "Lettre de Mathilde",
                "Mathilde soupçonnait Marguerite de modifier les médicaments d'Éléonore et voulait la renvoyer.",
            ),
            "sabotage_cable": (
                "Sabotage de la mise à la terre",
                "Le câble a été coupé volontairement ; un fragment de l'uniforme vert de Marguerite y est resté accroché.",
            ),
            "cylindre_dispute": (
                "Enregistrement de 3 h 10",
                "Mathilde accuse Marguerite d'avoir drogué le repas ; Damien lui ordonne de lâcher son couteau.",
            ),
            "fuite_jardin": (
                "Trace de fuite",
                "Des pas courts, avec un talon gauche irrégulier, vont de la chapelle vers la serre et la sortie du domaine.",
            ),
            "lettre_enterree": (
                "Lettre enterrée",
                "Une lettre attribue toute la faute à Auguste et prétend que Marguerite avait fui avant les violences.",
            ),
            "fausse_lettre": (
                "Faux témoignage de Marguerite",
                "La lettre enterrée est de la main de Marguerite et contient une information enregistrée après l'heure où elle dit avoir fui.",
            ),
            "echo_315": (
                "Écho de 3 h 15",
                "La machine restitue la scène : Marguerite poignarde Mathilde, Damien tente de la sauver, puis Auguste active la chambre.",
            ),
        }

    @staticmethod
    def _preuves_obligatoires() -> set[str]:
        return {
            "digitaline",
            "sedatif_repas",
            "journal_falsifie",
            "polaroid_detail",
            "couteau_damien",
            "lettre_mathilde",
            "sabotage_cable",
            "cylindre_dispute",
            "fuite_jardin",
            "echo_315",
        }

    def afficher_preuves(self) -> str:
        catalogue = self._catalogue_preuves()
        total = len(catalogue)
        if not self.preuves_enquete:
            return (
                "Aucune pièce à conviction formellement établie.\n"
                "Une description inquiétante ou une intuition ne suffit pas : inspectez les objets, "
                "éclairez les détails et comparez les écritures."
            )
        lignes = [
            f"PIÈCES À CONVICTION — {len(self.preuves_enquete)}/{total}",
            "----------------------------------------",
        ]
        for numero, cle in enumerate(self.preuves_enquete, 1):
            titre, detail = catalogue.get(cle, (cle, ""))
            lignes.append(f"{numero:02d}. {titre}")
            if detail:
                lignes.append(textwrap.fill(f"    {detail}", width=min(100, self.ascii_largeur)))
        return "\n".join(lignes)

    def afficher_suspects(self) -> str:
        return """
    SIGNALEMENTS — DOSSIER VALOMBRE

    AUGUSTE VALOMBRE
      48 ans, 1,83 m, blond cendré, droitier. Ingénieur. Obsession croissante pour
      sa machine et pour la survie d'Éléonore.

    MATHILDE VALOMBRE
      44 ans, 1,70 m, brune, gauchère. Préparait le départ de la famille et
      contestait les expériences de son mari.

    DAMIEN VALOMBRE
      22 ans, 1,89 m, blond, droitier. Étudiant en médecine. Propriétaire d'un
      couteau chirurgical gravé D.V. Revenu de Genève le 15 octobre.

    ÉLÉONORE VALOMBRE
      11 ans, châtain, malade depuis plusieurs mois. Ses symptômes étaient
      irréguliers et s'aggravaient surtout au domaine.

    MARGUERITE BELLAC
      56 ans, 1,58 m, cheveux gris, légère boiterie gauche. Gouvernante. Uniforme
      vert sombre. Responsable du garde-manger et des médicaments.
    """.strip()

    def _examiner_objet_enquete(self, objet_id: str) -> str | None:
        if objet_id == "flacon_digitaline":
            self._ajouter_preuve(
                "digitaline",
                "Le flacon de digitaline relie les malaises d'Éléonore aux retraits de Marguerite.",
            )
            return (
                "L'étiquette indique : « Digitaline — deux gouttes maximum — E. Valombre ».\n"
                "Au dos, la pharmacie a noté : « Retiré le 4 octobre par M. Bellac ».\n"
                "Le flacon est presque vide. Les symptômes du rapport — pouls lent, troubles "
                "visuels et confusion — sont compatibles avec des doses excessives."
            )
        if objet_id == "ampoule_chloral":
            self._ajouter_preuve(
                "sedatif_repas",
                "Le chloral et les dépôts des verres prouvent que le repas a été drogué.",
            )
            return (
                "L'ampoule porte la mention « hydrate de chloral — sédatif ». Un fil de laine "
                "vert sombre est collé au verre brisé. Quatre verres de la table présentent "
                "le même dépôt blanchâtre ; celui d'Éléonore n'en contient pas."
            )
        if objet_id == "registre_domestique":
            self._ajouter_preuve(
                "registre_ecriture",
                "Le registre fournit l'écriture de référence de Marguerite Bellac.",
            )
            return (
                "Marguerite a tenu ce registre pendant vingt ans. Les dernières lignes recensent "
                "des achats de digitaline, de chloral et de produits photographiques. Sa façon "
                "très particulière de former les D et les M permettra de comparer d'autres textes."
            )
        if objet_id == "polaroid_flou":
            if self.drapeaux["polaroid_enhanced"]:
                return (
                    "Sous la lumière rasante, la scène est nette : Damien, grand et blond, tient "
                    "son couteau mais s'en sert pour découper le corsage de Mathilde et comprimer "
                    "sa plaie. À l'arrière-plan, une petite silhouette en uniforme vert quitte "
                    "la chapelle en boitant."
                )
            self._ajouter_preuve(
                "polaroid_ambigu",
                "La photographie semble montrer Damien tenant un couteau au-dessus de Mathilde.",
            )
            return (
                "La photographie montre une grande silhouette blonde penchée sur Mathilde, un "
                "couteau brillant à la main. Tout désigne Damien, mais le flou empêche de savoir "
                "s'il frappe ou s'il tente de porter secours. Une lumière rasante pourrait faire "
                "apparaître les détails de l'émulsion."
            )
        if objet_id == "couteau_chirurgical":
            self._ajouter_preuve(
                "couteau_damien",
                "Le couteau appartient à Damien, mais des fibres vertes se trouvent sur le manche.",
            )
            return (
                "Les initiales D.V. confirment qu'il s'agit du couteau de Damien. La lame porte "
                "du sang séché. Sur le manche, coincées sous la garde, se trouvent des fibres de "
                "laine vert sombre et une trace de poudre de gant. Le propriétaire n'est pas "
                "nécessairement la personne qui l'a utilisé pour frapper."
            )
        if objet_id == "lettre_mathilde":
            self._ajouter_preuve(
                "lettre_mathilde",
                "Mathilde soupçonnait Marguerite d'empoisonner lentement Éléonore.",
            )
            return (
                "« Damien a raison : les crises d'Éléonore suivent les jours où Marguerite "
                "prépare seule ses gouttes. J'ai fait analyser un reste de médicament. Demain, "
                "je la renvoie et nous partons pour Genève. Je dois parler à Auguste avant qu'il "
                "ne mette encore la petite dans sa machine. — Mathilde »"
            )
        if objet_id == "fragment_tissu_vert":
            self._ajouter_preuve(
                "sabotage_cable",
                "Le tissu de l'uniforme de Marguerite est resté sur le câble saboté.",
            )
            return (
                "La laine correspond exactement à l'uniforme vert décrit dans le rapport. Le "
                "fragment est pris dans les torons du câble de mise à la terre, coupé à la pince "
                "puis arraché vers 2 h 40. Le sabotage a rendu la machine dangereusement instable."
            )
        if objet_id == "cylindre_urgence":
            return (
                "L'étiquette manuscrite indique : « Chapelle — ligne d'urgence — 15/10/1987 — "
                "3 h 10 ». Le cylindre doit être lu sur le phonographe du grenier."
            )
        if objet_id == "lettre_enterree":
            self._ajouter_preuve(
                "lettre_enterree",
                "La lettre enterrée accuse Auguste et prétend innocenter Marguerite.",
            )
            return (
                "La lettre affirme que Marguerite aurait quitté la maison à 2 h 50 et qu'Auguste "
                "aurait ensuite attaqué seul sa famille. Elle mentionne pourtant « le cri enregistré "
                "dans le cylindre de 3 h 10 ». Cette chronologie paraît impossible. Comparez son "
                "écriture à un document certain."
            )
        return None

    def comparer(self, reste: str) -> bool:
        match = re.match(r"(.+?)\s+(?:avec|et|a)\s+(.+)", normaliser(reste))
        if not match:
            self.dire("Exemple : comparer journal avec registre.")
            return False

        gauche_texte, droite_texte = match.group(1), match.group(2)
        candidats = self.pieces[self.piece_actuelle].objets + self.inventaire
        gauche = self._objet_correspondant(gauche_texte, candidats)
        droite = self._objet_correspondant(droite_texte, candidats)

        if not gauche or not droite:
            self.dire("Vous devez avoir les deux éléments à portée de main pour les comparer.")
            return False

        paire = {gauche, droite}
        if paire == {"journal_valombre", "registre_domestique"}:
            if self.drapeaux["journal_compared"]:
                self.dire("La comparaison est déjà consignée : la dernière page du journal est falsifiée.")
                return False
            self.drapeaux["journal_compared"] = True
            self._ajouter_preuve(
                "journal_falsifie",
                "La page qui accuse « D. » est de la main de Marguerite, pas d'Éléonore.",
            )
            self.dire(
                "Les pages authentiques d'Éléonore sont rondes et hésitantes. La dernière page, "
                "où l'on lit « D. me fait peur, ses sautes d'humeur empirent », reproduit les D "
                "anguleux et les M à longue boucle du registre de Marguerite. La page a été "
                "ajoutée pour orienter les soupçons vers Damien."
            )
            self._succes("Graphologue")
            return True

        if paire == {"lettre_enterree", "registre_domestique"}:
            if self.drapeaux["buried_letter_compared"]:
                self.dire("Vous avez déjà établi que la lettre enterrée est un faux témoignage de Marguerite.")
                return False
            self.drapeaux["buried_letter_compared"] = True
            self._ajouter_preuve(
                "fausse_lettre",
                "Marguerite a écrit et enterré son propre faux alibi après les faits.",
            )
            self.dire(
                "L'écriture correspond au registre : la lettre est bien de Marguerite. Plus grave, "
                "elle décrit un enregistrement daté de 3 h 10 alors qu'elle prétend avoir fui à "
                "2 h 50. Elle a rédigé ce faux témoignage après les violences."
            )
            self._succes("Le mensonge sous le saule")
            return True

        if paire == {"polaroid_flou", "couteau_chirurgical"}:
            self.dire(
                "La garde, la longueur de lame et les initiales visibles correspondent : le couteau "
                "de la photographie est bien celui de Damien. Cela prouve l'identité de l'objet, "
                "pas celle de la personne qui a porté le coup."
            )
            return True

        self.dire("Cette comparaison ne fait apparaître aucun lien probant.")
        return False

    def afficher_rapport_final(self) -> str:
        obligatoires = self._preuves_obligatoires()
        trouvees = obligatoires.intersection(self.preuves_enquete)
        manquantes = obligatoires.difference(self.preuves_enquete)
        machine = self.drapeaux["machine_silenced"]

        lignes = [
            "RAPPORT FINAL — CONTRÔLE AVANT DÉPÔT",
            "-----------------------------------",
            f"Preuves structurantes : {len(trouvees)}/{len(obligatoires)}",
            f"Machine neutralisée : {'oui' if machine else 'non'}",
            f"Lieu de dépôt : {'vestibule atteint' if self.piece_actuelle == 'vestibule' else 'retournez au vestibule'}",
            "",
            "Votre phrase finale doit reconstituer, dans l'ordre :",
            "  1. l'identité du coupable et son mobile ;",
            "  2. ce qui a été administré à Éléonore et au repas ;",
            "  3. l'agression de Mathilde et la fausse piste visant Damien ;",
            "  4. le sabotage de la machine et la fuite ;",
            "  5. le rôle d'Auguste à 3 h 15.",
            "",
            "Commande : conclure [votre phrase complète]",
            "Attention : un seul dépôt est autorisé.",
        ]
        if manquantes:
            zones = []
            correspondance = {
                "digitaline": "cuisine",
                "sedatif_repas": "salle à manger",
                "journal_falsifie": "bibliothèque et comparaison d'écritures",
                "polaroid_detail": "chambre d'Éléonore et lumière rasante",
                "couteau_damien": "salle de bain",
                "lettre_mathilde": "chambre des maîtres",
                "sabotage_cable": "atelier",
                "cylindre_dispute": "grenier et phonographe",
                "fuite_jardin": "jardin ou serre",
                "echo_315": "crypte",
            }
            zones = [correspondance[cle] for cle in sorted(manquantes)]
            lignes.append("")
            lignes.append("Le dossier comporte encore des lacunes dans : " + ", ".join(zones) + ".")
        elif not machine:
            lignes.append("")
            lignes.append("Toutes les preuves sont réunies, mais la maison retient encore le dossier.")
        else:
            lignes.append("")
            lignes.append(self._couleur("DOSSIER COMPLET — votre prochaine conclusion sera définitive.", Couleur.ROUGE + Couleur.GRAS))
        return "\n".join(lignes)

    def conclure(self, phrase: str) -> bool:
        if self.drapeaux["report_attempted"]:
            self.dire("Le rapport a déjà été déposé. Aucune seconde version n'est recevable.")
            return False
        if not self.drapeaux["machine_silenced"]:
            self.dire("La machine doit être neutralisée avant que les scellés puissent être levés.")
            return False
        if self.piece_actuelle != "vestibule":
            self.dire("Le formulaire officiel se trouve dans votre mallette, au vestibule.")
            return False

        manquantes = self._preuves_obligatoires().difference(self.preuves_enquete)
        if manquantes:
            self.dire(
                "Votre dossier ne contient pas encore assez de preuves structurantes. "
                "Consultez « rapport final » : le dépôt n'est pas encore ouvert."
            )
            return False
        if not phrase.strip():
            self.dire("Vous devez rédiger une phrase complète après la commande « conclure ».")
            return False

        self.drapeaux["report_attempted"] = True
        texte = normaliser(phrase)
        tests = [
            ("coupable", any(mot in texte for mot in ("marguerite", "bellac"))),
            (
                "mobile",
                any(
                    mot in texte
                    for mot in (
                        "depart",
                        "renvoi",
                        "abandon",
                        "indispensable",
                        "quitter",
                        "garder la famille",
                    )
                ),
            ),
            (
                "empoisonnement d'Éléonore",
                "eleonore" in texte
                and any(
                    mot in texte
                    for mot in ("empoison", "digitaline", "medicament", "gouttes")
                ),
            ),
            (
                "repas drogué",
                any(
                    mot in texte
                    for mot in ("drog", "sedatif", "chloral", "somnifere")
                )
                and any(
                    mot in texte
                    for mot in ("repas", "verre", "vin", "diner")
                ),
            ),
            (
                "agression de Mathilde",
                "mathilde" in texte
                and any(
                    mot in texte
                    for mot in ("poignard", "couteau", "blesse", "attaque", "tue")
                ),
            ),
            (
                "innocence de Damien",
                "damien" in texte
                and any(
                    mot in texte
                    for mot in (
                        "innocent",
                        "secour",
                        "sauv",
                        "soign",
                        "fausse piste",
                        "accuse",
                    )
                ),
            ),
            (
                "sabotage",
                any(mot in texte for mot in ("sabot", "coupe", "sectionne", "arrache"))
                and any(mot in texte for mot in ("cable", "mise a terre", "machine")),
            ),
            (
                "fuite",
                any(mot in texte for mot in ("fui", "fuite", "echappe", "jardin", "serre")),
            ),
            (
                "rôle d'Auguste",
                "auguste" in texte
                and any(
                    mot in texte
                    for mot in ("active", "activee", "declenche", "demarre", "3 h 15", "315")
                ),
            ),
        ]
        correct = all(ok for _, ok in tests)

        self.drapeaux["game_complete"] = True
        self.termine = True

        if correct:
            self.fin = "mandat"
            self.dire(
                self._couleur("\nFIN — LE MANDAT BELLAC", Couleur.VERT + Couleur.GRAS)
                + "\nVotre chronologie résiste à chaque contradiction. Le parquet transmet immédiatement "
                "le dossier au juge d'instruction.\n\n"
                "Marguerite Bellac a entretenu la maladie d'Éléonore par la digitaline afin de "
                "rester indispensable, puis a drogué le repas lorsque Mathilde a annoncé son "
                "renvoi. Elle a volé le couteau de Damien, poignardé Mathilde, saboté la mise à "
                "la terre de la machine et fabriqué des preuves contre le jeune homme. Damien "
                "tentait de sauver sa mère sur la photographie. À 3 h 15, Auguste a déclenché "
                "la chambre de résonance dans la panique, faisant disparaître les quatre membres "
                "de la famille restés dans la chapelle. Marguerite a fui par la serre.\n\n"
                "Un mandat d'arrêt national est lancé contre Marguerite Bellac pour empoisonnement, "
                "homicide, falsification de preuves et sabotage. Pour la première fois depuis "
                "quatre ans, le dossier Valombre possède une vérité judiciaire."
            )
            self._succes("La vérité tient en une phrase")
        else:
            self.fin = "erreur_judiciaire"
            manques = [nom for nom, ok in tests if not ok]
            self.dire(
                self._couleur("\nGAME OVER — ERREUR JUDICIAIRE", Couleur.ROUGE + Couleur.GRAS)
                + "\nLe rapport est signé et transmis. Il ne peut plus être corrigé.\n"
                "Votre version laisse des contradictions essentielles : "
                + ", ".join(manques)
                + ".\n\nLe suspect visé obtient un non-lieu. Marguerite Bellac, avertie par la "
                "réouverture de l'enquête, disparaît sous une nouvelle identité. Le dossier "
                "Valombre est définitivement classé."
            )
        self.dire(self._bilan(len(self.preuves_enquete), 0))
        return True

    @staticmethod
    def _cible_est(texte: str, *alias: str) -> bool:
        cible = nettoyer_cible(texte)
        formes = [nettoyer_cible(alias_item) for alias_item in alias]
        return any(forme and (cible == forme or forme in cible) for forme in formes)

    # ----- Commandes générales -----------------------------------------

    def executer(self, commande: str) -> str:
        self._sortie = []
        brut = commande.strip()
        cmd = normaliser(brut)
        if not cmd:
            return ""

        if self.termine and cmd not in {"charger", "load", "quitter", "quit", "sortir"} and not cmd.startswith("charger "):
            self.dire("L'histoire est terminée. Vous pouvez charger une sauvegarde ou quitter.")
            return "\n".join(self._sortie)

        mots = cmd.split()
        verbe = mots[0]
        reste = " ".join(mots[1:])
        consomme_tour = False

        # Confort et méta-commandes.
        if cmd in {"aide", "help", "commandes", "?"}:
            self.dire(self.aide())
        elif cmd in {"regarder", "observer", "regarder autour", "decrire", "description"}:
            self.dire(self.decrire_piece())
        elif cmd in {"inventaire", "inv", "i", "sac"}:
            self.dire(self.afficher_inventaire())
        elif cmd in {"objectifs", "objectif", "mission", "missions"}:
            self.dire(self.afficher_objectifs())
        elif cmd in {"journal", "notes", "carnet", "indices trouves"}:
            self.dire(self.afficher_journal())
        elif cmd in {"preuves", "preuve", "pieces a conviction", "elements"}:
            self.dire(self.afficher_preuves())
        elif cmd in {"suspects", "suspect", "signalements", "personnages"}:
            self.dire(self.afficher_suspects())
        elif cmd in {"rapport final", "rapport definitif", "conclusion", "etat du rapport"}:
            self.dire(self.afficher_rapport_final())
        elif verbe == "conclure":
            consomme_tour = self.conclure(reste)
        elif cmd in {
                "rapport",
                "dossier",
                "affaire",
                "dossier valombre",
                "personnes disparues",
            }:
            self.dire(self.rapport_affaire())
        elif cmd in {"indice", "indices", "hint", "aide moi"}:
            self.dire(self.donner_indice())
        elif cmd in {"carte", "map", "plan"}:
            self.dire(self.afficher_carte())
        elif cmd in {"succes", "achievements", "secrets"}:
            self.dire(self.afficher_succes())
        elif verbe in {"sauvegarder", "save"}:
            self.dire(self.sauvegarder(reste or str(DEFAULT_SAVE)))
        elif verbe in {"charger", "load"}:
            self.dire(self.charger(reste or str(DEFAULT_SAVE)))
        elif verbe == "ascii":
            self.dire(self.regler_ascii(reste))
        elif verbe in {"couleur", "color"}:
            self.dire(self.regler_couleur_prompt(reste))
        elif verbe in {"largeur", "width"}:
            self.dire(self.regler_largeur(reste))
        elif cmd in {"quitter", "quit", "exit", "sortir du jeu"}:
            self.termine = True
            self.dire("Vous refermez le carnet d'enquête. Merci d'avoir joué.")

        # Déplacement direct ou précédé d'un verbe.
        elif verbe in {"aller", "va", "marcher", "deplacer", "rendre"}:
            consomme_tour = self.deplacer(reste)
        elif verbe in {"nord", "sud", "est", "ouest", "haut", "bas"} and len(mots) == 1:
            consomme_tour = self.deplacer(verbe)
        elif verbe in {"monter", "grimpe"}:
            consomme_tour = self.deplacer("haut")
        elif verbe in {"descendre", "descend"}:
            consomme_tour = self.deplacer("bas")

        # Actions sur le monde.
        elif verbe in {"prendre", "ramasser", "recuperer", "saisir"}:
            consomme_tour = self.prendre(reste)
        elif verbe in {"inspecter", "examiner", "observer", "regarder", "fouiller"}:
            consomme_tour = self.inspecter(reste, verbe)
        elif verbe in {"lire", "dechiffrer"}:
            consomme_tour = self.lire(reste)
        elif verbe in {"utiliser", "employer", "servir"}:
            consomme_tour = self.utiliser(reste)
        elif verbe in {"combiner", "assembler", "associer"}:
            consomme_tour = self.combiner(reste)
        elif verbe in {"comparer", "confronter"}:
            consomme_tour = self.comparer(reste)
        elif verbe in {"ouvrir", "deverrouiller"}:
            consomme_tour = self.action_contextuelle("ouvrir", reste, cmd)
        elif verbe in {"allumer", "eteindre"}:
            consomme_tour = self.action_contextuelle(verbe, reste, cmd)
        elif verbe in {"ecouter", "entendre"}:
            consomme_tour = self.action_contextuelle("ecouter", reste, cmd)
        elif verbe in {"soulever", "pousser", "tirer", "tourner"}:
            consomme_tour = self.action_contextuelle(verbe, reste, cmd)
        elif verbe in {"entrer", "taper", "composer", "saisir"}:
            consomme_tour = self.action_contextuelle("entrer", reste, cmd)
        elif verbe in {"regler", "positionner", "mettre"}:
            consomme_tour = self.action_contextuelle("regler", reste, cmd)
        elif verbe in {"ordonner", "aligner", "classer"}:
            consomme_tour = self.action_contextuelle("ordonner", reste, cmd)
        elif verbe in {"placer", "poser", "inserer"}:
            consomme_tour = self.action_contextuelle("placer", reste, cmd)
        elif verbe in {"creuser", "deterrer"}:
            consomme_tour = self.action_contextuelle("creuser", reste, cmd)
        elif verbe in {"arreter", "desactiver", "detruire"}:
            consomme_tour = self.action_contextuelle("arreter", reste, cmd)
        elif verbe in {"activer", "reveiller", "demarrer"}:
            consomme_tour = self.action_contextuelle("activer", reste, cmd)
        else:
            self.dire("La maison ne comprend pas cette intention. Tapez « aide » pour voir les commandes.")

        if consomme_tour and not self.termine:
            self.tours += 1
            self._evenement_aleatoire()
        return "\n".join(self._sortie)

    def deplacer(self, demande: str) -> bool:
        demande = nettoyer_cible(demande)
        if not demande:
            self.dire("Aller où ?")
            return False

        directions = {
            "n": "nord",
            "nord": "nord",
            "s": "sud",
            "sud": "sud",
            "e": "est",
            "est": "est",
            "o": "ouest",
            "ouest": "ouest",
            "w": "ouest",
            "haut": "haut",
            "monter": "haut",
            "etage": "haut",
            "bas": "bas",
            "descendre": "bas",
            "sous sol": "bas",
            "cave": "bas",
        }
        direction = directions.get(demande)
        piece = self.pieces[self.piece_actuelle]

        if direction is None:
            # Autorise « aller cuisine » pour une pièce directement voisine.
            for direction_candidate, sortie_candidate in piece.sorties.items():
                destination = self.pieces[sortie_candidate.destination]
                formes = {nettoyer_cible(destination.nom), normaliser(destination.identifiant)}
                formes.update(nettoyer_cible(alias) for alias in destination.alias)
                if demande in formes or any(forme and forme in demande for forme in formes):
                    direction = direction_candidate
                    break

        if direction is None or direction not in piece.sorties:
            self.dire("Vous ne trouvez aucun passage dans cette direction.")
            return False

        sortie = piece.sorties[direction]
        if sortie.visible_si and not self.drapeaux.get(sortie.visible_si, False):
            self.dire("Vous ne voyez aucun passage par là.")
            return False
        if sortie.condition and not self.drapeaux.get(sortie.condition, False):
            self.dire(sortie.message_bloque)
            return False

        self.piece_actuelle = sortie.destination
        self.visitees.add(sortie.destination)
        self.dire(self.decrire_piece())
        return True

    def prendre(self, cible: str) -> bool:
        if self.piece_actuelle == "crypte" and self._cible_est(cible, "tresor", "or", "richesses"):
            return self._fin_cupidite()

        objet_id = self._objet_piece(cible)
        if objet_id is None:
            if self._objet_inventaire(cible):
                self.dire("Vous possédez déjà cet objet.")
            else:
                self.dire("Vous ne trouvez rien de ce nom à prendre ici.")
            return False

        objet = self.objets[objet_id]
        if not objet.portable:
            self.dire("Cet élément ne peut pas être emporté.")
            return False

        self.pieces[self.piece_actuelle].objets.remove(objet_id)
        self.inventaire.append(objet_id)
        self.dire(f"Vous prenez {objet.nom}.")
        return True

    def inspecter(self, cible: str, verbe: str = "inspecter") -> bool:
        if not cible:
            self.dire(self.decrire_piece())
            return False

        objet_id = self._objet_accessible(cible)
        if objet_id:
            special = self._examiner_objet_enquete(objet_id)
            if special is not None:
                self.dire(special)
                return True

            objet = self.objets[objet_id]
            description = objet.description
            if objet_id == "lampe_torche" and self.drapeaux["flashlight_ready"]:
                description = "La lampe torche contient maintenant une pile et projette un faisceau stable."
            elif objet_id == "lettre_chiffree" and self.drapeaux["letter_decoded"]:
                description = "La lettre a été décodée. Vos annotations font apparaître clairement le mot AUBE."
            self.dire(f"{objet.nom.capitalize()} — {description}")
            return True

        return self.action_contextuelle("inspecter", cible, f"{verbe} {cible}")

    def lire(self, cible: str) -> bool:
        objet_id = self._objet_accessible(cible)
        if objet_id == "note_recette":
            self.dire(
                "La recette ne décrit aucun plat cohérent :\n"
                "  « Sept roses, quatre grains de poivre, une feuille de laurier, deux clous. »\n"
                "Les quantités semblent plus importantes que les ingrédients."
            )
            self._decouvrir("code_7412", "La recette suggère la suite 7-4-1-2.")
            return True
        if objet_id == "journal_valombre":
            self.dire(
                "Les pages authentiques du journal d'Éléonore décrivent sa maladie, les fleurs de "
                "la serre et la machine de son père :\n"
                "  « La rose ouvre la voie, l'iris la regarde, le lys les suit et le pavot ferme la marche. »\n\n"
                "La toute dernière page est écrite d'une main plus ferme :\n"
                "  « D. me fait peur. Ses sautes d'humeur empirent. Il a apporté un couteau. »\n"
                "La lettre D semble désigner Damien, mais l'encre, la pression et l'écriture diffèrent. "
                "Un échantillon fiable permettrait une comparaison."
            )
            self._decouvrir("annee_1987", "La disparition et la dernière entrée datent de 1987.")
            self._decouvrir("ordre_fleurs", "Rose → iris → lys → pavot.")
            return True
        if objet_id == "registre_domestique":
            special = self._examiner_objet_enquete(objet_id)
            if special:
                self.dire(special)
            return True
        if objet_id == "lettre_mathilde":
            special = self._examiner_objet_enquete(objet_id)
            if special:
                self.dire(special)
            return True
        if objet_id == "lettre_chiffree":
            if not self.drapeaux["letter_decoded"]:
                self.dire("Les groupes de lettres restent incompréhensibles. Il vous faut un dispositif de déchiffrement.")
            else:
                self.dire(
                    "La lettre décodée est signée Auguste Valombre :\n"
                    "  « La mise à la terre a été coupée avant la séance. Je l'ai vu trop tard. "
                    "Si la chambre se verrouille, prononce AUBE, coupe l'alimentation et rends "
                    "son médaillon à Éléonore. À 3 h 15, j'ai tout déclenché dans la panique. »"
                )
                self._decouvrir("mot_aube", "Le mot de sécurité de la machine est AUBE.")
                self._decouvrir("verite_machine", "Auguste a activé la machine à 3 h 15 après un sabotage.")
            return True
        if objet_id == "lettre_enterree":
            special = self._examiner_objet_enquete(objet_id)
            if special:
                self.dire(special)
            return True
        if objet_id == "cylindre_urgence":
            self.dire(
                "Un cylindre de cire ne se lit pas à l'œil. L'étiquette indique 3 h 10 et le "
                "phonographe du grenier semble encore complet."
            )
            return True
        if objet_id:
            special = self._examiner_objet_enquete(objet_id)
            if special is not None:
                self.dire(special)
                return True
            self.dire("Cet objet ne contient rien de lisible.")
            return False

        return self.action_contextuelle("lire", cible, f"lire {cible}")

    def utiliser(self, reste: str) -> bool:
        if not reste:
            self.dire("Utiliser quoi, et sur quoi ?")
            return False

        gauche, droite = reste, ""
        for separateur in (" sur ", " avec ", " dans "):
            if separateur in f" {reste} ":
                gauche, droite = reste.split(separateur.strip(), 1) if separateur.strip() in reste else (reste, "")
                break

        # Le split précédent doit aussi gérer proprement les espaces.
        match = re.match(r"(.+?)\s+(?:sur|avec|dans)\s+(.+)", reste)
        if match:
            gauche, droite = match.group(1), match.group(2)

        objet_gauche = self._objet_inventaire(gauche)
        objet_droite = self._objet_inventaire(droite) if droite else None

        # Accepte l'ordre inverse : « utiliser lampe avec pile ».
        if objet_gauche is None and objet_droite is not None:
            objet_gauche, gauche, droite = objet_droite, droite, gauche

        if objet_gauche is None:
            # Certaines cibles sont des éléments fixes de la pièce : interrupteur,
            # robinet, machine, etc. « utiliser interrupteur » doit donc rester valide.
            return self.action_contextuelle("utiliser", reste, f"utiliser {reste}")

        if self._combinaison_speciale(objet_gauche, objet_droite, droite):
            return True

        return self.action_contextuelle(
            "utiliser",
            droite or gauche,
            f"utiliser {reste}",
            objet_utilise=objet_gauche,
        )

    def combiner(self, reste: str) -> bool:
        match = re.match(r"(.+?)\s+(?:avec|et|sur)\s+(.+)", reste)
        if not match:
            self.dire("Exemple : combiner pile avec lampe.")
            return False
        premier = self._objet_inventaire(match.group(1))
        second = self._objet_inventaire(match.group(2))
        if not premier or not second:
            self.dire("Vous devez posséder les deux objets à combiner.")
            return False
        if self._combinaison_speciale(premier, second, match.group(2)):
            return True
        if self._combinaison_speciale(second, premier, match.group(1)):
            return True
        self.dire("Ces deux objets ne s'assemblent pas de manière utile.")
        return False

    def _combinaison_speciale(self, premier: str, second: str | None, cible_texte: str) -> bool:
        paire = {premier, second} if second else {premier}
        cible_norm = nettoyer_cible(cible_texte)

        if "pile_seche" in paire and "lampe_torche" in paire:
            if self.drapeaux["flashlight_ready"]:
                self.dire("La pile est déjà installée dans la lampe.")
                return False
            self._retirer_inventaire("pile_seche")
            self.drapeaux["flashlight_ready"] = True
            self.dire("Vous installez la pile sèche. La lampe torche s'allume avec un claquement rassurant.")
            self._succes("Que la lumière soit")
            return True

        if premier == "pile_seche" and self._cible_est(cible_norm, "lampe", "lampe torche") and self._possede("lampe_torche"):
            return self._combinaison_speciale("pile_seche", "lampe_torche", cible_norm)
        if premier == "lampe_torche" and self._cible_est(cible_norm, "pile", "pile seche") and self._possede("pile_seche"):
            return self._combinaison_speciale("lampe_torche", "pile_seche", cible_norm)

        if "lampe_torche" in paire and "polaroid_flou" in paire:
            if not self.drapeaux["flashlight_ready"]:
                self.dire("La lampe ne contient aucune pile.")
                return False
            if self.drapeaux["polaroid_enhanced"]:
                self.dire("Les détails utiles de la photographie ont déjà été relevés.")
                return False
            self.drapeaux["polaroid_enhanced"] = True
            self._ajouter_preuve(
                "polaroid_detail",
                "La lumière rasante montre que Damien tentait de sauver Mathilde ; une silhouette verte fuyait.",
            )
            self.dire(
                "Vous placez la photographie presque parallèlement au faisceau. Les reliefs de "
                "l'émulsion apparaissent : Damien ne brandit pas le couteau pour frapper. Il "
                "découpe le vêtement de Mathilde et comprime sa blessure. Derrière lui, une "
                "petite silhouette vêtue de vert franchit la porte, le pied gauche traînant."
            )
            self._succes("Au-delà du flou")
            return True

        if premier == "lampe_torche" and self._cible_est(cible_norm, "polaroid", "photo", "photographie") and self._possede("polaroid_flou"):
            return self._combinaison_speciale("lampe_torche", "polaroid_flou", cible_norm)
        if premier == "polaroid_flou" and self._cible_est(cible_norm, "lampe", "lampe torche") and self._possede("lampe_torche"):
            return self._combinaison_speciale("polaroid_flou", "lampe_torche", cible_norm)

        if premier == "cylindre_urgence" and self._cible_est(cible_norm, "phonographe", "gramophone", "lecteur"):
            if self.piece_actuelle != "grenier":
                self.dire("Le phonographe capable de lire ce cylindre se trouve dans le grenier.")
                return False
            if self.drapeaux["cylinder_played"]:
                self.dire("L'enregistrement a déjà été transcrit dans votre dossier.")
                return False
            self.drapeaux["cylinder_played"] = True
            self._ajouter_preuve(
                "cylindre_dispute",
                "L'enregistrement de 3 h 10 place Marguerite avec le couteau et révèle le repas drogué.",
            )
            self.dire(
                "Le cylindre grésille puis restitue une dispute :\n"
                "  MATHILDE : « Les verres, les gouttes d'Éléonore... c'était vous depuis le début. »\n"
                "  MARGUERITE : « Vous alliez tous partir. Vous me laissiez seule. »\n"
                "  DAMIEN : « Marguerite, posez mon couteau. Maintenant. »\n"
                "Un choc interrompt l'enregistrement à 3 h 12."
            )
            self._succes("La voix de 3 h 10")
            return True

        if premier == "disque_chiffrement" and self._cible_est(cible_norm, "lettre", "lettre chiffree"):
            return self._decoder_lettre()
        if premier == "lettre_chiffree" and self._cible_est(cible_norm, "disque", "disque de chiffrement") and self._possede("disque_chiffrement"):
            return self._decoder_lettre()
        return False

    def _decoder_lettre(self) -> bool:
        if self.piece_actuelle != "bureau_secret" and not self._possede("lettre_chiffree"):
            self.dire("Vous n'avez pas la lettre chiffrée à portée de main.")
            return False
        if not self._possede("disque_chiffrement"):
            self.dire("Il vous manque le disque de chiffrement.")
            return False
        if not self._possede("lettre_chiffree"):
            self.dire("Prenez d'abord la lettre pour pouvoir la manipuler.")
            return False
        if self.drapeaux["letter_decoded"]:
            self.dire("La lettre est déjà décodée.")
            return False
        self.drapeaux["letter_decoded"] = True
        self.dire(
            "Vous alignez le symbole solaire du disque avec la lettre A. Après plusieurs rotations, les groupes\n"
            "incohérents deviennent des phrases. Un mot revient trois fois, souligné : AUBE."
        )
        self._decouvrir("mot_aube", "Le mot de sécurité de la machine est AUBE.")
        self._decouvrir("verite_machine", "La machine a capturé les souvenirs et les voix de la famille.")
        self._succes("Cryptographe")
        return True

    # ----- Interactions contextuelles ----------------------------------

    def action_contextuelle(
        self,
        verbe: str,
        cible: str,
        commande_complete: str,
        *,
        objet_utilise: str | None = None,
    ) -> bool:
        gestionnaires = {
            "salon": self._action_salon,
            "cuisine": self._action_cuisine,
            "salle_a_manger": self._action_salle_a_manger,
            "vestibule": self._action_vestibule,
            "couloir": self._action_couloir,
            "bibliotheque": self._action_bibliotheque,
            "chapelle": self._action_chapelle,
            "palier": self._action_palier,
            "chambre_maitre": self._action_chambre_maitre,
            "chambre_enfant": self._action_chambre_enfant,
            "salle_de_bain": self._action_salle_de_bain,
            "grenier": self._action_grenier,
            "cave": self._action_cave,
            "atelier": self._action_atelier,
            "bureau_secret": self._action_bureau_secret,
            "jardin": self._action_jardin,
            "serre": self._action_serre,
            "crypte": self._action_crypte,
        }
        traite = gestionnaires[self.piece_actuelle](verbe, cible, commande_complete, objet_utilise)
        if not traite:
            if objet_utilise:
                self.dire(f"{self.objets[objet_utilise].nom.capitalize()} n'a aucun effet utile ici.")
            else:
                self.dire("Vous essayez, mais rien de pertinent ne se produit.")
        return traite

    def _action_salon(self, verbe: str, cible: str, cmd: str, objet: str | None) -> bool:
        if self._cible_est(cible, "horloge", "grande horloge", "pendule"):
            if verbe in {"inspecter", "lire"}:
                if self.drapeaux["clock_open"]:
                    self.dire("Le cadran indique 3 h 15. Son socle cache un compartiment maintenant ouvert.")
                elif self.drapeaux["clock_wound"]:
                    self.dire("L'horloge fonctionne, mais les aiguilles peuvent être déplacées manuellement.")
                else:
                    self.dire("L'horloge est arrêtée à 3 h 15. Un petit orifice carré attend une clé de remontage.")
                self._decouvrir("heure_315", "L'horloge et la photographie insistent sur 3 h 15.")
                return True
            if verbe == "utiliser" and objet == "cle_remontage":
                if self.drapeaux["clock_wound"]:
                    self.dire("L'horloge est déjà remontée.")
                    return False
                self.drapeaux["clock_wound"] = True
                self.dire("La clé tourne trois fois. Le balancier repart et un mécanisme interne se déverrouille.")
                return True
            if verbe == "regler":
                code = extraire_chiffres(cmd)
                if not self.drapeaux["clock_wound"]:
                    self.dire("Les aiguilles résistent : le mécanisme doit d'abord être remonté.")
                    return False
                if code in {"315", "0315"}:
                    if self.drapeaux["clock_open"]:
                        self.dire("Le compartiment est déjà ouvert.")
                        return False
                    self.drapeaux["clock_open"] = True
                    self._ajouter_dans_piece("salon", "sceau_solaire", "cle_laiton")
                    self.dire(
                        "À 3 h 15 exactement, les douze chiffres du cadran s'enfoncent. Le socle s'ouvre et révèle\n"
                        "un sceau solaire ainsi qu'une clé en laiton marquée d'un livre."
                    )
                    self._succes("À l'heure du crime")
                    return True
                self.dire("L'horloge sonne une fois, sèchement, puis rejette ce réglage.")
                self._augmenter_tension(2)
                return True

        if self._cible_est(cible, "photographie", "photo", "famille", "photographie de famille") and verbe in {"inspecter", "lire"}:
            self.dire(
                "Les cinq personnes correspondent au rapport : Auguste est grand et blond cendré ; "
                "Mathilde, brune, se tient à sa gauche ; Damien dépasse son père et porte les cheveux "
                "blonds ; Éléonore serre la main de Marguerite, petite, en uniforme vert sombre. "
                "Marguerite appuie nettement moins sur sa jambe gauche. Sous le cadre : "
                "« Notre dernière réunion, 15 octobre 1987 — 3 h 15 »."
            )
            self._ajouter_preuve(
                "profils_famille",
                "La photographie confirme les tailles, les cheveux et la boiterie décrits dans le rapport.",
            )
            self._decouvrir("heure_315", "La dernière photographie familiale a été prise à 3 h 15.")
            self._decouvrir("annee_1987", "La dernière réunion familiale date de 1987.")
            return True
        if self._cible_est(cible, "cheminee", "foyer") and verbe in {"inspecter", "ouvrir"}:
            self.dire("Dans la suie, quelqu'un a tracé trois cercles : bronze, ivoire et pierre verte.")
            self._decouvrir("trois_sceaux", "Trois sceaux de matières différentes sont liés à la maison.")
            return True
        if self._cible_est(cible, "sofa", "canape") and verbe in {"inspecter", "fouiller", "soulever"}:
            self.dire("Sous les coussins, vous ne trouvez qu'un bouton de manchette et une odeur de poussière.")
            return True
        return False

    def _action_cuisine(self, verbe: str, cible: str, cmd: str, objet: str | None) -> bool:
        if self._cible_est(cible, "glaciere", "refrigerateur", "frigo", "cadenas"):
            if verbe in {"inspecter", "ouvrir"}:
                if self.drapeaux["icebox_open"]:
                    self.dire("La glacière est ouverte ; son contenu peut être examiné et emporté.")
                else:
                    self.dire("Un clavier à quatre chiffres remplace la serrure de la glacière.")
                return True
        if verbe == "entrer":
            code = extraire_chiffres(cmd)
            if code == "7412":
                if self.drapeaux["icebox_open"]:
                    self.dire("Le cadenas est déjà ouvert.")
                    return False
                self.drapeaux["icebox_open"] = True
                self._ajouter_dans_piece(
                    "cuisine",
                    "pile_seche",
                    "cle_remontage",
                    "flacon_digitaline",
                )
                self.dire(
                    "Le clavier accepte 7412. Dans la glacière reposent une pile sèche, une clé "
                    "de remontage et un flacon pharmaceutique presque vide."
                )
                self._succes("La recette impossible")
                return True
            self.dire("Le clavier clignote rouge. Code incorrect.")
            self._augmenter_tension(1)
            return True
        if self._cible_est(cible, "placards", "placard", "tiroirs") and verbe in {"ouvrir", "inspecter", "fouiller"}:
            if not self.drapeaux["matches_found"]:
                self.drapeaux["matches_found"] = True
                self._ajouter_dans_piece("cuisine", "allumettes")
                self.dire("Derrière des assiettes fendues, vous trouvez une boîte d'allumettes encore presque sèche.")
            else:
                self.dire("Les placards ne contiennent plus rien d'utile.")
            return True
        if self._cible_est(cible, "evier", "eau") and verbe in {"inspecter", "ouvrir", "allumer"}:
            self.dire(
                "Dans le siphon, une pellicule médicinale amère s'est déposée. Quelqu'un a rincé "
                "des instruments ou des compte-gouttes ici peu avant la disparition."
            )
            return True
        if self._cible_est(cible, "recette", "note") and verbe == "lire":
            return self.lire("note de recette")
        return False

    def _action_salle_a_manger(self, verbe: str, cible: str, cmd: str, objet: str | None) -> bool:
        if self._cible_est(cible, "portes fenetres", "porte fenetre", "portes du jardin", "serrure", "jardin"):
            if verbe in {"inspecter", "ouvrir"}:
                if self.drapeaux["garden_unlocked"]:
                    self.dire("Les portes-fenêtres s'ouvrent maintenant sur le jardin détrempé.")
                else:
                    self.dire("La serrure est trop longue pour une clé ordinaire. Une feuille de lierre est gravée autour du pêne.")
                return True
            if verbe == "utiliser" and objet == "cle_jardin":
                if self.drapeaux["garden_unlocked"]:
                    self.dire("Les portes sont déjà déverrouillées.")
                    return False
                self.drapeaux["garden_unlocked"] = True
                self.dire("La longue clé de fer tourne. Les portes-fenêtres s'entrouvrent sous la poussée du vent.")
                return True
        if self._cible_est(cible, "bougies", "chandelier"):
            if verbe == "utiliser" and objet == "allumettes":
                if self.drapeaux["dining_candles_lit"]:
                    self.dire("Les bougies brûlent déjà.")
                    return False
                self.drapeaux["dining_candles_lit"] = True
                self.dire(
                    "Les mèches prennent. La lumière rasante révèle des lettres gravées sous le "
                    "bord de la table et un éclat de verre près de la cinquième chaise."
                )
                return True
            if verbe == "allumer":
                if self._possede("allumettes"):
                    return self._action_salle_a_manger("utiliser", cible, cmd, "allumettes")
                self.dire("Il vous faudrait de quoi produire une flamme.")
                return False
            if verbe == "inspecter":
                self.dire("Les bougies ont été utilisées lors d'un repas qui n'a jamais été débarrassé.")
                return True
        if self._cible_est(cible, "table", "inscription", "verres", "repas", "serviettes", "chaise"):
            if verbe in {"inspecter", "lire", "fouiller"}:
                if self.drapeaux["dining_candles_lit"]:
                    self.dire(
                        "Sous le plateau : « Nous partirons avant la fin de 1987. — M. »\n"
                        "Quatre verres portent un dépôt blanchâtre identique. Le verre d'Éléonore "
                        "n'en contient pas. Près de la place de Marguerite, derrière une serviette "
                        "verte, vous trouvez une ampoule pharmaceutique brisée."
                    )
                    self._ajouter_dans_piece("salle_a_manger", "ampoule_chloral")
                    self._decouvrir("annee_1987", "La famille préparait un départ en 1987.")
                else:
                    self.dire(
                        "La table est couverte de poussière. Les verres semblent tachés, mais la "
                        "lumière est trop mauvaise pour distinguer les dépôts."
                    )
                return True
        return False

    def _action_vestibule(self, verbe: str, cible: str, cmd: str, objet: str | None) -> bool:
        if self._cible_est(cible, "porte", "porte entree", "sortie", "dehors"):
            if verbe in {"inspecter", "ouvrir", "tirer", "pousser"}:
                if self.drapeaux["machine_silenced"]:
                    self.dire(
                        "La pression invisible a disparu. La porte s'ouvre, mais votre mallette "
                        "attend encore le rapport final. Tapez « rapport final » avant de partir."
                    )
                else:
                    self.dire("La poignée tourne, mais une pression invisible maintient la porte fermée. La maison n'a pas fini avec vous.")
                return True
        if self._cible_est(cible, "porte parapluies", "parapluies", "patere", "manteaux") and verbe in {"inspecter", "fouiller"}:
            self.dire(
                "Dans le manteau de Damien, un billet pour Genève daté du 16 octobre 1987 n'a "
                "jamais été composté. Au dos, il a écrit : « Je ne repartirais pas sans Éléonore. »"
            )
            self._ajouter_preuve(
                "ticket_damien",
                "Damien avait annulé son départ afin de rester auprès de sa sœur.",
            )
            self._decouvrir("depart_manque", "Damien devait quitter la région le 16 octobre 1987.")
            return True
        if self._cible_est(cible, "mallette", "rapport final", "formulaire", "dossier") and verbe in {"inspecter", "ouvrir", "lire"}:
            self.dire(self.afficher_rapport_final())
            return True
        return False

    def _action_couloir(self, verbe: str, cible: str, cmd: str, objet: str | None) -> bool:
        if self._cible_est(cible, "tableau", "peinture", "homme sans visage"):
            if verbe in {"inspecter", "soulever", "pousser", "tirer", "tourner"}:
                if not self.drapeaux["painting_switch_found"]:
                    self.drapeaux["painting_switch_found"] = True
                    self.dire("Vous écartez le tableau. Un interrupteur de cuivre est encastré dans le mur.")
                else:
                    self.dire("Le tableau cache l'interrupteur de cuivre déjà découvert.")
                return True
        if self._cible_est(cible, "interrupteur", "bouton", "levier") and verbe in {"utiliser", "allumer", "pousser", "tirer", "tourner"}:
            if not self.drapeaux["painting_switch_found"]:
                self.dire("Vous ne voyez aucun interrupteur ici.")
                return False
            if self.drapeaux["cellar_revealed"]:
                self.dire("Le passage de la cave est déjà ouvert.")
                return False
            self.drapeaux["cellar_revealed"] = True
            self.dire("Le mur gronde et pivote de quelques degrés, révélant un escalier qui descend sous la maison.")
            self._succes("Derrière les apparences")
            return True
        if self._cible_est(cible, "escalier", "cave", "passage") and verbe in {"inspecter", "ouvrir"}:
            if not self.drapeaux["cellar_revealed"]:
                self.dire("L'escalier visible monte à l'étage. Aucun accès à la cave n'apparaît encore.")
            elif not self.drapeaux["flashlight_ready"]:
                self.dire("L'escalier secret est si noir que descendre sans lampe serait imprudent.")
            else:
                self.dire("Votre lampe permet de suivre les marches humides vers la cave.")
            return True
        if self._cible_est(cible, "porte chapelle", "chapelle") and verbe in {"inspecter", "ouvrir"}:
            self.dire("La porte de la chapelle n'est pas verrouillée. Elle s'ouvre vers l'est.")
            return True
        return False

    def _action_bibliotheque(self, verbe: str, cible: str, cmd: str, objet: str | None) -> bool:
        if self._cible_est(cible, "vitrine", "serrure", "journal", "disque", "registre"):
            if verbe in {"inspecter", "ouvrir"}:
                if self.drapeaux["library_case_open"]:
                    self.dire("La vitrine est ouverte. Le journal, le registre et le disque peuvent être pris.")
                else:
                    self.dire("La serrure de la vitrine porte le symbole d'un livre ouvert.")
                return True
            if verbe == "utiliser" and objet == "cle_laiton":
                if self.drapeaux["library_case_open"]:
                    self.dire("La vitrine est déjà ouverte.")
                    return False
                self.drapeaux["library_case_open"] = True
                self._ajouter_dans_piece(
                    "bibliotheque",
                    "journal_valombre",
                    "registre_domestique",
                    "disque_chiffrement",
                )
                self.dire(
                    "La clé en laiton ouvre la vitrine. Le journal d'Éléonore, le registre "
                    "domestique et le disque de chiffrement sont accessibles."
                )
                return True
        if self._cible_est(cible, "globe", "globe terrestre") and verbe in {"inspecter", "tourner"}:
            self.dire("Une épingle marque Genève. Sur son pied, une plaque indique : « Voyage annulé — 1987 ».")
            self._decouvrir("annee_1987", "Le voyage des Valombre a été annulé en 1987.")
            return True
        if self._cible_est(cible, "livres", "rayonnages", "etagere") and verbe in {"inspecter", "fouiller", "lire"}:
            self.dire(
                "Les ouvrages traitent d'acoustique, de mémoire et de spiritualisme. Entre deux "
                "volumes, une ordonnance rappelle que seule Marguerite retirait les médicaments "
                "d'Éléonore à la pharmacie."
            )
            return True
        return False

    def _action_chapelle(self, verbe: str, cible: str, cmd: str, objet: str | None) -> bool:
        if self._cible_est(cible, "autel", "cavites", "sceaux"):
            if verbe in {"inspecter", "lire"}:
                self.dire("Trois cavités épousent exactement des disques de bronze, d'ivoire et de pierre verte.")
                self._decouvrir("trois_sceaux", "L'autel réclame trois sceaux : solaire, ivoire et végétal.")
                return True
            if verbe == "placer":
                requis = {"sceau_solaire", "sceau_ivoire", "sceau_lunaire"}
                manquants = requis.difference(self.inventaire)
                if manquants:
                    noms = ", ".join(self.objets[item].nom for item in sorted(manquants))
                    self.dire(f"Toutes les cavités ne peuvent pas être remplies. Il manque : {noms}.")
                    return False
                if self.drapeaux["crypt_open"]:
                    self.dire("Les sceaux sont déjà en place et la crypte est ouverte.")
                    return False
                for item in requis:
                    self._retirer_inventaire(item)
                self.drapeaux["crypt_open"] = True
                self.dire(
                    "Les trois sceaux s'enfoncent ensemble. Une vibration traverse la chapelle et la dalle funéraire\n"
                    "glisse, révélant un escalier de pierre sous l'autel."
                )
                self._succes("Les trois gardiens")
                return True
        if self._cible_est(cible, "vitrail", "fenetre") and verbe in {"inspecter", "lire"}:
            self.dire("Le vitrail représente le soleil levant. Sous l'image, un seul mot latin a été traduit à la main : « AUBE ».")
            self._decouvrir("mot_aube", "Le vitrail associe le mot AUBE à la délivrance.")
            return True
        if self._cible_est(cible, "dalle", "dalle funeraire", "crypte") and verbe in {"inspecter", "ouvrir", "soulever"}:
            if self.drapeaux["crypt_open"]:
                self.dire("La dalle est ouverte ; un escalier descend dans la crypte.")
            else:
                self.dire("La dalle n'a ni poignée ni joint apparent. L'autel semble commander son mécanisme.")
            return True
        return False

    def _action_palier(self, verbe: str, cible: str, cmd: str, objet: str | None) -> bool:
        if self._cible_est(cible, "portraits", "portrait", "famille") and verbe in {"inspecter", "lire"}:
            self.dire(
                "Les cartouches nomment Auguste, Mathilde, Damien et Éléonore. Damien est de loin "
                "le plus grand et partage les cheveux blonds de son père. Une photographie séparée "
                "montre Marguerite en uniforme vert, le pied gauche légèrement tourné. Le dernier "
                "portrait est daté du 15 octobre 1987 ; une horloge peinte indique 3 h 15."
            )
            self._ajouter_preuve(
                "profils_famille",
                "Les portraits confirment l'apparence de Damien et la boiterie de Marguerite.",
            )
            self._decouvrir("heure_315", "Le dernier portrait montre 3 h 15.")
            self._decouvrir("annee_1987", "Le dernier portrait date de 1987.")
            return True
        if self._cible_est(cible, "trappe", "grenier") and verbe in {"inspecter", "ouvrir"}:
            self.dire("La trappe du grenier est entrouverte. Une échelle escamotable permet de monter.")
            return True
        return False

    def _action_chambre_maitre(self, verbe: str, cible: str, cmd: str, objet: str | None) -> bool:
        if self._cible_est(cible, "coiffeuse", "lettres", "tiroirs") and verbe in {"inspecter", "ouvrir", "fouiller", "lire"}:
            if "lettre_mathilde" not in self.pieces["chambre_maitre"].objets and not self._possede("lettre_mathilde"):
                self._ajouter_dans_piece("chambre_maitre", "lettre_mathilde")
                self.dire(
                    "Derrière le fond du tiroir, vous trouvez une lettre inachevée de Mathilde. "
                    "Les autres fragments parlent aussi de disputes sur l'expérience sous la chapelle."
                )
            else:
                self.dire("Le double fond est ouvert. La lettre de Mathilde est la seule pièce encore exploitable.")
            self._decouvrir("dispute", "Mathilde voulait arrêter l'expérience d'Auguste.")
            return True
        if self._cible_est(cible, "armoire", "penderie") and verbe in {"ouvrir", "inspecter"}:
            self.dire(
                "Les vêtements sont prêts pour Genève. Une note de Mathilde précise : "
                "« Départ demain. Marguerite ne viendra pas. »"
            )
            return True
        if self._cible_est(cible, "lit", "matelas") and verbe in {"inspecter", "soulever", "fouiller"}:
            self.dire("Sous le matelas, des marques de griffes forment trois cercles concentriques.")
            return True
        return False

    def _action_chambre_enfant(self, verbe: str, cible: str, cmd: str, objet: str | None) -> bool:
        if self._cible_est(cible, "boite a musique", "musique", "boite musique"):
            if verbe in {"inspecter", "ouvrir", "ecouter"}:
                if self.drapeaux["music_box_repaired"]:
                    self.dire("La boîte joue quatre notes : do, mi, sol, ré. Les chiffres 1-3-5-2 sont gravés sous le cylindre.")
                    self._decouvrir("code_1352", "La mélodie do-mi-sol-ré correspond aux degrés 1-3-5-2.")
                else:
                    self.dire("La boîte à musique est intacte, mais sa manivelle manque.")
                return True
            if verbe == "utiliser" and objet == "manivelle_musique":
                if self.drapeaux["music_box_repaired"]:
                    self.dire("La manivelle est déjà fixée.")
                    return False
                self._retirer_inventaire("manivelle_musique")
                self.drapeaux["music_box_repaired"] = True
                self.dire("La manivelle s'emboîte. La boîte joue do-mi-sol-ré ; sous le cylindre apparaissent les chiffres 1-3-5-2.")
                self._decouvrir("code_1352", "La boîte à musique donne le code 1352.")
                return True
        if self._cible_est(cible, "coffre", "coffre a jouets", "molettes"):
            if verbe in {"inspecter", "ouvrir"}:
                if self.drapeaux["toy_chest_open"]:
                    self.dire("Le coffre à jouets est ouvert. Une enveloppe photographique était cachée sous la doublure.")
                else:
                    self.dire("Quatre molettes numérotées ferment le coffre. Un dessin de portée musicale est gravé sur le couvercle.")
                return True
        if verbe == "entrer":
            code = extraire_chiffres(cmd)
            if code == "1352":
                if self.drapeaux["toy_chest_open"]:
                    self.dire("Le coffre à jouets est déjà ouvert.")
                    return False
                self.drapeaux["toy_chest_open"] = True
                self._ajouter_dans_piece("chambre_enfant", "sceau_ivoire", "polaroid_flou")
                self.dire(
                    "Les molettes se libèrent. Sous une poupée reposent un sceau d'ivoire et une "
                    "photographie instantanée floue, encore glissée dans son enveloppe."
                )
                self._succes("La mélodie d'Éléonore")
                return True
            self.dire("Les molettes reviennent à zéro.")
            self._augmenter_tension(1)
            return True
        if self._cible_est(cible, "dessins", "dessin", "mur") and verbe in {"inspecter", "lire"}:
            self.dire(
                "Un dessin montre Éléonore plaçant trois soleils sur un autel tandis que son père "
                "tourne une grande roue sous terre. Dans un coin, une petite femme en vert verse "
                "des gouttes dans une tasse ; le dessin a été rageusement barré."
            )
            self._decouvrir("trois_sceaux", "Les dessins relient trois sceaux à l'autel de la chapelle.")
            return True
        return False

    def _action_salle_de_bain(self, verbe: str, cible: str, cmd: str, objet: str | None) -> bool:
        if self._cible_est(cible, "robinet", "eau", "baignoire") and verbe in {"ouvrir", "allumer", "tourner", "utiliser"}:
            if not self.drapeaux["bathroom_steam"]:
                self.drapeaux["bathroom_steam"] = True
                self.dire("Le robinet crache de l'eau brûlante. La vapeur recouvre lentement le miroir.")
            else:
                self.dire("La salle de bain est déjà pleine de vapeur.")
            return True
        if self._cible_est(cible, "miroir", "buée", "buee") and verbe in {"inspecter", "lire", "essuyer"}:
            if self.drapeaux["bathroom_steam"]:
                if not self.drapeaux["bathroom_clue"]:
                    self.drapeaux["bathroom_clue"] = True
                    self.dire("Sous la buée, un mot tracé autrefois avec du savon réapparaît : AUBE.")
                    self._decouvrir("mot_aube", "Le miroir révèle le mot AUBE.")
                    self._succes("Message dans la buée")
                else:
                    self.dire("Le mot AUBE reste visible dans la condensation.")
            else:
                self.dire("Le miroir est piqué, mais aucune inscription n'est visible à sec.")
            return True
        if self._cible_est(cible, "armoire pharmacie", "armoire", "pharmacie") and verbe in {"ouvrir", "inspecter", "fouiller"}:
            if "couteau_chirurgical" not in self.pieces["salle_de_bain"].objets and not self._possede("couteau_chirurgical"):
                self._ajouter_dans_piece("salle_de_bain", "couteau_chirurgical")
                self.dire(
                    "Derrière des flacons contre l'insomnie, vous trouvez un couteau chirurgical "
                    "enveloppé dans une serviette humide. Les initiales D.V. sont gravées sur le manche."
                )
            else:
                self.dire("L'armoire contient surtout des flacons vides ; l'emplacement du couteau est maintenant dégagé.")
            return True
        return False

    def _action_grenier(self, verbe: str, cible: str, cmd: str, objet: str | None) -> bool:
        if self._cible_est(cible, "malle", "coffre", "chiffres", "serrure"):
            if verbe in {"inspecter", "ouvrir"}:
                if self.drapeaux["attic_trunk_open"]:
                    self.dire("La malle est ouverte.")
                else:
                    self.dire("La malle demande une année à quatre chiffres. Une étiquette indique : « départ annulé ».")
                return True
        if verbe == "entrer":
            code = extraire_chiffres(cmd)
            if code == "1987":
                if self.drapeaux["attic_trunk_open"]:
                    self.dire("La malle est déjà ouverte.")
                    return False
                self.drapeaux["attic_trunk_open"] = True
                self._ajouter_dans_piece(
                    "grenier",
                    "fusible",
                    "manivelle_musique",
                    "cylindre_urgence",
                )
                self.dire(
                    "Le verrou cède sur 1987. La malle contient un fusible en porcelaine, une "
                    "petite manivelle d'ivoire et un cylindre d'enregistrement daté de 3 h 10."
                )
                return True
            self.dire("La malle reste fermée.")
            self._augmenter_tension(1)
            return True
        if self._cible_est(cible, "caisses", "draps", "meubles", "cylindres") and verbe in {"inspecter", "fouiller", "soulever"}:
            self.dire(
                "Vous trouvez des appareils d'enregistrement à cylindres, tous étiquetés avec "
                "les prénoms de la famille. Un phonographe mécanique semble encore fonctionnel."
            )
            self._decouvrir("enregistrements", "Auguste enregistrait les voix de chaque membre de la famille.")
            return True
        if self._cible_est(cible, "phonographe", "gramophone", "lecteur") and verbe in {"inspecter", "ouvrir", "utiliser", "ecouter"}:
            if not self._possede("cylindre_urgence"):
                self.dire("Le phonographe fonctionne, mais aucun cylindre exploitable n'est posé sur son axe.")
                return True
            if verbe in {"utiliser", "ecouter"}:
                return self._combinaison_speciale("cylindre_urgence", None, "phonographe")
            self.dire("Le phonographe peut lire le cylindre d'urgence. Essayez : utiliser cylindre sur phonographe.")
            return True
        if self._cible_est(cible, "cheval", "cheval a bascule") and verbe in {"inspecter", "pousser"}:
            self.dire("Le cheval se balance seul une fois. Sous sa selle : « do-mi-sol-ré ».")
            self._decouvrir("melodie", "Une suite de notes revient : do-mi-sol-ré.")
            return True
        return False

    def _action_cave(self, verbe: str, cible: str, cmd: str, objet: str | None) -> bool:
        if self._cible_est(cible, "tableau electrique", "panneau", "tableau", "capot"):
            if verbe in {"inspecter", "ouvrir"}:
                if not self.drapeaux["panel_open"]:
                    self.dire("Deux grosses vis maintiennent le capot. Derrière une fente, l'emplacement du fusible est vide.")
                elif not self.drapeaux["power_restored"]:
                    self.dire("Le panneau est ouvert ; il manque un fusible en porcelaine.")
                else:
                    self.dire("Le fusible est en place et le tableau alimente la radio.")
                return True
            if verbe == "utiliser" and objet == "tournevis":
                if self.drapeaux["panel_open"]:
                    self.dire("Le capot est déjà retiré.")
                    return False
                self.drapeaux["panel_open"] = True
                self.dire("Vous retirez les deux vis et ouvrez le tableau électrique.")
                return True
            if verbe == "utiliser" and objet == "fusible":
                if not self.drapeaux["panel_open"]:
                    self.dire("Le capot doit être retiré avant d'installer le fusible.")
                    return False
                if self.drapeaux["power_restored"]:
                    self.dire("Un fusible est déjà en place.")
                    return False
                self._retirer_inventaire("fusible")
                self.drapeaux["power_restored"] = True
                self.dire("Le fusible se visse dans son logement. Les câbles vibrent et la radio s'allume faiblement.")
                self._succes("Courant alternatif")
                return True
        if self._cible_est(cible, "radio", "poste"):
            if verbe in {"inspecter", "ecouter"}:
                if not self.drapeaux["power_restored"]:
                    self.dire("La radio n'est pas alimentée.")
                elif self.drapeaux["radio_code_known"]:
                    self.dire("Entre les parasites, la voix répète : « trois, sept, un, neuf ».")
                else:
                    self.dire("La radio est alimentée mais son bouton est sur arrêt.")
                return True
            if verbe == "allumer":
                if not self.drapeaux["power_restored"]:
                    self.dire("Rien ne se passe : le tableau électrique ne fournit aucun courant.")
                    return False
                if self.drapeaux["radio_code_known"]:
                    self.dire("La radio diffuse déjà son message en boucle.")
                    return False
                self.drapeaux["radio_code_known"] = True
                self.dire("Une voix d'enfant traverse les parasites : « trois... sept... un... neuf... Papa, ouvre la porte. »")
                self._decouvrir("code_3719", "La radio transmet le code 3719.")
                return True
        if self._cible_est(cible, "porte", "porte blindee", "clavier", "bureau"):
            if verbe in {"inspecter", "ouvrir"}:
                if self.drapeaux["office_unlocked"]:
                    self.dire("La porte blindée est ouverte sur le bureau secret.")
                else:
                    self.dire("Le clavier attend quatre chiffres. De petites empreintes d'enfant marquent les touches.")
                return True
        if verbe == "entrer":
            code = extraire_chiffres(cmd)
            if code == "3719":
                if self.drapeaux["office_unlocked"]:
                    self.dire("La porte est déjà ouverte.")
                    return False
                self.drapeaux["office_unlocked"] = True
                self.dire("Le verrou blindé se retire avec un bruit lourd. Le bureau d'Auguste est accessible à l'ouest.")
                self._succes("La voix dans les parasites")
                return True
            self.dire("Le clavier refuse la combinaison.")
            self._augmenter_tension(2)
            return True
        if self._cible_est(cible, "tonneaux", "tonneau") and verbe in {"inspecter", "fouiller", "pousser"}:
            self.dire("Les tonneaux sont vides. Derrière eux, le mur porte des marques de câbles arrachés en direction de la chapelle.")
            return True
        return False

    def _action_atelier(self, verbe: str, cible: str, cmd: str, objet: str | None) -> bool:
        if self._cible_est(cible, "plan", "plan technique", "machine", "schema") and verbe in {"inspecter", "lire"}:
            self.dire(
                "Le plan décrit une « chambre de résonance mnésique » sous la chapelle. Trois "
                "sceaux stabilisent l'accès ; un médaillon sert d'identifiant familial et un mot "
                "vocal commande l'arrêt d'urgence. En rouge : « Mise à la terre indispensable. "
                "Sans elle, la chambre capture au lieu d'enregistrer. »"
            )
            self._decouvrir("fonction_machine", "La machine exige trois sceaux, le médaillon familial et un mot d'arrêt.")
            return True
        if self._cible_est(cible, "cable", "cable arrache", "mise a terre", "fil", "conducteur") and verbe in {"inspecter", "fouiller", "lire"}:
            if "fragment_tissu_vert" not in self.pieces["atelier"].objets and not self._possede("fragment_tissu_vert"):
                self._ajouter_dans_piece("atelier", "fragment_tissu_vert")
                self.dire(
                    "Le câble n'a pas cédé seul : les torons portent une coupe nette, puis des "
                    "traces d'arrachement. Coincé dans le cuivre, un fragment de laine vert sombre "
                    "est encore visible."
                )
            else:
                self.dire("La coupe volontaire et l'arrachement du câble sont désormais clairement documentés.")
            return True
        if self._cible_est(cible, "etabli", "outils", "etau", "engrenages") and verbe in {"inspecter", "fouiller", "ouvrir"}:
            self.dire(
                "Les outils portent les initiales A.V. Une pince coupante manque de son support. "
                "Le tournevis plat, lui, est encore pris dans l'étau."
            )
            return True
        return False

    def _action_bureau_secret(self, verbe: str, cible: str, cmd: str, objet: str | None) -> bool:
        if self._cible_est(cible, "documents", "notes", "papiers", "bureau") and verbe in {"inspecter", "lire", "fouiller"}:
            self.dire(
                "Les documents révèlent qu'Auguste cherchait à conserver les souvenirs de sa "
                "fille malade. Les tests ont progressivement produit des voix autonomes. Une note "
                "de 2 h 35 indique : « tension anormale — vérifier la mise à la terre ». Une autre, "
                "écrite après coup : « J'ai déclenché à 3 h 15 malgré l'alarme. »"
            )
            self._decouvrir("verite_partielle", "Auguste construisait la machine pour préserver les souvenirs d'Éléonore.")
            return True
        if self._cible_est(cible, "coffre", "coffre mural", "petit coffre", "serrure"):
            if verbe in {"inspecter", "ouvrir"}:
                if self.drapeaux["office_safe_open"]:
                    self.dire("Le coffre mural est ouvert.")
                else:
                    self.dire("Le coffre mural demande quatre chiffres. Une horloge miniature est gravée sur sa porte.")
                return True
        if verbe == "entrer":
            code = extraire_chiffres(cmd)
            if code in {"315", "0315"}:
                if self.drapeaux["office_safe_open"]:
                    self.dire("Le coffre est déjà ouvert.")
                    return False
                self.drapeaux["office_safe_open"] = True
                self._ajouter_dans_piece("bureau_secret", "pieces_or")
                self.dire(
                    "Le coffre s'ouvre sur un rouleau de pièces anciennes et une photographie "
                    "intacte. Au dos, Auguste a écrit : « Marguerite refuse notre départ. »"
                )
                self._succes("Le vrai petit trésor")
                return True
            self.dire("Le coffre mural reste fermé.")
            return True
        if self._cible_est(cible, "lettre", "lettre chiffree") and verbe == "utiliser" and objet == "disque_chiffrement":
            return self._decoder_lettre()
        return False

    def _action_jardin(self, verbe: str, cible: str, cmd: str, objet: str | None) -> bool:
        if self._cible_est(cible, "terre", "terre remuee", "trou", "saule"):
            if verbe in {"inspecter", "fouiller"}:
                if self.drapeaux["buried_letter_found"]:
                    self.dire("Le trou près du saule a déjà été fouillé.")
                else:
                    self.dire("La terre a été retournée puis tassée. Une pelle permettrait de creuser proprement.")
                return True
            if verbe == "utiliser" and objet == "pelle":
                return self._creuser_jardin()
            if verbe == "creuser":
                return self._creuser_jardin()
        if verbe == "creuser":
            return self._creuser_jardin()
        if self._cible_est(cible, "traces", "traces de pas", "empreintes", "pas", "boue") and verbe in {"inspecter", "suivre", "lire"}:
            self.dire(
                "Les empreintes sont courtes et étroites. Le talon gauche marque plus profondément "
                "puis traîne sur quelques centimètres. Elles partent de la porte latérale de la "
                "chapelle, traversent la serre et gagnent une brèche dans le mur du domaine."
            )
            self._ajouter_preuve(
                "fuite_jardin",
                "Les empreintes d'une personne petite et boiteuse prouvent une fuite par la serre.",
            )
            return True
        if self._cible_est(cible, "statue", "ange") and verbe in {"inspecter", "lire"}:
            self.dire("La statue sans visage tient trois disques contre sa poitrine. Sur son socle : « Ce qui pousse se souvient. »")
            return True
        if self._cible_est(cible, "serre") and verbe in {"inspecter", "ouvrir"}:
            self.dire("La porte de la serre est déformée mais non verrouillée. Elle se trouve à l'ouest.")
            return True
        return False

    def _creuser_jardin(self) -> bool:
        if not self._possede("pelle"):
            self.dire("Vous ne pouvez pas creuser cette terre compacte à mains nues.")
            return False
        if self.drapeaux["buried_letter_found"]:
            self.dire("Vous avez déjà trouvé ce qui était enterré ici.")
            return False
        self.drapeaux["buried_letter_found"] = True
        self._ajouter_dans_piece("jardin", "lettre_enterree")
        self.dire("Après quelques pelletées, vous découvrez un paquet enveloppé de toile cirée : une lettre enterrée.")
        self._succes("La gouvernante savait")
        return True

    def _action_serre(self, verbe: str, cible: str, cmd: str, objet: str | None) -> bool:
        if self._cible_est(cible, "fleurs", "rose", "iris", "lys", "pavot", "jardinieres") and verbe in {"inspecter", "lire"}:
            self.dire("Chaque jardinière coulisse. Les quatre noms sont encore lisibles : ROSE, IRIS, LYS, PAVOT.")
            return True
        if verbe == "ordonner":
            sequence = normaliser(cmd)
            attendu = "rose iris lys pavot"
            positions = [sequence.find(mot) for mot in attendu.split()]
            if all(position >= 0 for position in positions) and positions == sorted(positions):
                if self.drapeaux["greenhouse_solved"]:
                    self.dire("Les fleurs sont déjà dans le bon ordre.")
                    return False
                self.drapeaux["greenhouse_solved"] = True
                self._ajouter_dans_piece("serre", "sceau_lunaire")
                self.dire("Les jardinières s'enclenchent de gauche à droite. Le socle s'ouvre et libère un sceau de pierre verte.")
                self._succes("L'herbier vivant")
                return True
            self.dire("Les rails se bloquent et les pots reviennent à leur position initiale.")
            self._augmenter_tension(1)
            return True
        if self._cible_est(cible, "socle", "pierre", "mecanisme") and verbe in {"inspecter", "ouvrir"}:
            if self.drapeaux["greenhouse_solved"]:
                self.dire("Le socle est ouvert.")
            else:
                self.dire("Quatre encoches relient le socle aux rails des jardinières. Leur ordre commande le verrou.")
            return True
        if self._cible_est(cible, "traces", "empreintes", "boue", "sortie", "breche") and verbe in {"inspecter", "suivre", "ouvrir"}:
            self.dire(
                "Les mêmes empreintes au talon gauche irrégulier traversent la serre. Un bouton "
                "recouvert de laine verte est coincé dans la brèche du mur extérieur."
            )
            self._ajouter_preuve(
                "fuite_jardin",
                "La piste d'une personne boiteuse en uniforme vert quitte le domaine par la serre.",
            )
            return True
        return False

    def _action_crypte(self, verbe: str, cible: str, cmd: str, objet: str | None) -> bool:
        if self._cible_est(cible, "machine", "empreinte", "centre"):
            if verbe in {"inspecter", "lire"}:
                if not self.drapeaux["medallion_inserted"]:
                    self.dire("La machine possède une empreinte ovale exactement adaptée au médaillon d'Éléonore.")
                elif not self.drapeaux["machine_unlocked"]:
                    self.dire("Des lettres tournent autour du médaillon. La machine attend un mot de sécurité.")
                elif self.drapeaux["machine_silenced"]:
                    self.dire(
                        "La machine est silencieuse. Le cylindre central conserve encore l'écho "
                        "des dernières secondes précédant l'activation."
                    )
                else:
                    self.dire(
                        "La machine est déverrouillée. Les voix murmurent votre nom. Le cylindre "
                        "central semble pouvoir restituer la scène enregistrée à 3 h 15."
                    )
                return True
            if verbe == "utiliser" and objet == "medaillon":
                if self.drapeaux["medallion_inserted"]:
                    self.dire("Le médaillon est déjà en place.")
                    return False
                self._retirer_inventaire("medaillon")
                self.drapeaux["medallion_inserted"] = True
                self.dire("Le médaillon s'emboîte. La machine s'éveille et dessine quatre emplacements de lettres dans l'air.")
                return True
        if verbe == "placer" and self._cible_est(cible, "medaillon", "empreinte", "machine"):
            if not self._possede("medaillon"):
                self.dire("Vous ne possédez pas le médaillon.")
                return False
            return self._action_crypte("utiliser", "machine", cmd, "medaillon")
        if verbe == "entrer":
            mot = normaliser(cmd)
            if not self.drapeaux["medallion_inserted"]:
                self.dire("La machine ne présente aucun clavier actif tant que l'empreinte centrale est vide.")
                return False
            if "aube" in mot:
                if self.drapeaux["machine_unlocked"]:
                    self.dire("Le mot AUBE a déjà été accepté.")
                    return False
                self.drapeaux["machine_unlocked"] = True
                self.dire(
                    "A-U-B-E. Les anneaux cessent de tourner. Les voix deviennent distinctes. "
                    "La machine peut maintenant restituer son dernier écho ; vous pourrez ensuite "
                    "l'arrêter, l'activer pleinement ou arracher son cœur précieux."
                )
                self._succes("Le mot du matin")
                return True
            self.dire("Les lettres se dispersent. Le mot est refusé.")
            self._augmenter_tension(4)
            return True
        if self._cible_est(cible, "echo", "enregistrement", "cylindre", "dernieres secondes", "voix") and verbe in {"inspecter", "lire", "ecouter", "utiliser"}:
            if not self.drapeaux["machine_unlocked"]:
                self.dire("Le cylindre reste muet tant que le médaillon et le mot de sécurité ne sont pas acceptés.")
                return False
            self._ajouter_preuve(
                "echo_315",
                "L'écho de la machine reconstitue l'agression et l'activation de 3 h 15.",
            )
            self.dire(
                "Le cylindre restitue une séquence brisée mais intelligible :\n"
                "  MATHILDE : « Marguerite... pourquoi ? »\n"
                "  DAMIEN : « Elle l'a poignardée ! Donnez-moi de quoi comprimer la plaie ! »\n"
                "  MARGUERITE : « Vous ne m'enlèverez pas cette famille. »\n"
                "  AUGUSTE : « La mise à la terre est coupée... mais je peux encore les conserver. »\n"
                "  DAMIEN : « Père, non ! »\n"
                "Puis l'horloge sonne 3 h 15 et Auguste abaisse la commande d'activation. Une "
                "décharge engloutit Auguste, Mathilde, Damien et Éléonore. Des pas courts et "
                "irréguliers s'éloignent vers le jardin."
            )
            return True
        if verbe == "arreter" and self._cible_est(cible, "machine", "tout", "mecanisme", ""):
            return self._fin_liberation()
        if verbe == "activer" and self._cible_est(cible, "machine", "tout", "mecanisme", ""):
            return self._fin_activation()
        if self._cible_est(cible, "tombeaux", "sarcophages") and verbe in {"inspecter", "ouvrir"}:
            self.dire("Les tombeaux sont vides. Les noms de la famille sont gravés sur les câbles, pas sur la pierre.")
            return True
        if self._cible_est(cible, "tresor", "coeur", "cylindre") and verbe in {"prendre", "arracher"}:
            return self._fin_cupidite()
        return False

    # ----- Fins ---------------------------------------------------------

    def _conditions_decision(self) -> bool:
        if not self.drapeaux["machine_unlocked"]:
            self.dire("La machine n'est pas encore déverrouillée. Il faut le médaillon et le mot de sécurité.")
            return False
        if self.drapeaux["machine_silenced"]:
            self.dire("La machine est déjà neutralisée. Votre prochaine étape est le rapport final.")
            return False
        return True

    def _fin_liberation(self) -> bool:
        if not self._conditions_decision():
            return False
        if self.drapeaux["machine_silenced"]:
            self.dire("La machine est déjà neutralisée. Il ne reste qu'à déposer votre rapport.")
            return False

        self.drapeaux["machine_silenced"] = True
        self.dire(
            self._couleur("\nLA MACHINE SE TAIT", Couleur.VERT + Couleur.GRAS)
            + "\nVous abaissez le coupe-circuit d'urgence. Le cylindre se fissure sans exploser ; "
            "les voix d'Auguste, Mathilde, Damien et Éléonore traversent la crypte comme un dernier "
            "souffle, puis s'éteignent.\n\n"
            "Toutes les horloges de la maison repartent à l'heure présente. La porte d'entrée est "
            "libérée. L'enquête, elle, n'est pas terminée : remontez au vestibule, consultez "
            "« rapport final » et déposez votre unique conclusion avec « conclure ... »."
        )
        self._succes("La maison rend le silence")
        return True

    def _fin_activation(self) -> bool:
        if not self._conditions_decision():
            return False
        self.drapeaux["game_complete"] = True
        self.termine = True
        self.fin = "activation"
        self.dire(
            self._couleur("\nFIN — LA MAISON SE SOUVIENT", Couleur.ROUGE + Couleur.GRAS)
            + "\nVous tournez la commande vers ACTIVATION. Les voix se condensent, prennent forme et ouvrent\n"
            "les yeux dans les miroirs de toute la demeure. Éléonore vous remercie, mais derrière sa voix\n"
            "parlent des centaines d'autres souvenirs affamés. Au matin, la maison semble vide. Votre propre\n"
            "nom vient pourtant de s'ajouter aux cylindres du grenier."
        )
        self.dire(self._bilan(len(self.preuves_enquete), 0))
        self._succes("Une voix de plus")
        return True

    def _fin_cupidite(self) -> bool:
        if not self._conditions_decision():
            return False
        self.drapeaux["game_complete"] = True
        self.termine = True
        self.fin = "cupidite"
        self.dire(
            self._couleur("\nFIN — LE PRIX DU SILENCE", Couleur.JAUNE + Couleur.GRAS)
            + "\nVous arrachez le cœur de cuivre et les pierres fixées autour du cylindre. La machine hurle\n"
            "avec les voix de la famille. Vous parvenez à quitter la maison avec une fortune, mais chaque\n"
            "appareil électrique que vous approchez répète désormais 3-7-1-9. Certaines nuits, une enfant\n"
            "vous demande encore d'ouvrir la porte."
        )
        self.dire(self._bilan(len(self.preuves_enquete), 1))
        self._succes("Tout ce qui brille")
        return True

    def _bilan(self, preuves: int, secrets: int) -> str:
        return (
            f"\nBilan : {self.tours} tours — {preuves} pièces à conviction — "
            f"{secrets}/4 secrets facultatifs — tension finale {self.tension}/100."
        )

    # ----- Inventaire, objectifs, journal, carte ------------------------

    def afficher_inventaire(self) -> str:
        if not self.inventaire:
            return "Votre inventaire est vide."
        lignes = ["Vous transportez :"]
        for identifiant in self.inventaire:
            lignes.append(f"  • {self.objets[identifiant].nom}")
        if self.drapeaux["flashlight_ready"] and "lampe_torche" in self.inventaire:
            lignes.append("  La lampe torche est chargée et allumée.")
        return "\n".join(lignes)

    def afficher_objectifs(self) -> str:
        f = self.drapeaux
        objectifs: list[tuple[bool, str]] = []

        # L'intrigue policière est l'objectif principal.
        obligatoires = self._preuves_obligatoires()
        preuves_ok = len(obligatoires.intersection(self.preuves_enquete))
        objectifs.append(
            (
                preuves_ok == len(obligatoires),
                f"Établir les preuves structurantes de la nuit ({preuves_ok}/{len(obligatoires)}).",
            )
        )
        objectifs.append(
            (
                "journal_falsifie" in self.preuves_enquete,
                "Identifier la page falsifiée du journal d'Éléonore.",
            )
        )
        objectifs.append(
            (
                "polaroid_detail" in self.preuves_enquete,
                "Déterminer ce que montre réellement la photographie floue.",
            )
        )
        objectifs.append(
            (
                "cylindre_dispute" in self.preuves_enquete,
                "Écouter l'enregistrement de 3 h 10.",
            )
        )
        objectifs.append(
            (
                "fuite_jardin" in self.preuves_enquete,
                "Identifier la voie de fuite utilisée après les faits.",
            )
        )

        # Les énigmes de la maison restent indispensables pour accéder aux preuves.
        objectifs.append((f["icebox_open"], "Ouvrir la glacière de la cuisine."))
        objectifs.append((f["clock_open"], "Ouvrir le compartiment de l'horloge."))
        objectifs.append((f["library_case_open"], "Ouvrir la vitrine de la bibliothèque."))
        objectifs.append((f["flashlight_ready"], "Rendre la lampe torche fonctionnelle."))
        objectifs.append((f["radio_code_known"], "Restaurer le courant et écouter la radio."))
        objectifs.append((f["office_unlocked"], "Ouvrir le bureau secret d'Auguste."))
        objectifs.append((f["letter_decoded"], "Décoder la lettre d'Auguste."))
        objectifs.append((f["garden_unlocked"], "Trouver un accès au jardin."))

        sceaux = all(
            self._possede(item) or f["crypt_open"]
            for item in ("sceau_solaire", "sceau_ivoire", "sceau_lunaire")
        )
        objectifs.append((sceaux, "Réunir les trois sceaux de l'autel."))
        objectifs.append((f["crypt_open"], "Ouvrir la crypte sous la chapelle."))
        objectifs.append((f["machine_unlocked"], "Déverrouiller la machine et écouter son dernier écho."))
        objectifs.append((f["machine_silenced"], "Neutraliser la machine sans détruire les preuves."))
        objectifs.append((f["game_complete"], "Déposer l'unique rapport final au vestibule."))

        lignes = ["ÉTAT DE L'ENQUÊTE"]
        for termine, texte in objectifs:
            symbole = "✓" if termine else "·"
            lignes.append(f"  {symbole} {texte}")
        return "\n".join(lignes)

    def afficher_journal(self) -> str:
        textes = {
            "code_7412": "La recette suggère la combinaison 7412.",
            "heure_315": "La maison insiste sur l'heure 3 h 15.",
            "annee_1987": "Le dernier jour des Valombre se situe en 1987.",
            "ordre_fleurs": "Ordre de l'herbier : rose, iris, lys, pavot.",
            "trois_sceaux": "L'autel de la chapelle exige trois sceaux de matières différentes.",
            "depart_manque": "Damien devait repartir le 16 octobre 1987, mais son billet n'a pas servi.",
            "dispute": "Mathilde voulait interrompre l'expérience d'Auguste et quitter le domaine.",
            "code_1352": "La mélodie do-mi-sol-ré donne 1-3-5-2.",
            "melodie": "Une suite de notes récurrente : do-mi-sol-ré.",
            "enregistrements": "Auguste enregistrait les voix de sa famille.",
            "code_3719": "La radio répète 3719.",
            "fonction_machine": "Trois sceaux ouvrent l'accès ; le médaillon et un mot commandent la machine.",
            "verite_partielle": "Auguste voulait préserver les souvenirs d'Éléonore.",
            "mot_aube": "Mot de sécurité : AUBE.",
            "verite_machine": "Auguste a activé la machine à 3 h 15 malgré le sabotage.",
            "temoignage_marguerite": "La lettre enterrée prétend innocenter Marguerite, mais sa chronologie est douteuse.",
        }
        lignes = ["JOURNAL DE TERRAIN"]
        if not self.indices_decouverts:
            lignes.append("  Aucun indice secondaire consigné.")
        else:
            for cle in self.indices_decouverts:
                lignes.append(f"  • {textes.get(cle, cle)}")

        lignes.append("")
        lignes.append(
            f"Preuves formelles : {len(self.preuves_enquete)}/{len(self._catalogue_preuves())} "
            "(tapez « preuves » pour les détails)."
        )
        return "\n".join(lignes)

    def afficher_succes(self) -> str:
        if not self.succes:
            return "Aucun succès débloqué pour le moment."
        return "Succès :\n" + "\n".join(f"  ★ {nom}" for nom in sorted(self.succes))

    def afficher_carte(self) -> str:
        def nom(room: str, largeur: int = 20) -> str:
            if room not in self.visitees:
                texte = "?"
            else:
                texte = self.pieces[room].nom
            if room == self.piece_actuelle:
                texte = f"[{texte}]"
            return texte[:largeur].center(largeur)

        lignes = [
            "CARTE — les pièces non visitées restent masquées",
            "",
            "ÉTAGE",
            f"{nom('chambre_maitre')} ─ {nom('palier')} ─ {nom('chambre_enfant')}",
            f"{' ' * 23}│",
            f"{' ' * 23}{nom('salle_de_bain')}",
            f"{' ' * 23}│",
            f"{' ' * 23}{nom('grenier')}",
            "",
            "REZ-DE-CHAUSSÉE",
            f"{nom('salle_a_manger')} ─ {nom('salon')} ─ {nom('couloir')} ─ {nom('chapelle')}",
            f"{' ' * 9}│{' ' * 13}│{' ' * 13}│",
            f"{nom('jardin')}   {nom('vestibule')}   {nom('bibliotheque')}   {nom('crypte')}",
            f"     │",
            f"{nom('serre')}",
            "",
            "SOUS-SOL",
            f"{nom('bureau_secret')} ─ {nom('cave')} ─ {nom('atelier')}",
        ]
        return "\n".join(lignes)

    # ----- Indices progressifs -----------------------------------------

    def donner_indice(self) -> str:
        cle, niveaux = self._indice_actuel()
        niveau = self.niveaux_indices.get(cle, 0)
        niveau = min(niveau, len(niveaux) - 1)
        self.niveaux_indices[cle] = niveau + 1
        return f"Indice {niveau + 1}/{len(niveaux)} — {niveaux[niveau]}"

    def _indice_actuel(self) -> tuple[str, list[str]]:
        f = self.drapeaux
        room = self.piece_actuelle
        if room == "cuisine" and not f["icebox_open"]:
            return "cuisine_7412", [
                "Lisez attentivement la note de recette.",
                "Les ingrédients sont absurdes ; gardez seulement leurs quantités.",
                "Entrez le code 7412 sur la glacière.",
            ]
        if room == "salon" and not f["clock_open"]:
            if not f["clock_wound"]:
                return "salon_remontage", [
                    "Inspectez l'horloge et cherchez une clé adaptée dans la maison.",
                    "La glacière de la cuisine cache une clé de remontage.",
                    "Utilisez la clé de remontage sur l'horloge.",
                ]
            return "salon_315", [
                "La bonne heure apparaît à plusieurs endroits du salon et du palier.",
                "La photographie familiale indique 3 h 15.",
                "Réglez l'horloge sur 3h15.",
            ]
        if room == "bibliotheque" and not f["library_case_open"]:
            return "bibliotheque_cle", [
                "La serrure porte un symbole de livre.",
                "Une clé portant le même symbole se cache dans l'horloge.",
                "Utilisez la clé en laiton sur la vitrine.",
            ]
        if room == "chambre_maitre" and not f["flashlight_ready"]:
            return "lampe", [
                "La lampe torche est vide.",
                "La glacière contient une pile sèche.",
                "Prenez la lampe et la pile, puis utilisez la pile sur la lampe.",
            ]
        if room == "grenier" and not f["attic_trunk_open"]:
            return "grenier_1987", [
                "La malle attend l'année du départ annulé.",
                "Le journal, les portraits et le globe donnent tous la même année.",
                "Entrez le code 1987.",
            ]
        if room == "chambre_enfant" and not f["toy_chest_open"]:
            if not f["music_box_repaired"]:
                return "musique_manivelle", [
                    "La boîte à musique a perdu une pièce.",
                    "Une petite manivelle se trouve dans la malle du grenier.",
                    "Utilisez la manivelle sur la boîte à musique.",
                ]
            return "musique_code", [
                "Écoutez la suite de notes et observez les chiffres sous le cylindre.",
                "Do-mi-sol-ré correspond aux degrés 1-3-5-2.",
                "Entrez le code 1352 sur le coffre à jouets.",
            ]
        if room == "couloir" and not f["cellar_revealed"]:
            return "couloir_tableau", [
                "Le papier peint autour du tableau montre qu'il a été déplacé.",
                "Inspectez ou écartez le tableau.",
                "Utilisez l'interrupteur caché derrière le tableau.",
            ]
        if room == "cave" and not f["radio_code_known"]:
            if not f["panel_open"]:
                return "cave_panneau", [
                    "Le tableau électrique est maintenu par des vis.",
                    "Un tournevis se trouve dans l'atelier à l'est.",
                    "Utilisez le tournevis sur le tableau électrique.",
                ]
            if not f["power_restored"]:
                return "cave_fusible", [
                    "Le logement vide attend une pièce en porcelaine.",
                    "La malle du grenier contient un fusible.",
                    "Utilisez le fusible sur le tableau électrique.",
                ]
            return "cave_radio", [
                "Le courant est revenu ; un appareil peut maintenant fonctionner.",
                "Allumez puis écoutez la radio.",
                "Le message donne le code de la porte blindée : 3719.",
            ]
        if room == "bureau_secret" and not f["letter_decoded"]:
            return "bureau_lettre", [
                "La dernière procédure d'Auguste se trouve dans la lettre chiffrée.",
                "La bibliothèque contient un disque de chiffrement.",
                "Prenez les deux objets puis utilisez le disque de chiffrement sur la lettre.",
            ]
        if room == "salle_a_manger" and not f["garden_unlocked"]:
            return "jardin_cle", [
                "La serrure des portes-fenêtres porte une feuille de lierre.",
                "Le bureau secret contient une longue clé portant le même motif.",
                "Utilisez la clé du jardin sur les portes-fenêtres.",
            ]
        if room == "serre" and not f["greenhouse_solved"]:
            return "serre_fleurs", [
                "Le journal d'Éléonore décrit une marche de quatre fleurs.",
                "La rose ouvre, puis l'iris, le lys et enfin le pavot.",
                "Tapez : ordonner fleurs rose iris lys pavot.",
            ]
        if room == "chapelle" and not f["crypt_open"]:
            return "chapelle_sceaux", [
                "Les trois cavités attendent les trois sceaux de la maison.",
                "Ils se trouvent dans l'horloge, le coffre à jouets et la serre.",
                "Avec les trois sceaux en inventaire, tapez : placer sceaux sur autel.",
            ]
        if room == "crypte" and not f["machine_unlocked"]:
            if not f["medallion_inserted"]:
                return "crypte_medaillon", [
                    "L'empreinte centrale a la forme d'un bijou familial.",
                    "Le médaillon d'Éléonore se trouve dans le bureau secret.",
                    "Utilisez le médaillon sur la machine.",
                ]
            return "crypte_aube", [
                "Le mot de sécurité apparaît dans la lettre décodée, le miroir ou le vitrail.",
                "Ce mot désigne le moment où la nuit prend fin.",
                "Entrez le mot AUBE.",
            ]
        # Indices propres à l'enquête principale, proposés après les énigmes locales.
        if room == "cuisine" and f["icebox_open"] and "digitaline" not in self.preuves_enquete:
            return "preuve_digitaline", [
                "La glacière ne contient pas seulement des objets mécaniques.",
                "Prenez puis inspectez le flacon pharmaceutique.",
                "Le nom du retrait et les symptômes d'Éléonore sont essentiels.",
            ]
        if room == "salle_a_manger" and f["dining_candles_lit"] and "sedatif_repas" not in self.preuves_enquete:
            return "preuve_repas", [
                "La lumière des bougies révèle quelque chose près de la cinquième chaise.",
                "Inspectez la table ou les verres, puis prenez l'ampoule.",
                "Inspectez l'ampoule de chloral.",
            ]
        if room == "bibliotheque" and f["library_case_open"] and "journal_falsifie" not in self.preuves_enquete:
            return "preuve_ecriture", [
                "La dernière page du journal n'a pas la même écriture.",
                "Prenez le journal et le registre domestique.",
                "Tapez : comparer journal avec registre.",
            ]
        if room == "chambre_enfant" and f["toy_chest_open"] and "polaroid_detail" not in self.preuves_enquete:
            return "preuve_photo", [
                "Le coffre contient une photographie trop floue pour conclure.",
                "Prenez la photographie et rendez la lampe fonctionnelle.",
                "Utilisez la lampe torche sur le polaroid.",
            ]
        if room == "salle_de_bain" and "couteau_damien" not in self.preuves_enquete:
            return "preuve_couteau", [
                "L'armoire à pharmacie n'a pas été fouillée correctement.",
                "Ouvrez l'armoire, prenez le couteau puis inspectez-le.",
                "Les fibres sur le manche comptent davantage que les initiales.",
            ]
        if room == "chambre_maitre" and "lettre_mathilde" not in self.preuves_enquete:
            return "preuve_mathilde", [
                "Le tiroir de la coiffeuse possède un double fond.",
                "Fouillez la coiffeuse puis prenez la lettre.",
                "Lisez ou inspectez la lettre de Mathilde.",
            ]
        if room == "atelier" and "sabotage_cable" not in self.preuves_enquete:
            return "preuve_sabotage", [
                "Le câble de mise à la terre n'a pas rompu naturellement.",
                "Inspectez le câble arraché et prenez le fragment de tissu.",
                "Inspectez le fragment vert.",
            ]
        if room == "grenier" and f["attic_trunk_open"] and "cylindre_dispute" not in self.preuves_enquete:
            return "preuve_cylindre", [
                "La malle contient un enregistrement daté de 3 h 10.",
                "Prenez le cylindre et inspectez le phonographe.",
                "Utilisez le cylindre sur le phonographe.",
            ]
        if room in {"jardin", "serre"} and "fuite_jardin" not in self.preuves_enquete:
            return "preuve_fuite", [
                "La boue conserve mieux les mouvements que les souvenirs.",
                "Inspectez les traces de pas ou les empreintes.",
                "Comparez leur taille et le talon gauche au signalement de Marguerite.",
            ]
        if room == "crypte" and f["machine_unlocked"] and "echo_315" not in self.preuves_enquete:
            return "preuve_echo", [
                "La machine conserve un dernier fragment de la scène.",
                "Inspectez ou écoutez l'écho du cylindre central.",
                "Tapez : écouter écho.",
            ]
        return "general", [
            "Consultez « preuves » et « rapport final » pour repérer les zones encore incomplètes.",
            "Une impression n'est pas une preuve : inspectez, éclairez et comparez.",
            "Explorez toutes les pièces avec « carte » puis relisez les signalements avec « suspects ».",
        ]

    # ----- Sauvegarde et réglages ---------------------------------------

    def sauvegarder(self, chemin_texte: str) -> str:
        chemin = Path(chemin_texte).expanduser()
        if not chemin.is_absolute():
            chemin = Path.cwd() / chemin
        donnees: dict[str, Any] = {
            "version": self.VERSION_SAUVEGARDE,
            "piece_actuelle": self.piece_actuelle,
            "inventaire": self.inventaire,
            "drapeaux": self.drapeaux,
            "indices": self.indices_decouverts,
            "preuves_enquete": self.preuves_enquete,
            "visitees": sorted(self.visitees),
            "niveaux_indices": self.niveaux_indices,
            "succes": sorted(self.succes),
            "tours": self.tours,
            "tension": self.tension,
            "termine": self.termine,
            "fin": self.fin,
            "pieces_objets": {room: piece.objets for room, piece in self.pieces.items()},
            "reglages": {
                "ascii_active": self.ascii_active,
                "ascii_couleur": self.ascii_couleur,
                "ascii_largeur": self.ascii_largeur,
                "couleur_prompt": self.couleur_prompt,
            },
        }
        try:
            chemin.parent.mkdir(parents=True, exist_ok=True)
            chemin.write_text(json.dumps(donnees, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as exc:
            return f"Impossible de sauvegarder : {exc}"
        return f"Partie sauvegardée dans : {chemin}"

    def charger(self, chemin_texte: str) -> str:
        chemin = Path(chemin_texte).expanduser()
        if not chemin.is_absolute():
            chemin = Path.cwd() / chemin
        try:
            donnees = json.loads(chemin.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return f"Impossible de charger la sauvegarde : {exc}"

        if donnees.get("version") != self.VERSION_SAUVEGARDE:
            return "Cette sauvegarde appartient à une version incompatible du jeu."
        try:
            piece_actuelle = donnees["piece_actuelle"]
            if piece_actuelle not in self.pieces:
                raise ValueError("pièce inconnue")
            self.piece_actuelle = piece_actuelle
            self.inventaire = [item for item in donnees["inventaire"] if item in self.objets]
            self.drapeaux.update({k: bool(v) for k, v in donnees["drapeaux"].items() if k in self.drapeaux})
            self.indices_decouverts = list(donnees.get("indices", []))
            catalogue_preuves = self._catalogue_preuves()
            self.preuves_enquete = [
                str(cle) for cle in donnees.get("preuves_enquete", [])
                if str(cle) in catalogue_preuves
            ]
            self.visitees = {room for room in donnees.get("visitees", []) if room in self.pieces}
            self.visitees.add(self.piece_actuelle)
            self.niveaux_indices = {str(k): int(v) for k, v in donnees.get("niveaux_indices", {}).items()}
            self.succes = set(donnees.get("succes", []))
            self.tours = int(donnees.get("tours", 0))
            self.tension = int(donnees.get("tension", 0))
            self.termine = bool(donnees.get("termine", False))
            self.fin = donnees.get("fin")
            for room, objets in donnees.get("pieces_objets", {}).items():
                if room in self.pieces:
                    self.pieces[room].objets = [item for item in objets if item in self.objets]
            reglages = donnees.get("reglages", {})
            self.ascii_active = bool(reglages.get("ascii_active", self.ascii_active))
            self.ascii_couleur = bool(reglages.get("ascii_couleur", self.ascii_couleur))
            self.ascii_largeur = max(36, min(120, int(reglages.get("ascii_largeur", self.ascii_largeur))))
            couleur_chargee = normaliser(
                str(reglages.get("couleur_prompt", self.couleur_prompt))
            )

            if couleur_chargee in COULEURS_PROMPT:
                self.couleur_prompt = couleur_chargee
        except (KeyError, TypeError, ValueError) as exc:
            return f"Sauvegarde invalide : {exc}"
        return f"Partie chargée depuis : {chemin}\n{self.decrire_piece()}"

    def invite_commande(self) -> str:
        code = COULEURS_PROMPT.get(self.couleur_prompt, Couleur.VERT)
        return self._couleur("Que faites-vous ? ", code + Couleur.GRAS)

    def regler_couleur_prompt(self, reste: str) -> str:
        option = normaliser(reste)

        if option in {"defaut", "défaut", "reset", "normal"}:
            option = "vert"

        if option not in COULEURS_PROMPT:
            couleurs = ", ".join(
                ["vert", "bleu", "violet", "rouge", "jaune", "cyan", "blanc", "gris"]
            )
            return f"Couleur inconnue. Couleurs disponibles : {couleurs}."

        self.couleur_prompt = option
        return self._couleur(
            f"Le prompt est maintenant {option}.",
            COULEURS_PROMPT[option] + Couleur.GRAS,
        )

    def regler_ascii(self, reste: str) -> str:
        option = normaliser(reste)
        if option in {"on", "oui", "activer", "active"}:
            self.ascii_active = True
            return "Illustrations ASCII activées."
        if option in {"off", "non", "desactiver", "desactive"}:
            self.ascii_active = False
            return "Illustrations ASCII désactivées."
        if option in {"couleur", "color"}:
            self.ascii_active = True
            self.ascii_couleur = True
            return "Rendu ASCII en niveaux de gris ANSI activé."
        if option in {"mono", "monochrome", "sans couleur"}:
            self.ascii_active = True
            self.ascii_couleur = False
            return "Rendu ASCII monochrome activé."
        etat = "activé" if self.ascii_active else "désactivé"
        mode = "couleur" if self.ascii_couleur else "monochrome"
        return f"ASCII {etat}, mode {mode}, largeur {self.ascii_largeur}."

    def regler_largeur(self, reste: str) -> str:
        chiffres = extraire_chiffres(reste)
        if not chiffres:
            return f"Largeur ASCII actuelle : {self.ascii_largeur}. Exemple : largeur 80"
        largeur = max(36, min(120, int(chiffres)))
        self.ascii_largeur = largeur
        return f"Largeur ASCII réglée sur {largeur} caractères."

    # ----- Atmosphère ---------------------------------------------------

    def _augmenter_tension(self, quantite: int) -> None:
        self.tension = min(100, self.tension + quantite)

    def _evenement_aleatoire(self) -> None:
        if not self.evenements_aleatoires or self.rng.random() > 0.28:
            return
        communs = [
            "Une horloge lointaine bat une fois, alors qu'aucune ne devrait fonctionner.",
            "Un courant d'air transporte une odeur de fleurs mouillées.",
            "Pendant une seconde, vos pas semblent accompagnés par ceux d'un enfant.",
            "Les boiseries craquent comme si la maison changeait de position autour de vous.",
            "Une voix très basse prononce un mot que vous ne parvenez pas à retenir.",
        ]
        specifiques = {
            "salon": "Le sofa s'affaisse légèrement, comme si quelqu'un venait de s'y asseoir.",
            "bibliotheque": "Un livre tombe tout seul, ouvert à une page blanche datée de demain.",
            "chambre_enfant": "La boîte à musique émet une note sans que personne la touche.",
            "cave": "La radio laisse échapper votre propre respiration avec une seconde de retard.",
            "jardin": "Les fleurs de la serre se tournent toutes vers vous malgré l'absence de soleil.",
            "crypte": "La lueur du cylindre pulse au même rythme que votre cœur.",
        }
        evenement = specifiques.get(self.piece_actuelle) if self.rng.random() < 0.45 else None
        evenement = evenement or self.rng.choice(communs)
        self._augmenter_tension(self.rng.randint(1, 3))
        self.dire(self._couleur(f"Événement : {evenement}", Couleur.FAIBLE))


# ---------------------------------------------------------------------------
# Boucle interactive
# ---------------------------------------------------------------------------


def main() -> None:
    jeu = Jeu()
    print_centre(jeu.introduction())
    print_centre(jeu.decrire_piece())

    while not jeu.termine:
        try:
            commande = input(f"\n{jeu.invite_commande()}")
        except (EOFError, KeyboardInterrupt):
            print_centre("\nVous interrompez l'exploration.")
            break
        resultat = jeu.executer(commande)
        if resultat:
            print_centre(resultat)

    # Une fin narrative peut encore ajouter un succès après avoir positionné
    # ``termine``. Le texte a déjà été affiché par la commande correspondante.


if __name__ == "__main__":
    main()

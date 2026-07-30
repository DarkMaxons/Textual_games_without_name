"""Tests de non-régression du moteur et de la solution principale."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from main import Jeu


SOLUTION_PRINCIPALE = [
    "aller nord",
    "lire note",
    "entrer code 7412",
    "prendre pile",
    "prendre cle de remontage",
    "aller sud",
    "utiliser cle de remontage sur horloge",
    "regler horloge 3h15",
    "prendre sceau solaire",
    "prendre cle en laiton",
    "aller est",
    "aller nord",
    "utiliser cle en laiton sur vitrine",
    "prendre journal",
    "prendre disque de chiffrement",
    "lire journal",
    "aller sud",
    "inspecter tableau",
    "utiliser interrupteur",
    "aller haut",
    "aller ouest",
    "prendre lampe",
    "utiliser pile sur lampe",
    "aller est",
    "aller haut",
    "entrer code 1927",
    "prendre fusible",
    "prendre manivelle",
    "aller bas",
    "aller est",
    "utiliser manivelle sur boite a musique",
    "entrer code 1352",
    "prendre sceau ivoire",
    "aller ouest",
    "aller bas",
    "aller bas",
    "aller est",
    "prendre tournevis",
    "aller ouest",
    "utiliser tournevis sur tableau electrique",
    "utiliser fusible sur tableau electrique",
    "allumer radio",
    "entrer code 3719",
    "aller ouest",
    "prendre medaillon",
    "prendre cle du jardin",
    "prendre lettre chiffree",
    "utiliser disque de chiffrement sur lettre chiffree",
    "aller est",
    "aller haut",
    "aller ouest",
    "aller ouest",
    "utiliser cle du jardin sur portes fenetres",
    "aller sud",
    "aller ouest",
    "ordonner fleurs rose iris lys pavot",
    "prendre sceau vegetal",
    "aller est",
    "aller nord",
    "aller est",
    "aller est",
    "aller est",
    "placer sceaux sur autel",
    "aller bas",
    "utiliser medaillon sur machine",
    "entrer mot aube",
    "arreter machine",
]


class TestMaisonAuxSecrets(unittest.TestCase):
    def setUp(self) -> None:
        self.jeu = Jeu(afficher_ascii=False, evenements_aleatoires=False, graine=123)

    def test_solution_principale_est_faisable(self) -> None:
        erreurs = []
        messages_problemes = (
            "aucun passage",
            "rien de pertinent",
            "ne possédez pas",
            "aucun effet utile",
            "code incorrect",
        )
        for commande in SOLUTION_PRINCIPALE:
            resultat = self.jeu.executer(commande).lower()
            if any(message in resultat for message in messages_problemes):
                erreurs.append((commande, resultat))
                break

        self.assertFalse(erreurs, erreurs[0] if erreurs else None)
        self.assertTrue(self.jeu.termine)
        self.assertEqual(self.jeu.fin, "liberation")
        self.assertTrue(self.jeu.drapeaux["game_complete"])

    def test_les_images_sont_associees_a_des_fichiers_distincts(self) -> None:
        chemins = {piece.image for piece in self.jeu.pieces.values()}
        self.assertEqual(len(chemins), len(self.jeu.pieces))
        for chemin in chemins:
            self.assertTrue(Path(chemin).exists(), chemin)

    def test_l_interrupteur_est_un_element_fixe_utilisable(self) -> None:
        self.jeu.piece_actuelle = "couloir"
        self.jeu.executer("inspecter tableau")
        resultat = self.jeu.executer("utiliser interrupteur")
        self.assertIn("escalier", resultat.lower())
        self.assertTrue(self.jeu.drapeaux["cellar_revealed"])

    def test_sauvegarde_et_chargement(self) -> None:
        self.jeu.executer("aller nord")
        self.jeu.executer("entrer code 7412")
        self.jeu.executer("prendre pile")

        with tempfile.TemporaryDirectory() as dossier:
            chemin = Path(dossier) / "partie.json"
            message = self.jeu.sauvegarder(str(chemin))
            self.assertIn("sauvegardée", message)
            donnees = json.loads(chemin.read_text(encoding="utf-8"))
            self.assertEqual(donnees["piece_actuelle"], "cuisine")

            autre = Jeu(afficher_ascii=False, evenements_aleatoires=False)
            message = autre.charger(str(chemin))
            self.assertIn("chargée", message)
            self.assertEqual(autre.piece_actuelle, "cuisine")
            self.assertIn("pile_seche", autre.inventaire)
            self.assertTrue(autre.drapeaux["icebox_open"])

    def test_indices_progressifs(self) -> None:
        self.jeu.piece_actuelle = "cuisine"
        premier = self.jeu.donner_indice()
        second = self.jeu.donner_indice()
        troisieme = self.jeu.donner_indice()
        self.assertIn("note", premier.lower())
        self.assertIn("quantités", second.lower())
        self.assertIn("7412", troisieme)


if __name__ == "__main__":
    unittest.main(verbosity=2)

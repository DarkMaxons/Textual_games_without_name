# Principales modifications

## Moteur

- Suppression de l'exécution de scripts de pièce avec `exec()`.
- Correction du double affichage du synopsis et de l'appel à une fonction `main()` inexistante.
- Résolution propre des directions, sans conflit entre `descendre`, `bas` et `sous-sol`.
- Ajout d'un parseur normalisé tolérant aux accents, apostrophes, articles et synonymes.
- Ajout d'états persistants pour chaque énigme, serrure, mécanisme et passage.
- Ajout des sauvegardes JSON, de la carte, des objectifs, du journal et des indices progressifs.

## Jeu

- Nouvelle intrigue cohérente centrée sur Auguste et Éléonore Valombre.
- 18 pièces, 19 objets, trois sceaux, plus d'une douzaine d'énigmes et trois fins.
- Énigmes interdépendantes avec plusieurs indices redondants pour éviter les blocages.
- Événements atmosphériques et jauge de tension non punitive.
- Secrets facultatifs, succès et bilan de fin.

## Affichage ASCII

- Un moteur générique remplace le script limité au salon.
- Chaque pièce pointe vers sa propre image.
- Largeur adaptée au terminal, cache de rendu et modes couleur ou monochrome.
- Vignette textuelle de secours si Pillow ou une image manque.
- Le fichier `piece_salon.py` reste compatible avec l'ancien appel `generate_ascii_image()`.

# La Maison aux Secrets

Aventure textuelle gothique en Python, construite à partir du prototype original. Le jeu mêle exploration, inventaire, énigmes en chaîne, indices progressifs, sauvegarde JSON et illustrations dynamiques converties en caractères ASCII.

## Lancer le jeu

### Sous Windows

1. Installez Python 3.10 ou une version plus récente.
2. Double-cliquez sur `installer.bat` une seule fois.
3. Double-cliquez ensuite sur `lancer_jeu.bat`.

Ou depuis PowerShell :

```powershell
py -m pip install -r requirements.txt
py main.py
```

### Sous Linux ou macOS

```bash
python3 -m pip install -r requirements.txt
python3 main.py
```

Pillow ne sert qu'au rendu des images. Sans Pillow, le jeu reste jouable et affiche des vignettes ASCII de secours.

## Contenu de cette version

- 18 pièces reliées de manière cohérente sur trois niveaux et dans le jardin.
- Une enquête complète autour de la disparition de la famille Valombre.
- 19 objets manipulables, dont des clés, documents, outils et trois sceaux.
- Plus d'une douzaine d'énigmes liées entre elles, sans connaissance extérieure nécessaire.
- Trois fins différentes selon la décision prise dans la crypte.
- Quatre secrets facultatifs et plusieurs succès.
- Un journal d'indices, des objectifs, une carte des pièces visitées et des indices progressifs.
- Sauvegarde et chargement au format JSON.
- Parseur tolérant aux accents, articles et synonymes courants.
- Une image différente pour chaque pièce, automatiquement convertie en ASCII selon la largeur du terminal.

## Commandes utiles

```text
aller nord
aller cuisine
regarder
inspecter horloge
prendre lampe
lire journal
utiliser pile sur lampe
combiner pile avec lampe
ouvrir placards
allumer radio
entrer code 7412
régler horloge 3h15
ordonner fleurs rose iris lys pavot
placer sceaux sur autel
```

Commandes d'assistance :

```text
inventaire
objectifs
journal
indice
carte
succès
sauvegarder
charger
ascii on
ascii off
ascii couleur
ascii mono
largeur 80
```

La commande `aide` affiche la liste directement dans le jeu.

## Illustrations ASCII par pièce

Chaque pièce possède son propre chemin d'image dans `main.py` et charge un fichier portant son identifiant dans :

```text
assets/rooms/
```

Exemples :

```text
assets/rooms/salon.png
assets/rooms/cuisine.png
assets/rooms/cave.png
assets/rooms/serre.png
assets/rooms/crypte.png
```

Pour remplacer une illustration, conservez simplement le même nom de fichier. Les formats horizontaux assez contrastés donnent généralement le meilleur résultat. Le cache du rendu est recréé au prochain lancement du jeu.

Le fichier `generate_assets.py` régénère les silhouettes de secours. Il conserve l'image source du salon dans `assets/rooms/salon_source.png`.

## Organisation du projet

```text
main.py                 moteur, monde, objets, énigmes et boucle du jeu
ascii_renderer.py       conversion générique PNG/JPG vers ASCII
piece_salon.py          compatibilité avec l'ancien script de conversion
generate_assets.py      génération des illustrations de secours
test_game.py            tests automatiques et parcours complet
assets/rooms/            une illustration distincte par pièce
legacy/                  sauvegarde des deux scripts d'origine
SOLUTION.md              solution complète avec spoilers
```

## Tester le projet

```bash
python -m unittest -v
```

Les tests vérifient notamment que la solution principale est entièrement jouable, que les images sont distinctes et présentes, que l'interrupteur fixe fonctionne, et que la sauvegarde peut être rechargée.

## Ajouter une pièce

1. Ajoutez une entrée `Piece(...)` dans `_creer_pieces()`.
2. Reliez-la avec une ou plusieurs `Sortie(...)`.
3. Ajoutez une méthode d'interaction ou complétez un gestionnaire existant.
4. Placez son image dans `assets/rooms/<identifiant>.png`.
5. Ajoutez son gestionnaire dans `action_contextuelle()` si la pièce possède des interactions spécifiques.

Le moteur sépare les objets portables, les éléments fixes du décor, les sorties et les drapeaux d'état. Cette structure permet d'ajouter des énigmes sans exécuter dynamiquement un script avec `exec()`.

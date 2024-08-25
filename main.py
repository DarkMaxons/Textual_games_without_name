import random
from PIL import Image
from piece_salon import *

def afficher_synopsis():
    # Codes de couleur ANSI
    couleur_rouge = "\033[91m"
    couleur_vert = "\033[92m"
    couleur_bleu = "\033[94m"
    couleur_jaune = "\033[93m"
    couleur_reset = "\033[0m"  # Réinitialiser la couleur

    synopsis = f"""
{couleur_vert}Bienvenue dans "La Maison aux Secrets" !{couleur_reset}

Vous êtes un détective à la recherche de réponses sur une ancienne famille mystérieusement disparue. 
Cette maison, longtemps abandonnée, cache de nombreux secrets que vous devrez découvrir en explorant chaque pièce, 
en récupérant des objets et en résolvant des énigmes. Votre mission est de découvrir le trésor caché quelque part 
dans le jardin, mais soyez prudent... chaque coin sombre peut révéler quelque chose d'inattendu.

{couleur_bleu}Commandes utilisables :{couleur_reset}
{couleur_jaune}- aller [direction]{couleur_reset} : Se déplacer dans une direction spécifique (ex: aller au nord).
{couleur_jaune}- prendre [objet]{couleur_reset} : Ramasser un objet et l'ajouter à votre inventaire (ex: prendre clé).
{couleur_jaune}- regarder [objet]{couleur_reset} : Examiner un objet dans votre inventaire (ex: regarder clé).
{couleur_jaune}- inspecter [objet]{couleur_reset} : Examiner un objet dans la pièce (ex: inspecter tableau).
{couleur_jaune}- lire [objet]{couleur_reset} : Lire un document ou un livre (ex: lire note).
{couleur_jaune}- ouvrir [objet]{couleur_reset} : Ouvrir un objet ou une porte (ex: ouvrir porte).
{couleur_jaune}- soulever [objet]{couleur_reset} : Soulever un objet (ex: soulever serpillère).
{couleur_jaune}- utiliser [objet]{couleur_reset} : Utiliser un objet de votre inventaire (ex: utiliser clé).
{couleur_jaune}- creuser avec [objet]{couleur_reset} : Creuser à l'aide d'un objet (ex: creuser avec pelle).
{couleur_jaune}- allumer [objet]{couleur_reset} : Allumer un appareil ou une source de lumière (ex: allumer radio).
{couleur_jaune}- entrer code [code]{couleur_reset} : Entrer un code dans un cadenas ou un mécanisme (ex: entrer code 3719).
{couleur_jaune}- inventaire{couleur_reset} : Afficher les objets que vous portez actuellement.
{couleur_jaune}- quitter{couleur_reset} : Quitter le jeu.

{couleur_rouge}Bonne chance, et souvenez-vous, la maison ne vous révèlera ses secrets que si vous persévérez !{couleur_reset}
    """
    print(synopsis)

# Appel de la fonction pour afficher le synopsis au début du jeu
afficher_synopsis()

# Dictionnaire global pour mapper les objets
objets_mapping = {
    "Une clé": "clé",
    "La clé": "clé",
    "Cette clé": "clé",
    "Le livre": "livre",
    "Un livre": "livre",
    "Ce livre": "livre",
    "Un couteau": "couteau",
    "Le couteau": "couteau",
    "Ce couteau": "couteau",
    "Une note": "note",
    "La note": "note",
    "Cette note": "note",
    "Une boîte": "boîte",
    "La boîte": "boîte",
    "Cette boîte": "boîte",
    "Une lampe torche": "lampe torche",
    "La lampe torche": "lampe torche",
    "Cette lampe torche": "lampe torche",
    "Une lanterne": "lanterne",
    "La lanterne": "lanterne",
    "Cette lanterne": "lanterne",
    "Un journal": "journal",
    "Le journal": "journal",
    "Ce journal": "journal",
    "Une clé ancienne": "clé ancienne",
    "La clé ancienne": "clé ancienne",
    "Cette clé ancienne": "clé ancienne",
    "Une pelle": "pelle",
    "La pelle": "pelle",
    "Cette pelle": "pelle",
    "Un coffre": "coffre",
    "Le coffre": "coffre",
    "Ce coffre": "coffre",
    "Une radio": "radio",
    "La radio": "radio",
    "Cette radio": "radio",
    "Un cadenas": "cadenas",
    "Le cadenas": "cadenas",
    "Ce cadenas": "cadenas"
}

class Piece:
    def __init__(self, nom, script_path, description_base, objets_descriptions=None, interactions=None):
        self.nom = nom
        self.description_base = description_base
        self.script_path = script_path
        self.pieces_connectees = {}
        self.objets = []
        self.objets_descriptions = objets_descriptions or {}
        self.interactions = interactions or {}

    def connecter_piece(self, piece, direction):
        self.pieces_connectees[direction] = piece

    def obtenir_piece_dans_direction(self, direction):
        return self.pieces_connectees.get(direction)

    def ajouter_objet(self, objet):
        self.objets.append(objet)

    def retirer_objet(self, nom_objet):
        objet = next((i for i in self.objets if i.nom.lower() == nom_objet.lower()), None)
        if objet:
            self.objets.remove(objet)
        return objet

    def decrire(self, inventaire):
        print(f"\n{self.nom}")
        description_complete = self.description_base

        for objet in self.objets:
            if objet.nom.lower() not in [i.nom.lower() for i in inventaire]:
                description_complete += "\n" + self.objets_descriptions.get(objet.nom.lower(), "")

        print(description_complete)

        self.executer_script()

    def executer_script(self):
        try:
            if self.script_path:
                exec(open(self.script_path).read())
            else:
                print("Aucun script disponible pour cette pièce.")
        except Exception as e:
            print(f"Erreur lors de l'exécution du script pour la pièce {self.nom}: {e}")

    def interagir(self, action):
        interaction = self.interactions.get(action)
        if interaction:
            print(interaction)
            return True
        else:
            return False

class Objet:
    def __init__(self, nom, description):
        self.nom = nom
        self.description = description

    def decrire(self):
        print(f"{self.nom} : {self.description}")

class Joueur:
    def __init__(self, piece_de_depart):
        self.piece_actuelle = piece_de_depart
        self.inventaire = []
        self.bureau_deverrouille = False  # Ajouter cet attribut pour suivre l'état de la porte

    def deplacer(self, direction):
        direction_mapping = {
            "au nord": "nord",
            "nord": "nord",
            "vers le nord": "nord",
            "vers nord": "nord",
            "aller nord": "nord",
            "au nord-est": "nord",
            "a nord": "nord",
            "a nord": "nord",

            "au sud": "sud",
            "sud": "sud",
            "vers le sud": "sud",
            "vers sud": "sud",
            "aller sud": "sud",
            "a sud": "sud",
            "au sud-ouest": "sud",

            "a l'est": "est",
            "à l'est": "est",
            "est": "est",
            "vers l'est": "est",
            "vers est": "est",
            "aller est": "est",
            "a est": "est",

            "a l'ouest": "ouest",
            "à l'ouest": "ouest",
            "ouest": "ouest",
            "vers l'ouest": "ouest",
            "vers ouest": "ouest",
            "aller ouest": "ouest",
            "a ouest": "ouest",

            "en haut": "haut",
            "haut": "haut",
            "monter": "haut",
            "monter en haut": "haut",
            "monter vers haut": "haut",
            "aller en haut": "haut",
            "a haut": "haut",

            "en bas": "bas",
            "bas": "bas",
            "descendre": "bas",
            "descendre en bas": "bas",
            "aller en bas": "bas",
            "vers en bas": "bas",
            "a bas": "bas",

            "au sous-sol": "sous-sol",
            "sous-sol": "sous-sol",
            "descendre": "sous-sol",
            "descendre en bas": "sous-sol",
            "descendre au sous sol": "sous-sol",
            "sous sol": "sous-sol",
            "aller au sous-sol": "sous-sol",
            "aller sous sol": "sous-sol",
            "vers sous-sol": "sous-sol",
            "descente sous-sol": "sous-sol",

            "a la porte": "porte",
            "à la porte": "porte",
            "porte": "porte",
            "a porte": "porte",
            "la porte": "porte",
            "vers la porte": "porte",
            "vers porte": "porte",
            "aller porte": "porte",
        }

        direction_simplifiee = direction_mapping.get(direction, direction)
        prochaine_piece = self.piece_actuelle.obtenir_piece_dans_direction(direction_simplifiee)

        if prochaine_piece == bureau and not self.bureau_deverrouille:
            print("La porte est verrouillée. Vous devez entrer le bon code pour l'ouvrir.")
            return

        if prochaine_piece:
            self.piece_actuelle = prochaine_piece
            self.piece_actuelle.decrire(self.inventaire)
            declencher_evenement_aleatoire()
        else:
            print("Vous vous cognez contre un mur. Il n'y a pas de chemin par là.")

    def prendre_objet(self, nom_objet):
        # Simplifier le nom de l'objet avant de l'utiliser
        nom_objet_simplifie = objets_mapping.get(nom_objet, nom_objet)

        # Utiliser le nom simplifié pour retirer l'objet de la pièce
        objet = self.piece_actuelle.retirer_objet(nom_objet_simplifie)
        if objet:
            self.inventaire.append(objet)
            print(f"Vous prenez soigneusement le {objet.nom} et le placez dans votre inventaire.")
        else:
            print("Vous cherchez, mais ne trouvez pas cet objet.")

    def regarder_objet(self, nom_objet):
        nom_objet_simplifie = objets_mapping.get(nom_objet, nom_objet)
        objet = next((i for i in self.inventaire if i.nom.lower() == nom_objet_simplifie.lower()), None)
        if objet:
            objet.decrire()
        else:
            print("Vous ne semblez pas avoir cet objet.")

    def interagir(self, action):
        action_split = action.split()
        if len(action_split) < 2:
            print("Action non valide.")
            return

        action_type = action_split[0]
        nom_objet = " ".join(action_split[1:])

        # Simplifier le nom de l'objet en utilisant objets_mapping
        nom_objet_simplifie = objets_mapping.get(nom_objet, nom_objet)

        objet = next((i for i in self.inventaire if i.nom.lower() == nom_objet_simplifie.lower()), None)
        if objet:
            if action_type == "lire":
                if objet.nom.lower() == "livre":
                    print(
                        "Le livre est rempli de notes griffonnées.\nUne phrase se démarque : 'Ne fais confiance qu'à la lumière du matin.'")
                elif objet.nom.lower() == "note":
                    print("La note indique un code : 7412.\nElle est signée 'M.'")
                else:
                    print(f"Vous ne pouvez pas {action_type} {objet.nom}.")
            elif action_type == "utiliser" and objet.nom.lower() == "clé":
                print("Vous utilisez la clé pour déverrouiller quelque chose.")
            else:
                print(f"Vous ne pouvez pas {action_type} {objet.nom}.")
        else:
            if action_type == "entrer" and "code" in nom_objet:
                if nom_objet == "code 3719":
                    print(self.piece_actuelle.interactions.get("entrer code 3719"))
                    self.bureau_deverrouille = True  # Déverrouille la porte
                else:
                    print(self.piece_actuelle.interactions.get("entrer code", "Code incorrect."))
            else:
                interaction_reussie = self.piece_actuelle.interagir(action)
                if not interaction_reussie:
                    print(f"Vous ne pouvez pas {action_type} {nom_objet_simplifie} ici.")


def declencher_evenement_aleatoire():
    evenements = [
        "Un courant d'air froid vous donne des frissons.",
        "Vous entendez un murmure lointain, mais ne pouvez pas comprendre les mots.",
        "Les lumières vacillent un instant, puis se stabilisent.",
        "Vous avez soudainement l'impression d'être observé.",
        "Une porte lointaine grince en s'ouvrant quelque part dans la maison."
    ]
    evenement = random.choice(evenements)
    if random.random() > 0.5:
        print(f"Événement : {evenement}")

# Définition des pièces du jeu
salon = Piece(
    "Salon",
    "piece_salon.py",
    "Le salon est une vaste pièce ornée de boiseries anciennes.\n"
    "Un grand sofa en cuir craquelé trône au centre, face à une cheminée en marbre ornée de sculptures complexes.\n"
    "Une grande horloge murale, arrêtée à 3h15, domine l'un des murs.\n",
    objets_descriptions={
        "clé": "Une clé rouillée est accrochée au-dessus de la cheminée, presque cachée parmi les sculptures.\n",
        "livre": "Un vieux livre, à la couverture usée, est posé sur la table basse en bois massif, couvert de poussière.\n"
    },
    interactions={
        "lire livre": "Le livre est rempli de notes griffonnées.\nUne phrase se démarque : 'Ne fais confiance qu'à la lumière du matin.'",
        "inspecter horloge": "L'horloge est arrêtée à 3h15.\nEn la secouant, vous entendez un cliquetis étrange à l'intérieur.",
        "inspecter cheminée": "Vous inspectez la cheminée et trouvez une ancienne inscription gravée,\nindiquant un passage secret quelque part dans la maison."
    }
)

cle = Objet("clé", "Une vieille clé rouillée, probablement inutilisée depuis des décennies.")
livre = Objet("livre", "Un vieux livre avec une couverture en cuir, rempli de notes cryptiques.")
salon.ajouter_objet(cle)
salon.ajouter_objet(livre)

cuisine = Piece(
    "Cuisine",
    "piece_salon.py",
    "La cuisine est déserte et plongée dans une semi-obscurité.\n"
    "Une vieille table en bois occupe le centre de la pièce, entourée de chaises désassorties.\n"
    "Un réfrigérateur verrouillé est adossé à un mur, et l'évier est rempli d'eau stagnante.\n",
    objets_descriptions={
        "couteau": "Un couteau rouillé, visiblement ancien, est posé sur la table, prêt à être utilisé.\n",
        "note": "Une note jaunie est collée sur le réfrigérateur, ses bords commencent à se détacher.\n"
    },
    interactions={
        "lire note": "La note indique un code : 7412.\nElle est signée 'M.'",
        "inspecter réfrigérateur": "Le réfrigérateur est verrouillé par une chaîne.\nLe code de la note pourrait peut-être le débloquer...",
        "ouvrir placards": "Les placards contiennent de la vaisselle poussiéreuse et un bocal de vieilles épices."
    }
)

couteau = Objet("couteau", "Un couteau rouillé, avec une lame encore tranchante malgré son âge.")
note = Objet("note", "Une vieille note avec un code mystérieux inscrit dessus.")
cuisine.ajouter_objet(couteau)
cuisine.ajouter_objet(note)

couloir = Piece(
    "Couloir",
    "piece_salon.py",
    "Le couloir est étroit et mal éclairé, ses murs ornés de papiers peints à motifs floraux fanés.\n"
    "Un escalier semble donner accès à l'étage. Il y a sûrement d'autres pièces à explorer par là...\n"
    "Un tableau inquiétant représentant un paysage sombre est accroché au mur,\nses yeux semblent vous suivre où que vous alliez.\n",
    objets_descriptions={
        "tableau": "Le tableau représente une scène nocturne,\nles yeux de la figure centrale semblent vivants.\n"
    },
    interactions={
        "inspecter tableau": "Le tableau représente un paysage obscur,\nmais les yeux de la figure centrale semblent vivants.\nDerrière le tableau, vous trouvez un interrupteur.",
        "utiliser interrupteur": "L'interrupteur ouvre un passage secret dans le mur,\nrévélant un escalier obscur donnant l'impression de s'enfoncer vers le bas...",
        "ouvrir porte": "La porte menant à la cave est verrouillée,\npeut-être qu'une clé pourrait l'ouvrir."
    }
)

cave = Piece(
    "Cave",
    "piece_salon.py",
    "La cave est sombre, humide et sent la moisissure.\n"
    "Des tonneaux de vin vides sont empilés dans un coin, mais il semble que quelque chose brille derrière l'un d'eux.\n"
    "Une vieille radio, recouverte de poussière, est posée sur une étagère branlante.\n"
    "Une vieille porte en bois massif se trouve à l'ouest, verrouillée par un énorme cadenas à code.\n",
    objets_descriptions={
        "boîte": "Une petite boîte métallique est cachée derrière l'un des tonneaux, à peine visible dans l'ombre.\n",
        "radio": "Une vieille radio est posée sur l'étagère, couverte de poussière.\n",
        "cadenas": "Un énorme cadenas à code verrouille la porte en bois massif à l'ouest.\n"
    },
    interactions={
        "allumer radio": "La radio grésille, puis vous entendez une voix lointaine : 'Le code du coffre est 3719.'",
        "inspecter tonneaux": "Les tonneaux semblent vides, mais l'un d'eux cache une petite boîte métallique.",
        "entrer code 3719": "Le cadenas s'ouvre avec un déclic, et la porte en bois massif s'ouvre lentement vers le bureau caché.",
        "entrer code": "Vous devez entrer la bonne combinaison pour déverrouiller le cadenas.",
        "inspecter cadenas": "Le cadenas a un clavier numérique où vous pouvez entrer une combinaison de quatre chiffres."
    }
)

boite = Objet("boîte", "Une petite boîte métallique verrouillée, recouverte de rouille.")
cave.ajouter_objet(boite)

chambre = Piece(
    "Chambre",
    "piece_salon.py",
    "La chambre est en désordre,\ncomme si elle avait été abandonnée en pleine nuit.\nLe lit est défait, ses draps épars.\n"
    "Une fenêtre brisée laisse entrer un faible courant d'air glacial.\n",
    objets_descriptions={
        "lampe torche": "Une lampe torche repose sur la table de chevet, prête à être utilisée.\n"
    },
    interactions={
        "ouvrir armoire": "Vous entrez le code '3719', et l'armoire s'ouvre en grinçant.\nÀ l'intérieur, vous trouvez une lampe torche.",
        "regarder par fenêtre": "À travers la fenêtre brisée,\nvous apercevez le jardin de la maison, envahi par les mauvaises herbes.\nQuelque chose scintille dans l'herbe."
    }
)

lampe_torche = Objet("lampe torche", "Une lampe torche, idéale pour explorer les endroits sombres.")
chambre.ajouter_objet(lampe_torche)

grenier = Piece(
    "Grenier",
    "piece_salon.py",
    "Le grenier est encombré de vieilles boîtes et couvert de toiles d'araignée.\nLa faible lumière qui filtre à travers les petites fenêtres poussiéreuses éclaire à peine la pièce.\n",
    objets_descriptions={
        "lanterne": "Une lanterne poussiéreuse repose sur une caisse,\nson huile presque épuisée.\n",
        "journal": "Un vieux journal intime dépasse d'une boîte,\nses pages jaunies semblent prêtes à se désintégrer.\n"
    },
    interactions={
        "lire journal": "Le journal raconte l'histoire de la famille qui vivait ici.\nLa dernière entrée parle de la découverte d'un 'trésor' dans le jardin.",
        "inspecter lanterne": "La lanterne est encore fonctionnelle,\nmais l'huile à l'intérieur est presque épuisée."
    }
)

lanterne = Objet("lanterne", "Une lanterne ancienne, avec très peu d'huile restante.")
journal = Objet("journal", "Un journal intime fragile appartenant à un ancien résident.")
grenier.ajouter_objet(lanterne)
grenier.ajouter_objet(journal)

bureau = Piece(
    "Bureau caché",
    "piece_salon.py",
    "Le bureau caché est une petite pièce exiguë,\nremplie de papiers jaunis et de vieux livres.\nL'air y est lourd, comme si personne n'y était entré depuis des années.\n"
    "Un vieux tapis gît au sol, mais l'un des coins est rabattu, laissant apparaître une charnière au sol.\n",
    objets_descriptions={
        "clé ancienne": "Une clé ancienne est posée sur le bureau,\nrecouverte d'une fine couche de poussière.\n"
    },
    interactions={
        "soulever tapis": "Le tapis, une fois soulevé, laisse apparaître une trappe tandis que la poussière s'évapore.",
        "ouvrir trappe": "La trappe s'ouvre avec difficulté,\nrévélant un passage secret vers le jardin.",
        "inspecter papiers": "Les papiers sont des notes sur les expériences occultes de l'ancien propriétaire de la maison."
    }
)

cle_bureau = Objet("clé ancienne", "Une clé ancienne, probablement utilisée pour un coffre ou une porte secrète.")
bureau.ajouter_objet(cle_bureau)

jardin = Piece(
    "Jardin",
    "piece_salon.py",
    "Le jardin est sauvage et envahi par les mauvaises herbes.\nUne légère brise fait bruisser les feuilles des arbres envahis de lierre.\n",
    objets_descriptions={
        "pelle": "Une pelle rouillée est plantée dans le sol,\nprès d'une zone où la terre semble avoir été récemment retournée.\n",
        "coffre": "Un vieux coffre, enterré sous la terre, semble attendre d'être découvert.\n"
    },
    interactions={
        "creuser avec pelle": "Vous creusez dans le sol et découvrez un coffre contenant un trésor !"
    }
)

pelle = Objet("pelle", "Une pelle rouillée, idéale pour creuser la terre.")
coffre = Objet("coffre", "Un vieux coffre, verrouillé, enterré sous la terre.")
jardin.ajouter_objet(pelle)
jardin.ajouter_objet(coffre)

# Connexion des pièces entre elles
cave.connecter_piece(bureau, "porte")
bureau.connecter_piece(cave,"porte")
bureau.connecter_piece(jardin, "sous-sol")

salon.connecter_piece(cuisine, "nord")
cuisine.connecter_piece(salon, "sud")
salon.connecter_piece(couloir, "est")
couloir.connecter_piece(salon, "ouest")
couloir.connecter_piece(cave, "bas")
cave.connecter_piece(couloir, "haut")
couloir.connecter_piece(chambre, "nord")
chambre.connecter_piece(couloir, "sud")
chambre.connecter_piece(grenier, "haut")
grenier.connecter_piece(chambre, "bas")

# Création du joueur
joueur = Joueur(salon)

# Boucle de jeu
while True:
    commande = input("\nQue voulez-vous faire ? ").lower().split()

    if len(commande) == 0:
        continue

    action = commande[0]

    if action == "aller":
        if len(commande) > 1:
            direction = " ".join(commande[1:])
            joueur.deplacer(direction)
        else:
            print("Aller où ?")
    elif action == "prendre":
        if len(commande) > 1:
            nom_objet = " ".join(commande[1:])
            joueur.prendre_objet(nom_objet)
        else:
            print("Prendre quoi ?")
    elif action == "regarder":
        if len(commande) > 1:
            nom_objet = " ".join(commande[1:])
            joueur.regarder_objet(nom_objet)
        else:
            joueur.piece_actuelle.decrire(joueur.inventaire)
    elif action == "inventaire":
        if joueur.inventaire:
            print("Vous transportez :")
            for objet in joueur.inventaire:
                print(f"- {objet.nom}")
        else:
            print("Vous ne transportez rien.")
    elif action in ["inspecter", "utiliser", "lire", "ouvrir", "creuser", "allumer", "entrer"]:
        if len(commande) > 1:
            action_avec_objet = " ".join(commande)
            joueur.interagir(action_avec_objet)
        else:
            print(f"Que voulez-vous {action} ?")
    elif action == "quitter":
        print("Vous décidez qu'il est temps de quitter cet endroit.\nMerci d'avoir joué !")
        break
    else:
        print("Vous murmurez quelque chose d'incompréhensible.\nRien ne se passe.")

if __name__ == "__main__":
    afficher_synopsis()
    main()


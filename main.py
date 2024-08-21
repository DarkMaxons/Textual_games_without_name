import random


class Piece:
    def __init__(self, nom, description_base, objets_descriptions, interactions=None):
        self.nom = nom
        self.description_base = description_base
        self.objets_descriptions = objets_descriptions
        self.pieces_connectees = {}
        self.objets = []
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
                description_complete += " " + self.objets_descriptions.get(objet.nom.lower(), "")

        print(description_complete)


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

    def deplacer(self, direction):
        prochaine_piece = self.piece_actuelle.obtenir_piece_dans_direction(direction)
        if prochaine_piece:
            self.piece_actuelle = prochaine_piece
            self.piece_actuelle.decrire(self.inventaire)
            declencher_evenement_aleatoire()
        else:
            print("Vous vous cognez contre un mur. Il n'y a pas de chemin par là.")

    def prendre_objet(self, nom_objet):
        objet = self.piece_actuelle.retirer_objet(nom_objet)
        if objet:
            self.inventaire.append(objet)
            print(f"Vous prenez soigneusement le {objet.nom} et le placez dans votre inventaire.")
        else:
            print("Vous cherchez, mais ne trouvez pas cet objet.")

    def regarder_objet(self, nom_objet):
        objet = next((i for i in self.inventaire if i.nom.lower() == nom_objet.lower()), None)
        if objet:
            objet.decrire()
        else:
            print("Vous ne semblez pas avoir cet objet.")

    def interagir(self, action):
        if not self.piece_actuelle.interagir(action):
            print("Vous ne pouvez pas faire cela pour l'instant.")


def declencher_evenement_aleatoire():
    evenements = [
        "Un courant d'air froid vous donne des frissons.",
        "Vous entendez un murmure lointain, mais ne pouvez pas comprendre les mots.",
        "Les lumières vacillent un instant, puis se stabilisent.",
        "Vous avez soudainement l'impression d'être observé.",
        "Une porte lointaine grince en s'ouvrant quelque part dans la maison."
    ]
    evenement = random.choice(evenements)
    if random.random() > 0.5:  # 50% de chance de déclencher un événement
        print(f"Événement : {evenement}")


def main():
    # Créer les pièces avec les interactions
    salon = Piece(
        "Salon",
        "Le salon est sombre et poussiéreux.",
        {
            "clé": " Une clé est accrochée au-dessus de la cheminée.",
            "livre": " Un vieux livre est posé sur la table basse."
        },
        interactions={
            "lire livre": "Le livre est rempli de notes griffonnées. Une phrase se démarque : 'Ne fais confiance qu'à la lumière du matin.'",
            "inspecter horloge": "L'horloge est arrêtée à 3h15. En la secouant, vous entendez un cliquetis étrange à l'intérieur.",
            "inspecter cheminée": "Vous inspectez la cheminée et trouvez une ancienne inscription gravée, indiquant un passage secret quelque part dans la maison."
        }
    )

    cle = Objet("clé", "Une vieille clé rouillée.")
    livre = Objet("livre", "Un vieux livre plein de notes en marge.")
    salon.ajouter_objet(cle)
    salon.ajouter_objet(livre)

    cuisine = Piece(
        "Cuisine",
        "La cuisine est déserte.",
        {
            "couteau": " Un couteau rouillé est posé sur la table.",
            "note": " Une note est collée au réfrigérateur."
        },
        interactions={
            "lire note": "La note indique un code : 7412. Elle est signée 'M.'",
            "inspecter réfrigérateur": "Le réfrigérateur est verrouillé par une chaîne. Le code de la note pourrait peut-être le débloquer...",
            "ouvrir placards": "Les placards contiennent de la vaisselle poussiéreuse et un bocal de vieilles épices."
        }
    )

    couteau = Objet("couteau", "Un vieux couteau rouillé, encore tranchant.")
    note = Objet("note", "Une note avec un code secret dessus.")
    cuisine.ajouter_objet(couteau)
    cuisine.ajouter_objet(note)

    couloir = Piece(
        "Couloir",
        "Le couloir est étroit et mal éclairé.",
        {
            "tableau": " Un tableau étrange semble vous suivre du regard."
        },
        interactions={
            "inspecter tableau": "Le tableau représente un paysage obscur, mais les yeux de la figure centrale semblent vivants. Derrière le tableau, vous trouvez un interrupteur.",
            "utiliser interrupteur": "L'interrupteur ouvre un passage secret dans le mur, révélant un escalier descendant vers le bureau caché.",
            "ouvrir porte": "La porte menant à la cave est verrouillée, peut-être qu'une clé pourrait l'ouvrir."
        }
    )

    cave = Piece(
        "Cave",
        "La cave est sombre et humide.",
        {
            "boîte": " Une petite boîte métallique est cachée derrière un tonneau."
        },
        interactions={
            "allumer radio": "La radio grésille, puis vous entendez une voix lointaine : 'Le code du coffre est 3719.'",
            "inspecter tonneaux": "Les tonneaux semblent vides, mais l'un d'eux cache une petite boîte métallique."
        }
    )

    boite = Objet("boîte", "Une petite boîte métallique verrouillée.")
    cave.ajouter_objet(boite)

    chambre = Piece(
        "Chambre",
        "La chambre est en désordre.",
        {
            "lampe torche": " Une lampe torche est posée sur la table de chevet."
        },
        interactions={
            "ouvrir armoire": "Vous entrez le code '3719', et l'armoire s'ouvre en grinçant. À l'intérieur, vous trouvez une lampe torche.",
            "regarder par fenêtre": "À travers la fenêtre brisée, vous apercevez le jardin de la maison, envahi par les mauvaises herbes. Quelque chose scintille dans l'herbe."
        }
    )

    lampe_torche = Objet("lampe torche", "Une lampe torche qui pourrait être utile dans des endroits sombres.")
    chambre.ajouter_objet(lampe_torche)

    grenier = Piece(
        "Grenier",
        "Le grenier est poussiéreux, rempli de vieilles boîtes.",
        {
            "lanterne": " Une lanterne est posée sur une caisse.",
            "journal": " Un journal intime dépasse d'une boîte ouverte."
        },
        interactions={
            "lire journal": "Le journal raconte l'histoire de la famille qui vivait ici. La dernière entrée parle de la découverte d'un 'trésor' dans le jardin.",
            "inspecter lanterne": "La lanterne est encore fonctionnelle, mais l'huile à l'intérieur est presque épuisée."
        }
    )

    lanterne = Objet("lanterne", "Une vieille lanterne presque vide.")
    journal = Objet("journal", "Un journal intime appartenant à un ancien résident.")
    grenier.ajouter_objet(lanterne)
    grenier.ajouter_objet(journal)

    # Ajout d'une nouvelle pièce : le bureau caché
    bureau = Piece(
        "Bureau caché",
        "Le bureau est petit et encombré de papiers.",
        {
            "clé ancienne": " Une clé ancienne est posée sur le bureau."
        },
        interactions={
            "ouvrir trappe": "La trappe s'ouvre avec difficulté, révélant un passage secret vers le jardin.",
            "inspecter papiers": "Les papiers sont des notes sur les expériences occultes de l'ancien propriétaire de la maison."
        }
    )

    cle_bureau = Objet("clé ancienne", "Une clé ancienne trouvée dans le bureau, peut-être pour un coffre.")
    bureau.ajouter_objet(cle_bureau)

    # Ajout de la pièce du jardin
    jardin = Piece(
        "Jardin",
        "Le jardin est envahi par les mauvaises herbes.",
        {
            "pelle": " Une pelle rouillée est plantée dans le sol.",
            "coffre": " Un coffre ancien est enterré sous la terre."
        },
        interactions={
            "creuser avec pelle": "Vous creusez dans le sol et découvrez un coffre contenant un trésor !"
        }
    )

    pelle = Objet("pelle", "Une pelle rouillée, mais encore utilisable.")
    coffre = Objet("coffre", "Un coffre ancien, verrouillé, enterré sous la terre.")
    jardin.ajouter_objet(pelle)
    jardin.ajouter_objet(coffre)

    # Connexions supplémentaires
    couloir.connecter_piece(bureau, "bas")
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

    # Créer le joueur
    joueur = Joueur(salon)

    # Boucle de jeu
    while True:
        commande = input("\nQue voulez-vous faire ? ").lower().split()

        if len(commande) == 0:
            continue

        action = commande[0]

        if action == "aller":
            if len(commande) > 1:
                direction = commande[1]
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
        elif action in ["inspecter", "utiliser", "lire", "ouvrir", "creuser"]:
            if len(commande) > 1:
                action_avec_objet = " ".join(commande)
                joueur.interagir(action_avec_objet)
            else:
                print(f"Que voulez-vous {action} ?")
        elif action == "quitter":
            print("Vous décidez qu'il est temps de quitter cet endroit. Merci d'avoir joué !")
            break
        else:
            print("Vous murmurez quelque chose d'incompréhensible. Rien ne se passe.")


if __name__ == "__main__":
    main()

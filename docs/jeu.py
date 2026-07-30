def main():
    print("=" * 50)
    print("       BIENVENUE DANS MON JEU")
    print("=" * 50)

    nom = input("\nQuel est ton nom ? ")

    print(f"\nBienvenue, {nom} !")

    choix = input(
        "\nTu arrives devant une maison abandonnée.\n"
        "1 - Entrer\n"
        "2 - Partir\n"
        "\nTon choix : "
    )

    if choix == "1":
        print("\nTu entres dans la maison...")
    elif choix == "2":
        print("\nTu décides de partir.")
    else:
        print("\nChoix incorrect.")


if __name__ == "__main__":
    main()

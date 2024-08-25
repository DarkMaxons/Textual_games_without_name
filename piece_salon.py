from PIL import Image

# Définir les variables globales ici si nécessaire
ASCII_GRAYSCALE = [
    "\033[38;5;232m",
    "\033[38;5;233m",
    "\033[38;5;234m",
    "\033[38;5;235m",
    "\033[38;5;236m",
    "\033[38;5;237m",
    "\033[38;5;238m",
    "\033[38;5;239m",
    "\033[38;5;240m",
    "\033[38;5;241m",
    "\033[38;5;242m",
    "\033[38;5;243m",
    "\033[38;5;244m",
    "\033[38;5;245m",
    "\033[38;5;246m",
    "\033[38;5;247m",
    "\033[38;5;248m",
    "\033[38;5;249m",
    "\033[38;5;250m",
    "\033[38;5;251m",
    "\033[38;5;252m",
    "\033[38;5;253m",
    "\033[38;5;254m",
    "\033[38;5;255m"
]
RESET_COLOR = "\033[0m"

ascii_chars = "@%#*+=-:. "

def pixel_to_ascii(pixel):
    gray_scale = pixel // 11
    ascii_char = ascii_chars[min(pixel // 25, len(ascii_chars) - 1)]
    return ASCII_GRAYSCALE[gray_scale] + ascii_char + RESET_COLOR

def generate_ascii_image(image_path):
    try:
        image = Image.open(image_path)

        # Redimensionner l'image
        new_width = 110
        width, height = image.size
        aspect_ratio = height / width
        new_height = int(aspect_ratio * new_width * 0.55)
        image = image.resize((new_width, new_height))

        # Convertir en niveaux de gris
        image = image.convert('L')

        # Mapper les pixels en caractères ASCII colorés
        pixels = image.getdata()
        ascii_str = [pixel_to_ascii(pixel) for pixel in pixels]

        # Former l'image ASCII finale
        ascii_img = ""
        for i in range(0, len(ascii_str), new_width):
            ascii_img += ''.join(ascii_str[i:i + new_width]) + "\n"

        print(ascii_img)
    except Exception as e:
        print(f"Erreur lors de l'exécution du script pour la pièce Salon: {e}")

if __name__ == "__main__":
    generate_ascii_image("salon.png")

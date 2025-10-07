import os
from PIL import Image
import zipfile


def convert_and_zip(input_folder, output_zip, webp_quality=80, resize=None):
    """
    Convierte todas las imágenes de input_folder a WebP, opcionalmente las redimensiona,
    y las guarda en un ZIP.

    Args:
        input_folder (str): Carpeta con las imágenes originales (PNG/JPEG).
        output_zip (str): Nombre del archivo ZIP de salida.
        webp_quality (int): Calidad de compresión WebP (0-100).
        resize (tuple o None): Redimensionar imágenes (width, height), o None para mantener tamaño.
    """
    temp_folder = "temp_webp"
    os.makedirs(temp_folder, exist_ok=True)

    print(f"Procesando imágenes en '{input_folder}'...")

    for filename in os.listdir(input_folder):
        if filename.lower().endswith((".png", ".jpg", ".jpeg")):
            input_path = os.path.join(input_folder, filename)
            output_path = os.path.join(temp_folder, os.path.splitext(filename)[0] + ".webp")

            img = Image.open(input_path)
            if resize:
                img = img.resize(resize)
            img.save(output_path, "WEBP", quality=webp_quality)

    # Crear ZIP
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for filename in os.listdir(temp_folder):
            zipf.write(os.path.join(temp_folder, filename), filename)

    # Limpiar carpeta temporal
    for f in os.listdir(temp_folder):
        os.remove(os.path.join(temp_folder, f))
    os.rmdir(temp_folder)

    print(f"¡Listo! ZIP creado: '{output_zip}'")


# ------------------ USO ------------------
input_dataset = "dataset_original"  # Carpeta con las imágenes
output_zip_file = "dataset_comprimido.zip"
convert_and_zip(input_dataset, output_zip_file, webp_quality=80, resize=None)

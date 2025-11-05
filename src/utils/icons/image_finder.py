import os

def find_image(name: str) -> str:
    """Finds a certain image in the icons folder

    Args:
        name (str): icon's name

    Returns:
        str: path to the icon image
    """
    icons_dir = os.path.join(os.path.dirname(__file__))
    return os.path.join(icons_dir, f"{name}.png")
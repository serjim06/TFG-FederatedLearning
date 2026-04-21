import os

def find_image(name: str) -> str:
    """
        Finds the path to an image file in the icons directory.

        Parameters
        ----------
        name : str
            The name of the image file to find.

        Returns
        -------
        str
            The path to the image file.
    """
    icons_dir = os.path.join(os.path.dirname(__file__))
    return os.path.join(icons_dir, f"{name}.png")
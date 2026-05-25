### Para ejecutar:

- ``git clone https://github.com/serjim06/TFG2025.git``
- ``cd TFG-FederatedLearning/``
- ``python -m venv .venv source``
- ``.venv/bin/activate``
- ``pip install -r requirements.txt``
- ``cp .env.example .env``
- ``python -m scripts.init_database [--nodes N] [--env RUTA]``
- ``python -m src.main``

Python Version: 3.12/3.13

Admin: 
    Usuario y contraseña del administrador en .env


En la carpeta ``samples`` se pueden encontrar modelos y datasets de ejemplo, dentro de una carpeta con el nombre del problema. 
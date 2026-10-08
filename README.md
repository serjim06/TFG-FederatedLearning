# Plataforma de Aprendizaje Federado para Datos Tabulares

[![CI](https://github.com/serjim06/TFG-FederatedLearning/actions/workflows/ci.yml/badge.svg)](https://github.com/serjim06/TFG-FederatedLearning/actions/workflows/ci.yml)
![Python](<https://img.shields.io/badge/python-3.12%20%7C%203.13-blue>)
![Flower](https://img.shields.io/badge/Flower-1.29-informational)
![PyTorch](https://img.shields.io/badge/PyTorch-MLP-ee4c2c)

Aplicación de escritorio para la gestión y ejecución de proyectos de **aprendizaje federado** sobre conjuntos de datos tabulares. Permite definir proyectos, asignar datasets a nodos, entrenar modelos de forma distribuida sin centralizar los datos, analizar métricas y generar informes.

Este repositorio contiene el código fuente del Trabajo de Fin de Grado (TFG) de **Sergio Jiménez Cubas**.

La memoria completa del TFG está disponible en [`docs/TFG_Sergio_Jimenez_Cubas.pdf`](docs/TFG_Sergio_Jimenez_Cubas.pdf).

## Índice

- [Características](#características)
- [Arquitectura](#arquitectura)
- [Requisitos](#requisitos)
- [Instalación](#instalación)
- [Uso](#uso)
- [Modelos y datasets de ejemplo](#modelos-y-datasets-de-ejemplo)
- [Pruebas](#pruebas)
- [Estructura del repositorio](#estructura-del-repositorio)
- [Autor](#autor)

---

## Características

- **Gestión de usuarios y roles**: registro, inicio de sesión, recuperación de contraseña mediante frase de recuperación y rol de administrador para la gestión de nodos y usuarios.
- **Proyectos de aprendizaje federado**: clasificación y regresión sobre datos tabulares con modelos PyTorch definidos por el usuario.
- **Estrategias de agregación**:
  - `FedAvg` — media ponderada por número de muestras.
  - `FedMedian` — mediana coordenada a coordenada.
  - `SCAFFOLD` — corrección de deriva mediante variables de control.
  - `SSFed` — ponderación basada en significancia.
- **Simulación federada** con [Flower](https://flower.ai/) y Ray, lanzada directamente desde la interfaz.
- **Validación de resultados**: los resultados de cada entrenamiento quedan pendientes de confirmación antes de consolidarse.
- **Métricas e informes**: visualización de la evolución por ronda y exportación de informes en PDF.
- **Predicción** con el modelo global entrenado.

## Arquitectura

El proyecto sigue una organización por capas inspirada en la arquitectura hexagonal:

| Capa                 | Ubicación                           | Responsabilidad                                                        |
| -------------------- | ------------------------------------ | ---------------------------------------------------------------------- |
| Presentación        | `src/gui/`                         | Interfaz gráfica en Tkinter.                                          |
| Aplicación          | `src/application/`                 | Casos de uso, servicios y contratos de repositorio.                    |
| Infraestructura      | `src/infrastructure/`, `src/db/` | Implementación de repositorios sobre SQLite.                          |
| Aprendizaje federado | `src/federated/`, `src/models/`  | Orquestación de Flower, estrategias de agregación y lógica de nodo. |
| Transversal          | `src/security/`, `src/utils/`    | Hashing de contraseñas, políticas de acceso y utilidades.            |

Flujo típico: **GUI → caso de uso → servicio / repositorio → persistencia o simulación federada**.

**Stack tecnológico**: Python · Tkinter · SQLite · PyTorch · Flower · Ray · scikit-learn · Matplotlib · ReportLab · pytest.

## Requisitos

- Python **3.12** o **3.13**
- Tkinter (incluido en la mayoría de distribuciones de Python; en Linux puede requerir el paquete `python3-tk`)
- Git

## Instalación

1. **Clonar el repositorio**

   ```bash
   git clone https://github.com/serjim06/TFG-FederatedLearning.git
   cd TFG-FederatedLearning
   ```
2. **Crear y activar un entorno virtual**

   Linux / macOS:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

   Windows (PowerShell):

   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```
3. **Instalar las dependencias**

   ```bash
   pip install -r requirements.txt
   ```
4. **Configurar las variables de entorno**

   ```bash
   cp .env.example .env
   ```

   Edite `.env` para definir las credenciales del administrador:

   | Variable                 | Descripción                                          |
   | ------------------------ | ----------------------------------------------------- |
   | `ADMIN_USERNAME`       | Nombre de usuario del administrador.                  |
   | `ADMIN_PASSWORD`       | Contraseña del administrador.                        |
   | `ADMIN_RECOVER_PHRASE` | Frase de recuperación de la cuenta de administrador. |


   > **Importante:** cambie los valores por defecto antes de utilizar la aplicación fuera de un entorno de pruebas.
   >
5. **Inicializar la base de datos**

   ```bash
   python -m scripts.init_database [--nodes N] [--env RUTA]
   ```

   Crea `database/database.db`, el usuario administrador y `N` nodos (3 por defecto).

## Uso

```bash
python -m src.main
```

1. Registre un usuario nuevo en el sistema.
2. Cree un proyecto indicando el modelo (fichero `.py`), el tipo de problema, la estrategia de agregación y sus parámetros.
3. Asigne un dataset CSV a cada nodo participante.
4. Lance el entrenamiento federado indicando el número de rondas.
5. Revise y confirme los resultados, consulte las métricas, genere el informe PDF o realice predicciones.

## Modelos y datasets de ejemplo

El directorio `samples/` incluye material listo para probar la aplicación:

- `samples/sample_models/` — modelos MLP de ejemplo. Cada modelo hereda de `BaseModel` (`src/models/base_model.py`) e implementa `load_model()` y `get_features()`.
- `samples/sample_datasets/` — datasets ya particionados por cliente, agrupados por problema:

| Problema                                  | Tipo           | Modelo                             |
| ----------------------------------------- | -------------- | ---------------------------------- |
| Iris                                      | Clasificación | `iris_mlp_model.py`              |
| Calidad del aire                          | Regresión     | `air_quality_mlp_model.py`       |
| Consumo energético de electrodomésticos | Regresión     | `appliances_energy_mlp_model.py` |
| Salarios                                  | Regresión     | `job_salary_mlp_model.py`        |
| Hojas sintéticas                         | Clasificación | `synthetic_leaf_mlp_model.py`    |

Los scripts de `scripts/` permiten regenerar algunas de estas particiones.

## Pruebas

```bash
pip install -e ".[test]"
python -m pytest
```

Las pruebas se ejecutan automáticamente en cada *push* y *pull request* mediante GitHub Actions.

## Estructura del repositorio

```
├── src/
│   ├── main.py              # Punto de entrada de la aplicación
│   ├── gui/                 # Pantallas Tkinter
│   ├── application/         # Casos de uso, servicios, DTOs e interfaces
│   ├── infrastructure/      # Repositorios SQLite
│   ├── db/                  # Conexión a la base de datos
│   ├── federated/           # Servidor Flower y estrategias de agregación
│   ├── models/              # Modelo base y lógica de nodo
│   ├── security/            # Gestión de contraseñas
│   └── utils/               # Utilidades e iconos
├── scripts/                 # Inicialización de BD y particionado de datos
├── samples/                 # Modelos y datasets de ejemplo
├── tests/                   # Pruebas automatizadas (pytest)
├── requirements.txt
└── pyproject.toml
```

## Autor

**Sergio Jiménez Cubas** — Trabajo de Fin de Grado, 2025.

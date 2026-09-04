"""Verifica que el entorno pueda ejecutar el pipeline antes de lanzarlo.

Comprueba versión de Python, presencia y versión de cada dependencia, las
incompatibilidades conocidas (np.trapz en numpy 2.x, scipy.optimize.milp),
la existencia de los datos de entrada y la escritura del backend Agg.

    python check_entorno.py

Devuelve código 0 si todo está en orden, 1 si hay algún problema.
"""
import importlib
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# (módulo importable, nombre para el mensaje, versión mínima recomendada)
DEPENDENCIAS = [
    ("numpy", "numpy", (1, 24)),
    ("pandas", "pandas", (1, 5)),
    ("networkx", "networkx", (3, 0)),
    ("scipy", "scipy", (1, 9)),
    ("sklearn", "scikit-learn", (1, 2)),
    ("matplotlib", "matplotlib", (3, 6)),
]

ARCHIVOS_DATOS = [
    "data/red_ucuenca.graphml",
    "data/red_ucuenca_nodes.csv",
    "data/red_ucuenca_edges.csv",
]

problemas = []
avisos = []


def tupla_version(texto):
    partes = []
    for trozo in texto.split(".")[:3]:
        digitos = "".join(c for c in trozo if c.isdigit())
        partes.append(int(digitos) if digitos else 0)
    return tuple(partes)


print("=" * 62)
print("VERIFICACIÓN DE ENTORNO — red_ucuenca_redes_complejas")
print("=" * 62)

# --- Python ---------------------------------------------------------------
print(f"\nPython {sys.version.split()[0]}  ({sys.executable})")
if sys.version_info < (3, 9):
    problemas.append(f"Python {sys.version_info.major}.{sys.version_info.minor} "
                     "es demasiado antiguo; se requiere 3.9 o superior.")

# --- Dependencias ---------------------------------------------------------
print("\nDependencias:")
versiones = {}
for modulo, nombre, minima in DEPENDENCIAS:
    try:
        mod = importlib.import_module(modulo)
    except ImportError:
        print(f"  {nombre:<15} FALTA")
        problemas.append(f"Falta el paquete '{nombre}'. Instala con: pip install -r requirements.txt")
        continue

    version = getattr(mod, "__version__", "desconocida")
    versiones[modulo] = version
    marca = "ok"
    if version != "desconocida" and tupla_version(version) < minima:
        marca = "ANTIGUA"
        esperada = ".".join(str(x) for x in minima)
        problemas.append(f"{nombre} {version} es anterior a la mínima {esperada}.")
    print(f"  {nombre:<15} {version:<12} {marca}")

# --- Incompatibilidades conocidas ----------------------------------------
print("\nIncompatibilidades conocidas:")

if "numpy" in versiones:
    import numpy as np
    if hasattr(np, "trapz"):
        print("  np.trapz            disponible")
    else:
        print("  np.trapz            NO EXISTE")
        problemas.append(
            "numpy >= 2.0 eliminó np.trapz, usado en 08_p8_percolacion.py y "
            "11_p11_rediseno.py. Instala numpy<2.0 o cambia esas llamadas a np.trapezoid."
        )

if "scipy" in versiones:
    try:
        from scipy.optimize import milp  # noqa: F401
        print("  scipy.optimize.milp disponible")
    except ImportError:
        print("  scipy.optimize.milp NO EXISTE")
        problemas.append(
            "scipy.optimize.milp no está disponible (requiere scipy >= 1.9). "
            "07_p7_localizacion.py no podrá resolver los MILP exactos."
        )

# --- Backend de matplotlib ------------------------------------------------
if "matplotlib" in versiones:
    os.environ.setdefault("MPLBACKEND", "Agg")
    import matplotlib
    backend = matplotlib.get_backend()
    print(f"  backend matplotlib  {backend}")
    if backend.lower() != "agg":
        avisos.append(
            f"El backend activo es '{backend}'. run_all.py fuerza Agg en los "
            "subprocesos, pero si ejecutas un script suelto en una máquina sin "
            "entorno gráfico puede fallar."
        )

# --- Datos de entrada -----------------------------------------------------
print("\nDatos de entrada:")
for relativo in ARCHIVOS_DATOS:
    ruta = ROOT / relativo
    if ruta.is_file():
        print(f"  {relativo:<32} {ruta.stat().st_size:>9,} bytes")
    else:
        print(f"  {relativo:<32} FALTA")
        problemas.append(f"No se encuentra {relativo}. ¿Está el directorio data/ en el repositorio?")

# --- Estructura del proyecto ---------------------------------------------
print("\nEstructura:")
for relativo in ["scripts", "src", "src/red.py"]:
    ruta = ROOT / relativo
    estado = "ok" if ruta.exists() else "FALTA"
    print(f"  {relativo:<32} {estado}")
    if not ruta.exists():
        problemas.append(f"No se encuentra {relativo}.")

n_scripts = len(list((ROOT / "scripts").glob("[0-9]*.py"))) if (ROOT / "scripts").is_dir() else 0
print(f"  scripts numerados                {n_scripts}")
if n_scripts != 12:
    avisos.append(f"Se esperaban 12 scripts numerados (00 a 11) y hay {n_scripts}.")

# --- Resultado ------------------------------------------------------------
print("\n" + "=" * 62)
for aviso in avisos:
    print(f"[AVISO] {aviso}")
if problemas:
    for p in problemas:
        print(f"[ERROR] {p}")
    print(f"\n{len(problemas)} problema(s). El pipeline probablemente NO correrá.")
    raise SystemExit(1)

print("Entorno OK. Puedes ejecutar:  python run_all.py")

"""Ejecuta todo el pipeline (scripts/00 a scripts/11) en orden numérico.

Los scripts posteriores (p.ej. 10_p10_ranking_criticos.py) leen resultados
que generan scripts anteriores (06 y 09) desde resultados/tablas/, así que
deben correr en este orden y no en paralelo. Uso:

    python run_all.py

El entorno de los subprocesos fija MPLBACKEND=Agg para que las figuras se
generen sin necesidad de un servidor gráfico (máquina limpia, CI, SSH), y
PYTHONUNBUFFERED=1 para que la salida de cada script aparezca en tiempo real
cuando se redirige a un archivo de log.
"""
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIR_SCRIPTS = ROOT / "scripts"
PATRON = re.compile(r"^(\d+)_")

# Se hereda el entorno del proceso padre y se añaden las dos variables que
# garantizan reproducibilidad de las figuras y orden del log.
ENTORNO = {**os.environ, "MPLBACKEND": "Agg", "PYTHONUNBUFFERED": "1"}


def etapas():
    """Devuelve los scripts con prefijo numérico, ordenados por ese número."""
    encontrados = []
    for ruta in DIR_SCRIPTS.glob("*.py"):
        m = PATRON.match(ruta.name)
        if m:
            encontrados.append((int(m.group(1)), ruta))
    return [ruta for _, ruta in sorted(encontrados)]


def main():
    if not DIR_SCRIPTS.is_dir():
        sys.exit(f"[ERROR] No existe el directorio {DIR_SCRIPTS}")

    scripts = etapas()
    if not scripts:
        sys.exit(f"[ERROR] No se encontraron scripts numerados en {DIR_SCRIPTS}")

    print(f"Python  : {sys.version.split()[0]} ({sys.executable})")
    print(f"Etapas  : {len(scripts)}")
    print(f"Backend : Agg", flush=True)

    inicio_total = time.perf_counter()
    for script in scripts:
        print(f"\n=== Ejecutando {script.name} ===", flush=True)
        inicio = time.perf_counter()
        resultado = subprocess.run(
            [sys.executable, str(script)],
            cwd=ROOT,
            env=ENTORNO,
        )
        duracion = time.perf_counter() - inicio

        if resultado.returncode != 0:
            print(
                f"\n[ERROR] {script.name} terminó con código "
                f"{resultado.returncode}. Pipeline detenido.",
                flush=True,
            )
            sys.exit(resultado.returncode)
        print(f"--- {script.name} OK ({duracion:.1f}s)", flush=True)

    total = time.perf_counter() - inicio_total
    print(
        f"\nPipeline completo en {total:.1f}s: todas las tablas y figuras "
        "se regeneraron en resultados/.",
        flush=True,
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("\n[INTERRUMPIDO] Pipeline cancelado por el usuario.")
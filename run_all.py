"""Ejecuta todo el pipeline (scripts/00 a scripts/11) en orden numérico.

Los scripts posteriores (p.ej. 10_p10_ranking_criticos.py) leen resultados
que generan scripts anteriores (06 y 09) desde resultados/tablas/, así que
deben correr en este orden y no en paralelo. Uso:

    python run_all.py
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCRIPTS = sorted((ROOT / "scripts").glob("*.py"))

for script in SCRIPTS:
    print(f"\n=== Ejecutando {script.name} ===")
    resultado = subprocess.run([sys.executable, str(script)], cwd=ROOT)
    if resultado.returncode != 0:
        print(f"\n[ERROR] {script.name} terminó con código {resultado.returncode}. Pipeline detenido.")
        sys.exit(resultado.returncode)

print("\nPipeline completo: todas las tablas y figuras se regeneraron en resultados/.")

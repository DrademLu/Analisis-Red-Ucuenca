from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.red import cargar_datos, verificar_pipeline

OUT = ROOT / "resultados" / "tablas"
OUT.mkdir(parents=True, exist_ok=True)

G, nodos, aristas = cargar_datos()
tabla, ok = verificar_pipeline(G, nodos, aristas)

print(tabla.to_string(index=False))
tabla.to_csv(OUT / "00_verificacion_pipeline.csv", index=False)

if not ok:
    raise SystemExit("La verificación del pipeline FALLÓ.")

print("\nVERIFICACIÓN COMPLETA: todos los valores coinciden con el Anexo A.")

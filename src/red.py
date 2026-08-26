from pathlib import Path
import networkx as nx
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

def cargar_datos():
    """Carga GraphML y CSV y devuelve (G, nodos, aristas)."""
    G = nx.Graph(nx.read_graphml(DATA / "red_ucuenca.graphml"))
    nodos = pd.read_csv(DATA / "red_ucuenca_nodes.csv")
    aristas = pd.read_csv(DATA / "red_ucuenca_edges.csv")
    return G, nodos, aristas

def verificar_pipeline(G, nodos, aristas):
    """Verifica los valores publicados en el Anexo A del proyecto."""
    esperados = {
        "nodos": 177,
        "aristas": 209,
        "componentes": 1,
        "densidad_redondeada": 0.0134,
        "capa_acceso": 132,
        "capa_agregacion": 27,
        "capa_core": 5,
        "capa_wan": 11,
        "capa_interconexion": 2,
        "rol_principal": 157,
        "rol_wan": 32,
        "rol_respaldo": 12,
        "rol_secundario": 5,
        "rol_inferido": 3,
        "trafico_definido": 170,
        "capacidad_definida": 28,
    }

    obtenidos = {
        "nodos": G.number_of_nodes(),
        "aristas": G.number_of_edges(),
        "componentes": nx.number_connected_components(G),
        "densidad_redondeada": round(nx.density(G), 4),
        "capa_acceso": int((nodos["capa"] == "acceso").sum()),
        "capa_agregacion": int((nodos["capa"] == "agregacion").sum()),
        "capa_core": int((nodos["capa"] == "core").sum()),
        "capa_wan": int((nodos["capa"] == "wan").sum()),
        "capa_interconexion": int((nodos["capa"] == "interconexion").sum()),
        "rol_principal": int((aristas["rol"] == "principal").sum()),
        "rol_wan": int((aristas["rol"] == "wan").sum()),
        "rol_respaldo": int((aristas["rol"] == "respaldo").sum()),
        "rol_secundario": int((aristas["rol"] == "secundario").sum()),
        "rol_inferido": int((aristas["rol"] == "inferido").sum()),
        "trafico_definido": int(aristas["trafico_mbps"].notna().sum()),
        "capacidad_definida": int(aristas["capacidad_mbps"].notna().sum()),
    }

    filas = []
    ok_total = True
    for clave, esperado in esperados.items():
        obtenido = obtenidos[clave]
        ok = obtenido == esperado
        ok_total &= ok
        filas.append({
            "propiedad": clave,
            "esperado": esperado,
            "obtenido": obtenido,
            "estado": "OK" if ok else "ERROR",
        })

    return pd.DataFrame(filas), ok_total

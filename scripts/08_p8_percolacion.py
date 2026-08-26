from pathlib import Path
import random
import time
import math

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
TAB = ROOT / 'resultados' / 'tablas'
FIG = ROOT / 'resultados' / 'figuras'
TAB.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)

SEED = 2026
N_RANDOM = 100
N_NULL = 100
EFF_FRACS = np.linspace(0.0, 0.95, 20)

G0 = nx.Graph(nx.read_graphml(DATA / 'red_ucuenca.graphml'))
N0, M0 = G0.number_of_nodes(), G0.number_of_edges()
assert (N0, M0) == (177, 209)
assert nx.is_connected(G0)


def component_stats(G):
    if G.number_of_nodes() == 0:
        return 0, 0
    sizes = sorted((len(c) for c in nx.connected_components(G)), reverse=True)
    return sizes[0], sizes[1] if len(sizes) > 1 else 0


def global_efficiency_current(G):
    n = G.number_of_nodes()
    if n < 2:
        return 0.0
    total = 0.0
    # Suma sobre pares ordenados implícitamente: por cada fuente se suman destinos.
    for source, dist in nx.all_pairs_shortest_path_length(G):
        total += sum(1.0 / d for target, d in dist.items() if target != source and d > 0)
    return total / (n * (n - 1))


def estimate_threshold(df):
    fc = float(df.loc[df['S2'].idxmax(), 'f'])
    half = df[df['S'] <= 0.5]
    f50 = float(half.iloc[0]['f']) if len(half) else 1.0
    return fc, f50


def node_curve_from_order(G, order):
    """Curva exacta S/S2 mediante unión-búsqueda en orden inverso."""
    nodes = list(G.nodes())
    idx = {n: i for i, n in enumerate(nodes)}
    n = len(nodes)
    parent = np.full(n, -1, dtype=int)
    size = np.zeros(n, dtype=int)
    active = np.zeros(n, dtype=bool)

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra == rb:
            return
        if size[ra] < size[rb]:
            ra, rb = rb, ra
        parent[rb] = ra
        size[ra] += size[rb]

    S = np.zeros(n + 1)
    S2 = np.zeros(n + 1)

    # k=n removidos: ningún nodo activo.
    S[n] = 0.0
    S2[n] = 0.0

    # Al añadir order[k] en reversa queda exactamente k nodos removidos.
    for k in range(n - 1, -1, -1):
        node = order[k]
        i = idx[node]
        active[i] = True
        parent[i] = i
        size[i] = 1

        for nbr in G.neighbors(node):
            j = idx[nbr]
            if active[j]:
                union(i, j)

        comps = sorted(
            (int(size[r]) for r in range(n) if active[r] and parent[r] == r),
            reverse=True,
        )
        S[k] = (comps[0] if comps else 0) / N0
        S2[k] = (comps[1] if len(comps) > 1 else 0) / N0

    return pd.DataFrame({
        'removed': np.arange(n + 1),
        'f': np.arange(n + 1) / N0,
        'S': S,
        'S2': S2,
    })


def edge_curve_from_order(G, order):
    """Curva exacta S/S2 de enlaces mediante unión-búsqueda en reversa."""
    nodes = list(G.nodes())
    idx = {n: i for i, n in enumerate(nodes)}
    n = len(nodes)
    m = len(order)
    parent = np.arange(n, dtype=int)
    size = np.ones(n, dtype=int)

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra == rb:
            return
        if size[ra] < size[rb]:
            ra, rb = rb, ra
        parent[rb] = ra
        size[ra] += size[rb]

    S = np.zeros(m + 1)
    S2 = np.zeros(m + 1)

    # k=m: no quedan aristas, todos los nodos son componentes unitarias.
    S[m] = 1.0 / N0 if n else 0.0
    S2[m] = 1.0 / N0 if n > 1 else 0.0

    for k in range(m - 1, -1, -1):
        u, v = order[k]
        union(idx[u], idx[v])
        comps = sorted(
            (int(size[r]) for r in range(n) if parent[r] == r),
            reverse=True,
        )
        S[k] = (comps[0] if comps else 0) / N0
        S2[k] = (comps[1] if len(comps) > 1 else 0) / N0

    return pd.DataFrame({
        'removed': np.arange(m + 1),
        'f': np.arange(m + 1) / M0,
        'S': S,
        'S2': S2,
    })

def node_degree_order(G):
    deg = dict(G.degree())
    return sorted(G.nodes(), key=lambda n: (-deg[n], str(n)))


def node_bet_order(G):
    b = nx.betweenness_centrality(G, normalized=True)
    return sorted(G.nodes(), key=lambda n: (-b[n], str(n)))


def node_adaptive_bet_order(G):
    H = G.copy(); order = []
    while H.number_of_nodes():
        if H.number_of_nodes() == 1:
            chosen = next(iter(H.nodes()))
        else:
            b = nx.betweenness_centrality(H, normalized=True)
            chosen = min(H.nodes(), key=lambda n: (-b[n], str(n)))
        order.append(chosen)
        H.remove_node(chosen)
    return order


def edge_bet_order(G):
    eb = nx.edge_betweenness_centrality(G, normalized=True)
    return [e for e, _ in sorted(eb.items(), key=lambda kv: (-kv[1], tuple(sorted(map(str, kv[0])))))]


def edge_adaptive_bet_order(G):
    H = G.copy(); order = []
    while H.number_of_edges():
        eb = nx.edge_betweenness_centrality(H, normalized=True)
        chosen = min(eb, key=lambda e: (-eb[e], tuple(sorted(map(str, e)))))
        order.append(chosen)
        H.remove_edge(*chosen)
    return order


def bridge_first_order(G):
    bridges = {tuple(sorted(map(str, e))) for e in nx.bridges(G)}
    eb = nx.edge_betweenness_centrality(G, normalized=True)
    return sorted(
        G.edges(),
        key=lambda e: (
            0 if tuple(sorted(map(str, e))) in bridges else 1,
            -eb[e],
            tuple(sorted(map(str, e)))
        )
    )


def efficiency_nodes(G, order, fractions):
    requested = sorted(set(min(N0, int(round(f * N0))) for f in fractions) | {0})
    H = G.copy(); out = []
    req = set(requested)
    for k in range(N0 + 1):
        if k in req:
            out.append((k, k / N0, global_efficiency_current(H)))
        if k < N0:
            H.remove_node(order[k])
    return pd.DataFrame(out, columns=['removed','f','E'])


def efficiency_edges(G, order, fractions):
    requested = sorted(set(min(M0, int(round(f * M0))) for f in fractions) | {0})
    H = G.copy(); out = []
    req = set(requested)
    for k in range(M0 + 1):
        if k in req:
            out.append((k, k / M0, global_efficiency_current(H)))
        if k < M0 and H.has_edge(*order[k]):
            H.remove_edge(*order[k])
    return pd.DataFrame(out, columns=['removed','f','E'])


print('1/7 Órdenes dirigidos de nodos...')
t0 = time.perf_counter()
degree_order = node_degree_order(G0)
bet_order = node_bet_order(G0)
adapt_bet_order = node_adaptive_bet_order(G0)
print(f'   listo en {time.perf_counter()-t0:.2f}s')

node_curves = {
    'grado_desc': node_curve_from_order(G0, degree_order),
    'intermediacion_desc': node_curve_from_order(G0, bet_order),
    'intermediacion_adaptativa': node_curve_from_order(G0, adapt_bet_order),
}
for k, df in node_curves.items():
    df.to_csv(TAB / f'02_nodos_{k}.csv', index=False)

print('2/7 100 realizaciones aleatorias de nodos...')
rng = random.Random(SEED)
random_node_orders = []
arrS = np.zeros((N_RANDOM, N0+1)); arrS2 = np.zeros((N_RANDOM, N0+1))
for r in range(N_RANDOM):
    order = list(G0.nodes()); rng.shuffle(order); random_node_orders.append(order)
    c = node_curve_from_order(G0, order)
    arrS[r] = c['S']; arrS2[r] = c['S2']
random_node_df = pd.DataFrame({
    'removed': np.arange(N0+1), 'f': np.arange(N0+1)/N0,
    'S_mean': arrS.mean(0), 'S_std': arrS.std(0, ddof=1),
    'S2_mean': arrS2.mean(0), 'S2_std': arrS2.std(0, ddof=1)
})
random_node_df.to_csv(TAB/'01_nodos_aleatorio_100_realizaciones.csv', index=False)

thresholds = []
rt = random_node_df.rename(columns={'S_mean':'S','S2_mean':'S2'})
fc, f50 = estimate_threshold(rt)
thresholds.append(('nodos','aleatorio_media_100',fc,f50))
for name, df in node_curves.items():
    fc, f50 = estimate_threshold(df); thresholds.append(('nodos',name,fc,f50))

print('3/7 Eficiencia en percolación de nodos...')
E0 = global_efficiency_current(G0)
# Random mean/std only on sampled fractions.
rand_eff = {}
for order in random_node_orders:
    edf = efficiency_nodes(G0, order, EFF_FRACS)
    for _, r in edf.iterrows():
        rand_eff.setdefault(int(r.removed), []).append(float(r.E))
eff_node_parts = []
rows=[]
for k in sorted(rand_eff):
    vals=np.asarray(rand_eff[k]); rows.append(('aleatorio_media_100',k,k/N0,vals.mean(),vals.std(ddof=1),vals.mean()/E0))
eff_node_parts.append(pd.DataFrame(rows, columns=['estrategia','removed','f','E_mean','E_std','E_relativa_E0']))
for name, order in [('grado_desc',degree_order),('intermediacion_desc',bet_order),('intermediacion_adaptativa',adapt_bet_order)]:
    edf=efficiency_nodes(G0,order,EFF_FRACS)
    edf['estrategia']=name; edf['E_mean']=edf['E']; edf['E_std']=0.0; edf['E_relativa_E0']=edf['E']/E0
    eff_node_parts.append(edf[['estrategia','removed','f','E_mean','E_std','E_relativa_E0']])
eff_nodes=pd.concat(eff_node_parts, ignore_index=True)
eff_nodes.to_csv(TAB/'03_eficiencia_percolacion_nodos.csv', index=False)

print('4/7 Percolación de enlaces...')
t0=time.perf_counter()
ebet=edge_bet_order(G0); eadapt=edge_adaptive_bet_order(G0); ebridge=bridge_first_order(G0)
print(f'   órdenes listos en {time.perf_counter()-t0:.2f}s')
edge_curves={
    'intermediacion_arista_desc': edge_curve_from_order(G0,ebet),
    'intermediacion_arista_adaptativa': edge_curve_from_order(G0,eadapt),
    'puentes_P1_primero': edge_curve_from_order(G0,ebridge),
}
for k,df in edge_curves.items(): df.to_csv(TAB/f'05_enlaces_{k}.csv',index=False)

rng=random.Random(SEED+10000)
random_edge_orders=[]
arrES=np.zeros((N_RANDOM,M0+1)); arrES2=np.zeros((N_RANDOM,M0+1))
base_edges=list(G0.edges())
for r in range(N_RANDOM):
    order=base_edges.copy(); rng.shuffle(order); random_edge_orders.append(order)
    c=edge_curve_from_order(G0,order); arrES[r]=c['S']; arrES2[r]=c['S2']
random_edge_df=pd.DataFrame({
    'removed':np.arange(M0+1),'f':np.arange(M0+1)/M0,
    'S_mean':arrES.mean(0),'S_std':arrES.std(0,ddof=1),
    'S2_mean':arrES2.mean(0),'S2_std':arrES2.std(0,ddof=1)
})
random_edge_df.to_csv(TAB/'04_enlaces_aleatorio_100_realizaciones.csv',index=False)
rt=random_edge_df.rename(columns={'S_mean':'S','S2_mean':'S2'})
fc,f50=estimate_threshold(rt); thresholds.append(('enlaces','aleatorio_media_100',fc,f50))
for name,df in edge_curves.items():
    fc,f50=estimate_threshold(df); thresholds.append(('enlaces',name,fc,f50))
threshold_df=pd.DataFrame(thresholds,columns=['tipo','estrategia','fc_pico_segunda_componente','f50'])
threshold_df.to_csv(TAB/'06_umbrales_fc_f50.csv',index=False)

print('5/7 Eficiencia en percolación de enlaces...')
rand_eff={}
for order in random_edge_orders:
    edf=efficiency_edges(G0,order,EFF_FRACS)
    for _,r in edf.iterrows(): rand_eff.setdefault(int(r.removed),[]).append(float(r.E))
parts=[]; rows=[]
for k in sorted(rand_eff):
    vals=np.asarray(rand_eff[k]); rows.append(('aleatorio_media_100',k,k/M0,vals.mean(),vals.std(ddof=1),vals.mean()/E0))
parts.append(pd.DataFrame(rows,columns=['estrategia','removed','f','E_mean','E_std','E_relativa_E0']))
for name,order in [('intermediacion_arista_desc',ebet),('intermediacion_arista_adaptativa',eadapt),('puentes_P1_primero',ebridge)]:
    edf=efficiency_edges(G0,order,EFF_FRACS); edf['estrategia']=name; edf['E_mean']=edf['E']; edf['E_std']=0.; edf['E_relativa_E0']=edf['E']/E0
    parts.append(edf[['estrategia','removed','f','E_mean','E_std','E_relativa_E0']])
eff_edges=pd.concat(parts,ignore_index=True)
eff_edges.to_csv(TAB/'07_eficiencia_percolacion_enlaces.csv',index=False)

print('6/7 Comparación con modelos nulos...')
def degree_preserving_null(G, seed):
    H=G.copy(); nx.double_edge_swap(H, nswap=10*H.number_of_edges(), max_tries=200*H.number_of_edges(), seed=seed); return H

def random_curve_graph(G, rng):
    order = list(G.nodes())
    rng.shuffle(order)
    return node_curve_from_order(G, order)['S'].to_numpy()


def degree_curve_graph(G):
    order = node_degree_order(G)
    return node_curve_from_order(G, order)['S'].to_numpy()

null_random={'UCuenca':arrS,'Erdos-Renyi':np.zeros((N_NULL,N0+1)),'Configuracion':np.zeros((N_NULL,N0+1))}
null_degree={'UCuenca':node_curves['grado_desc']['S'].to_numpy()[None,:], 'Erdos-Renyi':np.zeros((N_NULL,N0+1)), 'Configuracion':np.zeros((N_NULL,N0+1))}
rngn=random.Random(SEED+20000)
for r in range(N_NULL):
    er=nx.gnm_random_graph(N0,M0,seed=SEED+30000+r)
    cfg=degree_preserving_null(G0,SEED+40000+r)
    null_random['Erdos-Renyi'][r]=random_curve_graph(er,rngn)
    null_random['Configuracion'][r]=random_curve_graph(cfg,rngn)
    null_degree['Erdos-Renyi'][r]=degree_curve_graph(er)
    null_degree['Configuracion'][r]=degree_curve_graph(cfg)

fnode=np.arange(N0+1)/N0
rows=[]
for attack,dct in [('fallo_aleatorio',null_random),('grado_desc',null_degree)]:
    for model,arr in dct.items():
        mean=arr.mean(0); std=arr.std(0,ddof=1) if arr.shape[0]>1 else np.zeros(N0+1)
        auc=float(np.trapz(mean,fnode)); hi=np.flatnonzero(mean<=0.5); f50=float(fnode[hi[0]]) if len(hi) else 1.0
        for k in range(N0+1): rows.append((attack,model,k,fnode[k],mean[k],std[k],auc,f50))
null_df=pd.DataFrame(rows,columns=['ataque','modelo','removed','f','S_mean','S_std','AUC_S','f50'])
null_df.to_csv(TAB/'08_comparacion_modelos_nulos.csv',index=False)
null_summary=null_df.groupby(['ataque','modelo']).agg(AUC_S=('AUC_S','first'),f50=('f50','first'),S_inicial=('S_mean','first')).reset_index()
null_summary.to_csv(TAB/'09_resumen_robustez_modelos_nulos.csv',index=False)

snap=[]
for fv in [0.05,0.10,0.20,0.30,0.50]:
    def val(df,col): return float(df.loc[(df['f']-fv).abs().idxmin(),col])
    snap.append((fv,val(random_node_df,'S_mean'),val(node_curves['grado_desc'],'S'),val(node_curves['intermediacion_desc'],'S'),val(node_curves['intermediacion_adaptativa'],'S')))
pd.DataFrame(snap,columns=['f','S_random','S_grado','S_betweenness','S_betweenness_adaptativa']).to_csv(TAB/'10_nodos_S_en_fracciones_clave.csv',index=False)

print('7/7 Figuras...')
plt.figure(figsize=(9,6)); plt.plot(random_node_df['f'],random_node_df['S_mean'],label='Fallo aleatorio (media 100)'); plt.fill_between(random_node_df['f'],random_node_df['S_mean']-random_node_df['S_std'],random_node_df['S_mean']+random_node_df['S_std'],alpha=.18)
for n,l in [('grado_desc','Grado descendente'),('intermediacion_desc','Intermediación descendente'),('intermediacion_adaptativa','Intermediación recalculada')]: plt.plot(node_curves[n]['f'],node_curves[n]['S'],label=l)
plt.xlabel('Fracción de nodos eliminados f'); plt.ylabel('S(f) = |GCC| / N original'); plt.title('Percolación de nodos — Red UCuenca'); plt.legend(); plt.tight_layout(); plt.savefig(FIG/'01_percolacion_nodos_S.png',dpi=190); plt.close()

plt.figure(figsize=(9,6))
for s,l in [('aleatorio_media_100','Fallo aleatorio (media 100)'),('grado_desc','Grado descendente'),('intermediacion_desc','Intermediación descendente'),('intermediacion_adaptativa','Intermediación recalculada')]:
    d=eff_nodes[eff_nodes['estrategia']==s]; plt.plot(d['f'],d['E_mean'],marker='o',label=l)
plt.xlabel('Fracción de nodos eliminados f'); plt.ylabel('Eficiencia global E'); plt.title('Eficiencia global — percolación de nodos'); plt.legend(); plt.tight_layout(); plt.savefig(FIG/'02_percolacion_nodos_eficiencia.png',dpi=190); plt.close()

plt.figure(figsize=(9,6)); plt.plot(random_edge_df['f'],random_edge_df['S_mean'],label='Fallo aleatorio (media 100)'); plt.fill_between(random_edge_df['f'],random_edge_df['S_mean']-random_edge_df['S_std'],random_edge_df['S_mean']+random_edge_df['S_std'],alpha=.18)
for n,l in [('intermediacion_arista_desc','Intermediación de arista'),('intermediacion_arista_adaptativa','Intermediación de arista recalculada'),('puentes_P1_primero','Puentes de P1 primero')]: plt.plot(edge_curves[n]['f'],edge_curves[n]['S'],label=l)
plt.xlabel('Fracción de enlaces eliminados f'); plt.ylabel('S(f) = |GCC| / N original'); plt.title('Percolación de enlaces — Red UCuenca'); plt.legend(); plt.tight_layout(); plt.savefig(FIG/'03_percolacion_enlaces_S.png',dpi=190); plt.close()

plt.figure(figsize=(9,6))
for s,l in [('aleatorio_media_100','Fallo aleatorio (media 100)'),('intermediacion_arista_desc','Intermediación de arista'),('intermediacion_arista_adaptativa','Intermediación de arista recalculada'),('puentes_P1_primero','Puentes de P1 primero')]:
    d=eff_edges[eff_edges['estrategia']==s]; plt.plot(d['f'],d['E_mean'],marker='o',label=l)
plt.xlabel('Fracción de enlaces eliminados f'); plt.ylabel('Eficiencia global E'); plt.title('Eficiencia global — percolación de enlaces'); plt.legend(); plt.tight_layout(); plt.savefig(FIG/'04_percolacion_enlaces_eficiencia.png',dpi=190); plt.close()

for attack,title,fn in [('fallo_aleatorio','Fallo aleatorio: UCuenca vs modelos nulos','05_nulos_fallo_aleatorio.png'),('grado_desc','Ataque por grado: UCuenca vs modelos nulos','06_nulos_ataque_grado.png')]:
    plt.figure(figsize=(9,6))
    for model in ['UCuenca','Erdos-Renyi','Configuracion']:
        d=null_df[(null_df['ataque']==attack)&(null_df['modelo']==model)]; plt.plot(d['f'],d['S_mean'],label=model)
    plt.xlabel('Fracción de nodos eliminados f'); plt.ylabel('S(f)'); plt.title(title); plt.legend(); plt.tight_layout(); plt.savefig(FIG/fn,dpi=190); plt.close()

print('\n=== UMBRALES ==='); print(threshold_df.to_string(index=False))
print('\n=== NULOS ==='); print(null_summary.to_string(index=False))
print('\n=== FRACCIONES CLAVE ==='); print(pd.read_csv(TAB/'10_nodos_S_en_fracciones_clave.csv').to_string(index=False))
print(f'\nE0={E0:.6f}')

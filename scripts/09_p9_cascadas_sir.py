"""
P9 — Propagación de fallos en cascada y epidemias SIR — Red UCuenca.

Cascada: carga inicial = intermediación (betweenness) normalizada;
C_i=(1+tau)L_i. Tras cada falla se recalcula la intermediación sobre la
topología superviviente, interpretando el cambio como redistribución de carga
por nuevos caminos mínimos.

SIR: simulación continua tipo Gillespie con lambda=beta/mu y mu=1.
Inmunización: m=10 nodos, aleatoria vs top-10 por intermediación.

Referencias del módulo usadas en la discusión:
Newman, M. E. J. (2010). Networks: An Introduction. Oxford University Press.
Latora, V., Nicosia, V., & Russo, G. (2017). Complex Networks: Principles,
Methods and Applications. Cambridge University Press.
"""
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import networkx as nx, pandas as pd, numpy as np, random, math, os
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'; TAB=ROOT/'resultados'/'tablas'; FIG=ROOT/'resultados'/'figuras'; TAB.mkdir(parents=True,exist_ok=True); FIG.mkdir(parents=True,exist_ok=True)
G=nx.Graph(nx.read_graphml(DATA/'red_ucuenca.graphml')); nodes_df=pd.read_csv(DATA/'red_ucuenca_nodes.csv'); META=nodes_df.set_index('id'); NODES=list(G); N=len(NODES); ADJ={u:list(G.neighbors(u)) for u in NODES}
INIT=nx.betweenness_centrality(G, normalized=True)

def cascade(trigger,tau,detail=False):
    cap={n:(1+tau)*INIT[n] for n in NODES}; H=G.copy(); failed={trigger}; gens=[[trigger]]; H.remove_node(trigger)
    while H.number_of_nodes():
        load=nx.betweenness_centrality(H, normalized=True)
        over=[n for n in H if load[n]>cap[n]+1e-12]
        if not over: break
        H.remove_nodes_from(over); failed.update(over); gens.append(over)
    return failed,gens

def worker(args):
    trigger,tau=args; f,g=cascade(trigger,tau)
    return (tau,trigger,META.loc[trigger,'campus'],META.loc[trigger,'capa'],len(f),len(f)/N,len(g),len(f)/N>0.2)

if __name__=='__main__':
    pd.DataFrame([{'nodo':n,'campus':META.loc[n,'campus'],'capa':META.loc[n,'capa'],'carga_inicial':INIT[n]} for n in NODES]).sort_values('carga_inicial',ascending=False).to_csv(TAB/'01_carga_inicial.csv',index=False)
    rows=[]
    tasks=[(n,tau) for tau in [0.0,0.035,0.04] for n in NODES]
    with ProcessPoolExecutor(max_workers=min(5, os.cpu_count() or 1)) as ex:
        for out in ex.map(worker,tasks,chunksize=4):
            rows.append(out)
    scan=pd.DataFrame(rows,columns=['tau','trigger','campus','capa','fallos_totales','fraccion_afectada','generaciones','supera_20pct']); scan.to_csv(TAB/'02_barrido_tau.csv',index=False)
    best=(scan.sort_values(['tau','fallos_totales'],ascending=[True,False]).groupby('tau',as_index=False).first()); best.to_csv(TAB/'03_max_cascada_por_tau.csv',index=False)
    near=scan[(scan.tau==0.035)&scan.supera_20pct]
    crit=near.sort_values('fallos_totales',ascending=False).iloc[0].trigger
    lo,hi=0.035,0.04
    for _ in range(16):
        mid=(lo+hi)/2; f,_=cascade(crit,mid)
        if len(f)/N>0.2: lo=mid
        else: hi=mid
    tau_c=lo
    cc=[]
    for tau in np.linspace(0,0.05,26):
        f,g=cascade(crit,float(tau)); cc.append({'tau':float(tau),'trigger':crit,'fallos_totales':len(f),'fraccion_afectada':len(f)/N,'generaciones':len(g)})
    pd.DataFrame(cc).to_csv(TAB/'04_curva_trigger_critico.csv',index=False)
    scan[scan.tau==0].sort_values(['fallos_totales','trigger'],ascending=[False,True]).head(15).to_csv(TAB/'05_top_disparadores_tau0.csv',index=False)
    scan[scan.tau==0.035].sort_values(['fallos_totales','trigger'],ascending=[False,True]).head(15).to_csv(TAB/'06_top_disparadores_tau035.csv',index=False)
    f,gens=cascade(crit,tau_c*(1-1e-7)); gr=[]
    for i,grp in enumerate(gens):
        for n in grp: gr.append({'generacion':i,'nodo':n,'campus':META.loc[n,'campus'],'capa':META.loc[n,'capa']})
    pd.DataFrame(gr).to_csv(TAB/'07_generaciones_cascada_critica.csv',index=False)
    # SIR
    def sir_once(lam,rng,immune=None):
        immune=set() if immune is None else set(immune); avail=[u for u in NODES if u not in immune]; seed=rng.choice(avail); S=set(avail); S.remove(seed); I={seed}; ever={seed}
        while I:
            si=[(u,v) for u in I for v in ADJ[u] if v in S]; ir=lam*len(si); rr=len(I); total=ir+rr
            if si and rng.random()<ir/total:
                _,v=rng.choice(si); S.remove(v); I.add(v); ever.add(v)
            else:
                u=rng.choice(tuple(I)); I.remove(u)
        return len(ever)
    deg=np.array([d for _,d in G.degree()],float); mk=deg.mean(); mk2=(deg**2).mean(); lmf=mk/mk2
    sr=[]
    for lam in np.round(np.arange(0.05,1.51,0.05),2):
        rng=random.Random(2026+int(lam*10000)); vals=np.array([sir_once(float(lam),rng) for _ in range(500)],float)/N
        sr.append({'lambda':lam,'tamano_final_medio':vals.mean(),'std':vals.std(ddof=1),'prob_brote_mayor_20pct':np.mean(vals>0.2),'susceptibilidad_finita':N*vals.var(ddof=1)/vals.mean()})
    sir=pd.DataFrame(sr); sir.to_csv(TAB/'08_SIR_barrido_lambda.csv',index=False); above=sir[sir.prob_brote_mayor_20pct>=0.10]; lemp=float(above.iloc[0]['lambda']); lsusc=float(sir.loc[sir.susceptibilidad_finita.idxmax(),'lambda'])
    pd.DataFrame([{'mean_k':mk,'mean_k2':mk2,'lambda_c_campo_medio':lmf,'lambda_c_empirico_operacional':lemp,'criterio_empirico':'primera lambda con P(brote >20%) >= 10%','lambda_pico_susceptibilidad_finita':lsusc}]).to_csv(TAB/'09_umbral_epidemico.csv',index=False)
    # immunization
    bet_sorted=sorted(INIT.items(),key=lambda kv:(-kv[1],str(kv[0]))); cent={n for n,_ in bet_sorted[:10]}; pd.DataFrame([{'ranking':i+1,'nodo':n,'campus':META.loc[n,'campus'],'capa':META.loc[n,'capa'],'betweenness':b} for i,(n,b) in enumerate(bet_sorted[:10])]).to_csv(TAB/'10_inmunizacion_top10.csv',index=False)
    def immrun(strategy):
        rng=random.Random(2026+{'ninguna':100000,'aleatoria':200000,'centralidad':300000}[strategy]); vals=[]
        for _ in range(1000):
            imm=set() if strategy=='ninguna' else (set(rng.sample(NODES,10)) if strategy=='aleatoria' else cent); vals.append(sir_once(1.0,rng,imm))
        vals=np.array(vals,float)/N; return {'estrategia':strategy,'m':0 if strategy=='ninguna' else 10,'lambda':1.0,'tamano_final_medio':vals.mean(),'std':vals.std(ddof=1),'prob_brote_mayor_20pct':np.mean(vals>0.2)}
    imm=pd.DataFrame([immrun(x) for x in ['ninguna','aleatoria','centralidad']]); base=float(imm[imm.estrategia=='ninguna'].tamano_final_medio.iloc[0]); imm['reduccion_media_vs_base_pct']=100*(base-imm.tamano_final_medio)/base; imm.to_csv(TAB/'11_inmunizacion_resultados.csv',index=False)
    # figures
    cdf=pd.DataFrame(cc); import matplotlib.pyplot as plt
    plt.figure(figsize=(8,5)); plt.plot(cdf.tau,100*cdf.fraccion_afectada,marker='o'); plt.axhline(20,ls='--',label='20%'); plt.axvline(tau_c,ls='--',label=f'tau_c={tau_c:.4f}'); plt.xlabel('Margen tau'); plt.ylabel('Nodos afectados (%)'); plt.title(f'Cascada: {crit}'); plt.legend(); plt.tight_layout(); plt.savefig(FIG/'01_tau_critico.png',dpi=180); plt.close()
    plt.figure(figsize=(9,5)); plt.plot(sir['lambda'],sir.tamano_final_medio,marker='o',label='Tamaño medio'); plt.plot(sir['lambda'],sir.prob_brote_mayor_20pct,marker='o',label='P(brote>20%)'); plt.axvline(lmf,ls='--',label=f'MF={lmf:.3f}'); plt.axvline(lemp,ls=':',label=f'Emp={lemp:.2f}'); plt.xlabel('lambda=beta/mu'); plt.ylabel('Fracción / probabilidad'); plt.legend(); plt.tight_layout(); plt.savefig(FIG/'02_SIR_umbral.png',dpi=180); plt.close()
    plt.figure(figsize=(8,5)); plt.bar(imm.estrategia,imm.tamano_final_medio); plt.ylabel('Fracción media infectada'); plt.title('Inmunización m=10, lambda=1.0'); plt.tight_layout(); plt.savefig(FIG/'03_inmunizacion.png',dpi=180); plt.close()
    print('tau_c',tau_c,'crit',crit); print(best[['tau','trigger','fallos_totales','fraccion_afectada']].to_string(index=False)); print('lambda mf',lmf,'emp',lemp,'susc',lsusc); print(imm.to_string(index=False))

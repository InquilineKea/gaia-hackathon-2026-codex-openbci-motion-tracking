import json,math
from pathlib import Path
b=Path('outputs/collagen-graph-audit-controls-20261031');rs=json.loads((b/'raw/controls.json').read_text())['records'];lookup={(r['z_target'],r['seed'],r['arm'],r['kappa'],r['rate_beta'],r['dt']):r for r in rs}
def value(r,t):
 assert r['converged'] and r['G0']>1e-6
 p=min(r['trace'],key=lambda p:abs(p['t']-t));assert abs(p['t']-t)<1e-8;return p['stress']/r['trace'][0]['stress']
rows=[]
for z in [3.2,4.,4.8]:
 for k in [.003,.03]:
  for t in [.2,.5,1.,2.,5.]:
   pairs=[]
   for seed in range(74000,74004):
    values={(arm,beta):value(lookup[(z,seed,arm,k,beta,.1)],t) for arm in [0,3] for beta in [0.,10.]}
    pairs.append(dict(seed=seed,hub_delta_beta0=values[3,0.]-values[0,0.],hub_delta_beta10=values[3,10.]-values[0,10.],uniform_rate_delta=values[0,10.]-values[0,0.],hub_rate_delta=values[3,10.]-values[3,0.]))
   row=dict(z_target=z,kappa=k,t=t,n=4,pairs=pairs)
   for key in ['hub_delta_beta0','hub_delta_beta10','uniform_rate_delta','hub_rate_delta']:row[key+'_mean']=sum(p[key] for p in pairs)/4
   rows.append(row)
out=dict(scope='Existing dt.1 traces only; beta0 has no finer-time-step controls. No new numerical simulation. Four original paired seeds; normalized time-t stress, not material parameter inference.',records=rows)
(b/'analysis/TRANSIENT_RATE_SUMMARY.json').write_text(json.dumps(out,indent=2,allow_nan=False)+'\n')
worst=max(rows,key=lambda r:abs(r['uniform_rate_delta_mean']));print(json.dumps(worst));print('Final versus intermediate rate differences must not be replaced by an analytic exp(-5) universal bound.')

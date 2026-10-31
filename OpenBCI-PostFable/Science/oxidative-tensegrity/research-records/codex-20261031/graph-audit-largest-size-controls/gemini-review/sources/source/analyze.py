import json,csv,math,hashlib,statistics
from pathlib import Path
b=Path('outputs/collagen-graph-audit-controls-20261031');o=b/'analysis';o.mkdir(exist_ok=True)
def read(n):return json.loads((b/n).read_text())
def write(n,x):(o/n).write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def mean(x):return sum(x)/len(x) if x else None
def csvout(name,rows):
 if not rows:return
 with (o/name).open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
graphs=read('raw/audit.json')['records'];cases=read('raw/controls.json')['records'];ac=read('raw/audit-complete.json');cc=read('raw/controls-complete.json');assert ac['complete'] and cc['complete'] and len(graphs)==336 and len(cases)==384
assert all(g['hash_matched'] for g in graphs)
for g in graphs:
 assert bool(any(v[0] for c in g['components'] for v in c['winding_vectors']))==g['wrap_basis_1']
 assert bool(any(v[1] for c in g['components'] for v in c['winding_vectors']))==g['wrap_basis_2']
 assert sum(g['degree_histogram'])==g['L']**2 and sum(k*n for k,n in enumerate(g['degree_histogram']))==2*g['edges']
 g['edges_outside_giant']=g['edges']-g['giant_edges']
def finite(x):
 if isinstance(x,float):assert math.isfinite(x)
 elif isinstance(x,dict):
  for v in x.values():finite(v)
 elif isinstance(x,list):
  for v in x:finite(v)
finite(graphs);finite(cases)
def key(r):return tuple(r[k] for k in ['L','z_target','seed','arm','kappa','r','dt','rate_beta'])
lookup={key(r):r for r in cases};assert len(lookup)==len(cases)
def eligible(r):return r['converged'] and r['completed_internal_time']==5. and r['G0']>1e-6 and r['modulus_step_relative_difference']<1e-4 and r['retention'] is not None
for r in cases:
 assert r['converged'] and r['max_force_residual']<=1e-8 and r['completed_internal_time']==5
 assert r['mask_sha256']==next(g['mask_sha256'] for g in graphs if (g['L'],g['z_target'],g['seed'],g['arm'])==(r['L'],r['z_target'],r['seed'],r['arm']))
refs=read('inputs/prior_mechanical_references.json');rep=[]
for r in refs:
 if key(r) not in lookup:continue
 c=lookup[key(r)];assert c['mask_sha256']==r['mask_sha256']
 rep.append(dict(key=list(key(r)),G0_difference=c['G0']-r['G0'],retention_difference=None if c['retention'] is None or r['retention'] is None else c['retention']-r['retention']))
write('BASELINE_REPRODUCTION.json',dict(reference_rows_checked=len(rep),unique_case_keys=len({tuple(r['key']) for r in rep}),maximum_G0_difference=max(abs(x['G0_difference']) for x in rep),maximum_retention_difference=max(abs(x['retention_difference']) for x in rep if x['retention_difference'] is not None)))
groups=[]
for L in [12,18,24]:
 for z in [1.2,1.6,2.,2.4,3.2,4.,4.8]:
  for arm in range(4):
   rs=[g for g in graphs if (g['L'],g['z_target'],g['arm'])==(L,z,arm)]
   d=dict(L=L,z_target=z,arm=arm,n=len(rs))
   for k in ['z_actual','triangles','clustering','clustering_degree_ge2','transitivity','degree_variance','isolated_fraction','giant_nodes','giant_edges','giant_mean_degree','giant_bends','edges_outside_giant','giant_winding_rank','accepted']:
    d[k+'_mean']=mean([g[k] for g in rs])
   d['rank2_any_fraction']=mean([g['any_rank2_component'] for g in rs]);d['rank2_giant_fraction']=mean([g['giant_winding_rank']==2 for g in rs]);d['both_flags_fraction']=mean([g['wrap_basis_1'] and g['wrap_basis_2'] for g in rs]);d['both_flags_without_rank2_count']=sum(g['wrap_basis_1'] and g['wrap_basis_2'] and not g['any_rank2_component'] for g in rs)
   for k in range(7):d['degree_'+str(k)+'_fraction_mean']=mean([g['degree_histogram'][k]/L**2 for g in rs])
   groups.append(d)
csvout('graph-audit-summary.csv',groups)
write('GRAPH_AUDIT_SUMMARY.json',dict(graphs=len(graphs),all336_hashes_match=True,degree_sequence_invariants_checked=ac['degree_sequences_preserved'],directional_flag_consistency_all336=True,graphs_with_edges_outside_giant=sum(g['edges_outside_giant']>0 for g in graphs),both_flags_without_rank2_examples=[{k:g[k] for k in ['L','z_target','seed','arm','giant_winding_rank']} for g in graphs if g['wrap_basis_1'] and g['wrap_basis_2'] and not g['any_rank2_component']],both_flags_without_rank2=sum(g['wrap_basis_1'] and g['wrap_basis_2'] and not g['any_rank2_component'] for g in graphs),selected_L24=[g for g in groups if g['L']==24 and g['z_target'] in [2.4,3.2,4.,4.8]],elapsed_seconds=ac['elapsed_seconds']))
refinements=[]
for r in cases:
 if r['dt']!=.025:continue
 c=lookup[key(r)[:-2]+(.05,r['rate_beta'])];coarse=lookup[key(r)[:-2]+(.1,r['rate_beta'])]
 row={k:r[k] for k in ['L','z_target','seed','arm','kappa','r','rate_beta','G0']};ok=all(eligible(x) for x in [r,c,coarse]);row['eligible']=ok
 row.update(retention_dt1=coarse['retention'],retention_dt05=c['retention'],retention_dt025=r['retention'],fine_difference=None if not ok else c['retention']-r['retention'],coarse_difference=None if not ok else coarse['retention']-r['retention'])
 row['meets_predeclared_0001']=None if not ok else abs(row['fine_difference'])<=.0001;refinements.append(row)
csvout('time-step-pairs.csv',refinements)
write('TIME_STEP_SUMMARY.json',dict(comparisons=len(refinements),eligible_comparisons=sum(r['eligible'] for r in refinements),ineligible_comparisons=sum(not r['eligible'] for r in refinements),eligible_failures=sum(r['eligible'] and not r['meets_predeclared_0001'] for r in refinements),threshold_retention=.0001,max_fine_difference=max(abs(r['fine_difference']) for r in refinements if r['eligible']),max_coarse_difference=max(abs(r['coarse_difference']) for r in refinements if r['eligible']),worst_eligible=sorted([r for r in refinements if r['eligible']],key=lambda r:abs(r['fine_difference']),reverse=True)[:8]))
paired=[]
for z in [3.2,4.,4.8]:
 for kap in [.003,.03]:
  for name,plus,minus in [('hub_minus_uniform',3,0),('triangle_high_minus_low',1,2)]:
   for seed in range(74000,74004):
    row=dict(z_target=z,kappa=kap,contrast=name,seed=seed);vals=[]
    for dt in [.1,.05,.025]:
     p=lookup[(24,z,seed,plus,kap,.5,dt,10.)];m=lookup[(24,z,seed,minus,kap,.5,dt,10.)];delta=p['retention']-m['retention'] if eligible(p) and eligible(m) else None
     row['delta_dt'+str(dt)]=delta;vals.append(delta)
    row['contrast_change_fine']=None if any(v is None for v in vals) else vals[1]-vals[2];paired.append(row)
csvout('paired-time-step-contrasts.csv',paired)
ps=[]
for z in [3.2,4.,4.8]:
 for kap in [.003,.03]:
  for name in ['hub_minus_uniform','triangle_high_minus_low']:
   rs=[r for r in paired if (r['z_target'],r['kappa'],r['contrast'])==(z,kap,name)];d=dict(z_target=z,kappa=kap,contrast=name)
   for dt in [.1,.05,.025]:
    v=[r['delta_dt'+str(dt)] for r in rs if r['delta_dt'+str(dt)] is not None];d['n_dt'+str(dt)]=len(v);d['mean_dt'+str(dt)]=mean(v);d['paired_values_dt'+str(dt)]=v
   d['max_paired_fine_change']=max([abs(r['contrast_change_fine']) for r in rs if r['contrast_change_fine'] is not None],default=None);ps.append(d)
write('PAIRED_TIME_STEP_SUMMARY.json',ps)
rates=[]
for z in [3.2,4.,4.8]:
 for kap in [0.,.003,.03]:
  for beta in [0.,10.]:
   pairs=[];vals={0:[],3:[]}
   for seed in range(74000,74004):
    rs=[lookup[(24,z,seed,arm,kap,.5,.1,beta)] for arm in [0,3]]
    for r in rs:
     if eligible(r):vals[r['arm']].append(r['retention'])
    if all(eligible(r) for r in rs):pairs.append(dict(seed=seed,delta=rs[1]['retention']-rs[0]['retention'],uniform=rs[0]['retention'],hub=rs[1]['retention']))
   rates.append(dict(z_target=z,kappa=kap,rate_beta=beta,eligible_uniform=len(vals[0]),eligible_hub=len(vals[3]),eligible_pairs=len(pairs),paired_uniform_mean=mean([p['uniform'] for p in pairs]),paired_hub_mean=mean([p['hub'] for p in pairs]),paired_delta_mean=mean([p['delta'] for p in pairs]),pairs=pairs))
write('RATE_SUMMARY.json',rates)
cols=['L','z_target','seed','arm','kappa','r','rate_beta','dt','G0','retention','max_force_residual','converged','completed_internal_time','max_raw_rate_argument','rate_cap_steps','rate_cap_edge_updates','mask_sha256'];csvout('mechanical-cases.csv',[{k:r[k] for k in cols} for r in cases])
write('RUN_SUMMARY.json',dict(graphs_audited=len(graphs),mechanical_cases=len(cases),all_converged=True,eligible_cases=sum(eligible(r) for r in cases),max_force_residual=max(r['max_force_residual'] for r in cases),maximum_uncapped_rate_argument=max(r['max_raw_rate_argument'] for r in cases),total_cap_steps=sum(r['rate_cap_steps'] for r in cases),total_cap_edge_updates=sum(r['rate_cap_edge_updates'] for r in cases),elapsed_graph_audit=ac['elapsed_seconds'],elapsed_controls=cc['elapsed_seconds'],four_seeds_not_new_replication=True))
print(json.dumps(read('analysis/RUN_SUMMARY.json')));print(json.dumps(read('analysis/TIME_STEP_SUMMARY.json')))

import csv,json,statistics,math,collections,random
from pathlib import Path
b=Path('outputs/collagen-controlled-topology-20261031');raw=b/'raw';out=b/'analysis';out.mkdir(exist_ok=True)
data=json.loads((raw/'production.json').read_text())['records'];central=json.loads((raw/'central.json').read_text())['records'];ref=json.loads((raw/'refinement.json').read_text())['records']
def eligible(r):return r['converged'] and r.get('completed_internal_time',5)>=4.999 and r['G0']>1e-6 and r['modulus_step_relative_difference']<1e-4
fields=[k for k in data[0] if k!='trace']
for name,rows in [('production',data),('central',central),('refinement',ref)]:
 with (out/(name+'-cases.csv')).open('w') as f:
  w=csv.DictWriter(f,fieldnames=fields+['eligible_for_matched_comparison','matched_fraction_homogeneous_null']);w.writeheader()
  for r in rows:w.writerow({**{k:r.get(k) for k in fields},'eligible_for_matched_comparison':eligible(r),'matched_fraction_homogeneous_null':r['r']+(1-r['r'])*math.exp(-5)})
graphs={}
for r in data:graphs[(r['L'],r['seed'],r['z_target'],r['arm'])]=r
groups=collections.defaultdict(list)
for r in graphs.values():groups[(r['L'],r['z_target'],r['arm'])].append(r)
gs=[]
for key,rr in sorted(groups.items()):
 row=dict(zip(['L','z_target','arm'],key));row['graph_blocks']=len(rr)
 for k in ['z_actual','triangles','clustering','transitivity','degree_variance','largest_component','susceptibility','accepted','proposals','wrap_basis_1','wrap_basis_2']:
  row[k+'_mean']=statistics.mean(float(r[k]) for r in rr)
 gs.append(row)
with (out/'graph-summary.csv').open('w') as f:w=csv.DictWriter(f,fieldnames=list(gs[0]));w.writeheader();w.writerows(gs)
lookup={(r['L'],r['seed'],r['z_target'],r['arm'],r['kappa'],r['r']):r for r in data+central};contr=[]
for r in data+central:
 if r['arm'] not in [1,3] or r['r']!=.5 and r['kappa']!=0:continue
 c=lookup.get((r['L'],r['seed'],r['z_target'],2 if r['arm']==1 else 0,r['kappa'],r['r']))
 if c is None:continue
 row={k:r[k] for k in ['L','seed','z_target','kappa','r']};row['contrast']='triangle_high_minus_low' if r['arm']==1 else 'hub_minus_uniform';row['matched_pair_eligible']=eligible(r) and eligible(c)
 for k in ['triangles','transitivity','degree_variance','largest_component','bends','G0','retention','matched_final_stress']:
  row['delta_'+k]=r[k]-c[k] if r[k] is not None and c[k] is not None else None
 contr.append(row)
with (out/'paired-contrasts.csv').open('w') as f:w=csv.DictWriter(f,fieldnames=list(contr[0]));w.writeheader();w.writerows(contr)
agg=collections.defaultdict(list)
for r in contr:agg[(r['L'],r['z_target'],r['kappa'],r['r'],r['contrast'])].append(r)
summary=[];rng=random.Random(20261031)
for key,rr in sorted(agg.items()):
 row=dict(zip(['L','z_target','kappa','r','contrast'],key));row['available_pairs']=len(rr);er=[r for r in rr if r['matched_pair_eligible']];row['eligible_pairs']=len(er)
 for k in ['G0','retention','matched_final_stress']:
  vals=[r['delta_'+k] for r in er if r['delta_'+k] is not None]
  if vals:
   boot=sorted(statistics.mean(rng.choices(vals,k=len(vals))) for _ in range(2000));row[k+'_delta_mean']=statistics.mean(vals);row[k+'_pointwise_CI_low']=boot[49];row[k+'_pointwise_CI_high']=boot[1949]
 summary.append(row)
keys=list(dict.fromkeys(k for r in summary for k in r))
with (out/'paired-summary.csv').open('w') as f:w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(summary)
refdiff=[]
for r in ref:
 c=lookup[(r['L'],r['seed'],r['z_target'],r['arm'],r['kappa'],r['r'])]
 if eligible(r) and eligible(c):refdiff.append(abs(r['retention']-c['retention']))
result={'production_cases':len(data),'central_cases':len(central),'refined_cases':len(ref),'graph_treatment_variants':len(graphs),'base_graph_settings':len({(r['L'],r['seed'],r['z_target']) for r in data}),'size_seed_blocks':len({(r['L'],r['seed']) for r in data}),'distinct_seed_identifiers':len({r['seed'] for r in data}),'unique_masks':len({r['mask_sha256'] for r in data}),'production_converged':sum(r['converged'] for r in data),'central_converged':sum(r['converged'] for r in central),'eligible_production_cases':sum(eligible(r) for r in data),'maximum_refinement_retention_difference':max(refdiff) if refdiff else None,'eligible_refinement_pairs':len(refdiff),'maximum_force_residual_production':max(r['max_force_residual'] for r in data),'maximum_elastic_retention_error':max(abs(r['retention']-1) for r in data if r['r']==1 and r['retention'] is not None),'scope':'Distinct small-strain linearized central-force/collinear-bending model with quasi-static internal memory. Not a reproduction of nonlinear H100 results or physical seconds.','null_definition':'Runtime field homogeneous_relaxation_null_retention is the fully relaxing exp(-5) reference. Matched-fraction homogeneous null r+(1-r)*exp(-5) is added explicitly in derived CSV. Both are analytic whole-energy rescaling controls, not numerical trajectories.','statistical_limits':'Four graph seeds per size/setting; finite MCMC interventions, not demonstrated equilibrium ensembles. Pointwise bootstrap intervals unadjusted for multiple comparisons. Complete-case matching excludes unresolved/nonrigid states. Hub bias co-changes clustering; triangle arms preserve degree/direction but can change bending motifs.','graph_summaries':gs,'selected_contrasts':[r for r in summary if r['z_target'] in [2.4,4.8] and r['L']==24]}
(out/'SUMMARY.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['graph_summaries','selected_contrasts']}))

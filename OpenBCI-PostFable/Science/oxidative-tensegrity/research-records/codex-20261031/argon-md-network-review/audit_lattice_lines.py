"""Independently enumerate the documented triangular candidate graph; no repo import."""
import collections,json
from pathlib import Path

rows=[]
for W in [8,12,16,32,48,64]:
    def idx(i,j):return (j%W)*W+(i%W)
    nxt=[]
    for j in range(W):
        for i in range(W):
            even=j%2==0
            nbrs=[(i+1,j),(i if even else i+1,j+1),(i-1 if even else i,j+1)]
            nxt.append([idx(a,b) for a,b in nbrs])
    lengths=[]
    for k in range(3):
        seen=set()
        for start in range(W*W):
            if start in seen:continue
            n=start;count=0
            while n not in seen:seen.add(n);count+=1;n=nxt[n][k]
            lengths.append(count)
    N=W*W;nb=3*N;nlines=len(lengths);z=3.4
    assert collections.Counter(lengths)=={W:W,2*W:W}
    p=min(1,z/6/(1-1/W));expected=6*p*(1-nlines/nb)
    rows.append({'W':W,'line_lengths_and_counts':dict(collections.Counter(lengths)),
                 'line_count':nlines,'expected_mean_z_at_target_3_4':expected,
                 'p_used':p,'expected_fraction_after_forced_cuts':1-nlines/nb})
result={'scope':'Independent standard-library enumeration of the source adjacency and line-cycle algorithm, without importing or executing the repository. Expected counts are algebraic expectations, not a mechanical simulation.',
        'rows':rows,'conclusion':'The rectangular periodic staggered triangular graph has W horizontal cycles of length W and W/2 cycles of length 2W in each diagonal direction: 2W total lines. Expected surviving bond fraction after one forced cut per line is p*(1-2/(3W)), not p*(1-1/W). Realized post-bridging coordination must be recorded. Additional random dilution prevents inferring that mean fibre length scales linearly with W.'}
Path('outputs/collagen-argon-swarm-20261031/LATTICE_LINE_AUDIT.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(rows))

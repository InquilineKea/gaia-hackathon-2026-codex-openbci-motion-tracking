"""Exact graph controls, not a collagen or mechanical simulation."""
import collections,json
from fractions import Fraction
from pathlib import Path

def cycles(lengths):
    edges=[];offset=0
    for n in lengths:
        edges += [(offset+i,offset+(i+1)%n) for i in range(n)]
        offset+=n
    return offset,edges

def metrics(lengths):
    n,edges=cycles(lengths);adj=[set() for _ in range(n)]
    for a,b in edges:adj[a].add(b);adj[b].add(a)
    todo=set(range(n));sizes=[]
    while todo:
        root=todo.pop();stack=[root];count=1
        while stack:
            for b in adj[stack.pop()] & todo:
                todo.remove(b);stack.append(b);count+=1
        sizes.append(count)
    wedges=sum(len(ns)*(len(ns)-1)//2 for ns in adj)
    closed=sum(sum(b in adj[a] for a in ns for b in ns if a<b) for ns in adj)
    local=[Fraction(sum(b in adj[a] for a in ns for b in ns if a<b),len(ns)*(len(ns)-1)//2) if len(ns)>1 else Fraction(0) for ns in adj]
    return {'cycle_lengths':lengths,'nodes':n,'edges':len(edges),'degree_histogram':dict(collections.Counter(map(len,adj))),'mean_degree':2*len(edges)/n,'average_local_clustering':float(sum(local)/n),'transitivity':closed/wedges if wedges else 0,'component_sizes':sorted(sizes,reverse=True),'largest_component_fraction':max(sizes)/n,'adjacency':{str(i):sorted(ns) for i,ns in enumerate(adj)}}

data={'scope':'Exact combinatorial counterexamples on simple undirected graphs, without geometry, edge-length matching, mechanics or a phase-transition claim.',
      'cases':[metrics([12]),metrics([6,6]),metrics([3,3,3,3])],
      'conclusions':['All three cases have N=12, M=12, mean degree 2 and the same degree sequence.','One 12-cycle and two 6-cycles have identical mean degree and clustering but different component sizes.','Four triangles have clustering 1 and largest component fraction 0.25; the 12-cycle has clustering 0 and fraction 1. This is not a universal causal effect of clustering.','Any spatial collagen comparison must additionally control admissible edges, geometry, length, orientation and constitutive parameters.']}
assert all(x['nodes']==12 and x['edges']==12 and x['degree_histogram']=={2:12} for x in data['cases'])
assert [x['average_local_clustering'] for x in data['cases']]==[0,0,1]
assert [x['largest_component_fraction'] for x in data['cases']]==[1,.5,.25]
Path('outputs/collagen-argon-swarm-20261031/GRAPH_COUNTEREXAMPLES.json').write_text(json.dumps(data,indent=2)+'\n')
print(json.dumps([{k:v for k,v in x.items() if k not in ['adjacency']} for x in data['cases']]))

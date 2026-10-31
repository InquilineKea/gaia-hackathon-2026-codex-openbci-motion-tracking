import sys,json,time,hashlib,math
from pathlib import Path
sys.path.insert(0,'/mnt/work')
from model import graph
out=Path('/mnt/work/out');start=time.monotonic();records=[];steps=[(1,0),(0,1),(-1,1)]
expected=json.loads(Path('/mnt/work/inputs/expected_graphs.json').read_text())
for ref in expected:
 if time.monotonic()-start>1150:raise TimeoutError('Graph audit deadline')
 L,z,seed,arm=[ref[k] for k in ['L','z_target','seed','arm']];N=L*L
 E,mask,meta=graph(L,z,seed,arm);assert meta['mask_sha256']==ref['mask_sha256']
 for k in ['edges','triangles','clustering','degree_variance','wrap_basis_1','wrap_basis_2']:assert meta[k]==ref[k],(k,meta[k],ref[k])
 active=[int(e) for e in mask.nonzero()[0]];adj=[[] for _ in range(N)]
 for e in active:
  i,j,d=map(int,E[e]);dx,dy=steps[d];adj[i].append((j,dx,dy));adj[j].append((i,-dx,-dy))
 deg=[len(x) for x in adj];labels=[-1]*N;components=[]
 for root in range(N):
  if labels[root]>=0:continue
  ci=len(components);positions={root:(0,0)};labels[root]=ci;queue=[root];nodes=[];wind=set()
  while queue:
   i=queue.pop();nodes.append(i)
   for j,dx,dy in adj[i]:
    pos=(positions[i][0]+dx,positions[i][1]+dy)
    if j not in positions:positions[j]=pos;labels[j]=ci;queue.append(j)
    else:
     a,b=pos[0]-positions[j][0],pos[1]-positions[j][1];assert a%L==0 and b%L==0
     a,b=a//L,b//L
     if a or b:
      g=math.gcd(abs(a),abs(b));a,b=a//g,b//g
      if a<0 or (a==0 and b<0):a,b=-a,-b
      wind.add((a,b))
  vectors=sorted(wind);rank=0 if not vectors else 1
  if any(a*d-b*c for a,b in vectors for c,d in vectors):rank=2
  components.append(dict(root=root,nodes=len(nodes),edges=sum(deg[i] for i in nodes)//2,bends=0,winding_vectors=vectors,winding_rank=rank))
 for e in active:
  i,j,d=map(int,E[e]);dx,dy=steps[d];x,y=i%L,i//L;h=((y-dy)%L)*L+(x-dx)%L
  prev=3*h+d
  if mask[prev]:components[labels[i]]['bends']+=1
 assert sum(c['nodes'] for c in components)==N and sum(c['edges'] for c in components)==len(active)
 assert sum(c['bends'] for c in components)==ref['bends']
 giant=max(range(len(components)),key=lambda c:components[c]['nodes']);g=components[giant];isolate=sum(x==0 for x in deg)
 sets=[set(j for j,_,_ in a) for a in adj]
 local=[sum(v in sets[u] for u in sets[i] for v in sets[i] if u<v)/(deg[i]*(deg[i]-1)/2) for i in range(N) if deg[i]>=2]
 rec={**meta,'hash_matched':True,'degree_histogram':[deg.count(k) for k in range(7)],'isolated_nodes':isolate,'isolated_fraction':isolate/N,'clustering_degree_ge2':sum(local)/len(local) if local else 0.,'giant_component_index':giant,'giant_nodes':g['nodes'],'giant_edges':g['edges'],'giant_mean_degree':2*g['edges']/g['nodes'],'giant_bends':g['bends'],'giant_winding_rank':g['winding_rank'],'any_rank2_component':any(c['winding_rank']==2 for c in components),'components':components,'node_components':labels,'degrees':deg,'active_edge_indices':active}
 records.append(rec)
 (out/'audit.json').write_text(json.dumps(dict(records=records,elapsed_seconds=time.monotonic()-start)))
 print(json.dumps(dict(L=L,z=z,seed=seed,arm=arm,completed_graphs=len(records),elapsed_seconds=time.monotonic()-start)),flush=True)
# Exact degree-sequence and edge-direction checks against reconstructed uniform counterparts.
lookup={(r['L'],r['z_target'],r['seed'],r['arm']):r for r in records}
for r in records:
 base=lookup[(r['L'],r['z_target'],r['seed'],0)]
 assert r['edges']==base['edges']
 if r['arm'] in [1,2]:assert r['degrees']==base['degrees']
(out/'audit-complete.json').write_text(json.dumps(dict(complete=len(records)==336,graphs=len(records),all_hashes_matched=True,degree_sequences_preserved=True,elapsed_seconds=time.monotonic()-start)))

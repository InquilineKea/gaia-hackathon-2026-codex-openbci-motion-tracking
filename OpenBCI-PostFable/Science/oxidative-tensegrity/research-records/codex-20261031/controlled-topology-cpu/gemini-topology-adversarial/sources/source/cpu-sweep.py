import os,sys,json,time,hashlib,csv,math,argparse
from pathlib import Path
sys.path.insert(0,'/mnt/work/deps')
isolation=dict(home_hidden=not Path('/home/oxt').exists(),network_namespace_inode=os.readlink('/proc/self/ns/net'),dependency_mount_read_only=any(' /mnt/work/deps ' in line and 'ro,' in line for line in Path('/proc/mounts').read_text().splitlines()))
Path('/mnt/work/out/isolation.json').write_text(json.dumps(isolation))
assert isolation['home_hidden'] and isolation['dependency_mount_read_only']
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import cg
P=argparse.ArgumentParser();P.add_argument('--mode',choices=['benchmark','production'],required=True);a=P.parse_args();out=Path('/mnt/work/out');out.mkdir(exist_ok=True);start=time.monotonic()
def graph(L,z,seed,arm):
 rng=np.random.default_rng(seed);N=L*L;edges=[];steps=[(1,0),(0,1),(-1,1)]
 for i in range(N):
  x,y=i%L,i//L
  for d,(dx,dy) in enumerate(steps):edges.append((i,((y+dy)%L)*L+(x+dx)%L,d))
 E=np.array(edges);mask=np.zeros(3*N,dtype=bool)
 for d in range(3):mask[rng.choice(np.arange(d,3*N,3),min(N,round(z*N/6)),replace=False)]=True
 adj=[set() for _ in range(N)]
 def toggle(e,on):
  i,j,_=edges[e];common=len(adj[i]&adj[j]);mask[e]=on
  if on:adj[i].add(j);adj[j].add(i)
  else:adj[i].remove(j);adj[j].remove(i)
  return common if on else -common
 for e in np.where(mask)[0]:i,j,_=edges[e];adj[i].add(j);adj[j].add(i)
 lookup={tuple(sorted((i,j))):e for e,(i,j,d) in enumerate(edges)}
 def triangles():return sum(len(adj[i]&adj[j]) for i,j,d in edges if mask[lookup[tuple(sorted((i,j)))]])//3
 direction_counts=np.bincount(E[mask,2],minlength=3);before=[len(x) for x in adj];accepted=0;proposals=100*N if arm else 0
 for k in range(proposals):
  if arm in [1,2]:
   x,y=int(rng.integers(L)),int(rng.integers(L));ring=[((y+dy)%L)*L+(x+dx)%L for dx,dy in [(1,0),(0,1),(-1,1),(-1,0),(0,-1),(1,-1)]]
   es=[lookup[tuple(sorted((ring[t],ring[(t+1)%6])))] for t in range(6)]
   pattern=mask[es].copy()
   if not all(pattern[t]!=pattern[(t+1)%6] for t in range(6)):continue
   change=sum(toggle(e,not mask[e]) for e in es)
   beta=2 if arm==1 else -2
   if rng.random()<math.exp(min(0,beta*change)):accepted+=1
   else:
    for e in es:toggle(e,not mask[e])
  else:
   d=int(rng.integers(3));on=np.where(mask[d::3])[0]*3+d;off=np.where(~mask[d::3])[0]*3+d
   if not len(on) or not len(off):continue
   e,f=int(rng.choice(on)),int(rng.choice(off));nodes=set(edges[e][:2]+edges[f][:2]);old=sum(len(adj[i])**2 for i in nodes)
   toggle(e,False);toggle(f,True);new=sum(len(adj[i])**2 for i in nodes)
   if rng.random()<math.exp(min(0,.6*(new-old))):accepted+=1
   else:toggle(f,False);toggle(e,True)
 if arm in [1,2]:assert before==[len(x) for x in adj]
 assert np.array_equal(direction_counts,np.bincount(E[mask,2],minlength=3))
 assert int(mask.sum())==3*min(N,round(z*N/6))
 deg=np.array([len(x) for x in adj]);T=triangles();components=[];visited={};wrap=[False,False]
 for root in range(N):
  if root in visited:continue
  visited[root]=(0,0);queue=[root];count=0
  while queue:
   i=queue.pop();count+=1
   for j in adj[i]:
    e=lookup[tuple(sorted((i,j)))];u,v,d=edges[e];dx,dy=steps[d];sign=1 if i==u else -1;pos=(visited[i][0]+sign*dx,visited[i][1]+sign*dy)
    if j not in visited:visited[j]=pos;queue.append(j)
    else:
     diff=[pos[k]-visited[j][k] for k in range(2)];assert all(x%L==0 for x in diff)
     for k in range(2):wrap[k]|=diff[k]!=0
  components.append(count)
 sizes=sorted(components,reverse=True);small=sizes[1:];wedges=sum(int(k)*(int(k)-1)//2 for k in deg)
 local=[sum(v in adj[u] for u in adj[i] for v in adj[i] if u<v)/(len(adj[i])*(len(adj[i])-1)/2) if len(adj[i])>1 else 0 for i in range(N)]
 meta=dict(L=L,seed=seed,arm=arm,z_target=z,z_actual=float(deg.mean()),edges=int(mask.sum()),triangles=T,clustering=float(np.mean(local)),transitivity=3*T/wedges if wedges else 0,degree_variance=float(deg.var()),largest_component=max(sizes)/N,susceptibility=sum(s*s for s in small)/max(1,sum(small)),wrap_basis_1=wrap[0],wrap_basis_2=wrap[1],proposals=proposals,accepted=accepted,mask_sha256=hashlib.sha256(mask.tobytes()).hexdigest())
 return E,mask,meta

def mechanics(E,mask,L,kap,r,dt=.1):
 N=L*L;dirs=np.array([[1.,0],[.5,3**.5/2],[-.5,3**.5/2]]);active=np.where(mask)[0];rows=[];cols=[];vals=[];aff=[]
 for row,e in enumerate(active):
  i,j,d=E[e];v=dirs[d]
  for k in range(2):rows.extend([row,row]);cols.extend([2*i+k,2*j+k]);vals.extend([-v[k],v[k]])
  aff.append(v[0]*v[1])
 B=coo_matrix((vals,(rows,cols)),shape=(len(active),2*N)).tocsr();aff=np.array(aff);rows=[];cols=[];vals=[];nb=0
 for e in active:
  i,j,d=E[e];prev=int(np.where((E[:,1]==i)&(E[:,2]==d))[0][0])
  if not mask[prev]:continue
  h=E[prev,0];normal=np.array([-dirs[d,1],dirs[d,0]])
  for node,c in [(h,1),(i,-2),(j,1)]:
   for k in range(2):rows.append(nb);cols.append(2*node+k);vals.append(c*normal[k])
  nb+=1
 D=coo_matrix((vals,(rows,cols)),shape=(nb,2*N)).tocsr();H=(B.T@B+kap*(D.T@D)).tocsr();q=np.zeros(len(active));u=np.zeros(2*N);maxres=0.;fail=False
 if not hasattr(mechanics,'checked'):
  v=np.random.default_rng(9).normal(size=2*N)*.001;w=np.random.default_rng(10).normal(size=2*N);rhs0=B.T@(-.001*aff)
  def energy(x):return .5*float(x@(H@x))-float(rhs0@x)
  fd=(energy(v+1e-5*w)-energy(v-1e-5*w))/2e-5;analytic=float(w@(H@v-rhs0));err=abs(fd-analytic)
  translation=np.tile([.3,-.2],N);te=float(np.max(np.abs(H@translation)))
  assert err<1e-8 and te<1e-10
  (out/'cpu-selftest.json').write_text(json.dumps(dict(gradient_directional_error=err,translation_residual=te)))
  mechanics.checked=True
 def solve(gamma):
  nonlocal u,maxres,fail
  rhs=B.T@((1-r)*q-gamma*aff);u,info=cg(H,rhs,x0=u,rtol=1e-9,atol=1e-11,maxiter=6000);res=float(np.max(np.abs(H@u-rhs)));maxres=max(maxres,res);fail|=info!=0 or res>1e-8
  e=B@u+gamma*aff;stress=float(aff@(e-(1-r)*q))/(N*3**.5/2)
  return e,stress
 e,s=solve(.001);G=s/.001;e,s2=solve(.002);G2=s2/.002;u[:]=0;e,s0=solve(.1);trace=[dict(t=0,stress=s0,strain_rms=float(np.sqrt(np.mean(e*e))))]
 for step in range(round(5/dt)):
  if time.monotonic()-start>1800:fail=True;break
  q=e+(q-e)*np.exp(-dt*np.exp(np.minimum(30,10*np.abs(e-q)))) if r<1 else q
  e,s=solve(.1);trace.append(dict(t=(step+1)*dt,stress=s,strain_rms=float(np.sqrt(np.mean(e*e)))))
 return dict(kappa=kap,r=r,dt=dt,G0=G,Gcheck=G2,modulus_step_relative_difference=abs(G-G2)/max(abs(G),1e-15),retention=s/s0 if abs(s0)>1e-14 else None,matched_initial_stress=s0/G if G>1e-12 else None,matched_final_stress=s/G if G>1e-12 else None,max_force_residual=maxres,converged=not fail,completed_internal_time=trace[-1]['t'],bends=nb,trace=trace,homogeneous_relaxation_null_retention=math.exp(-5))

records=[];sizes=[8] if a.mode=='benchmark' else [12,18,24];seeds=range(2) if a.mode=='benchmark' else range(4);zs=[3.2,4.] if a.mode=='benchmark' else [1.2,1.6,2.,2.4,3.2,4.,4.8]
for L in sizes:
 for seed in seeds:
  for z in zs:
   for arm in ([0] if a.mode=='benchmark' else range(4)):
    if time.monotonic()-start>1800:break
    E,mask,meta=graph(L,z,(74000 if L==24 else 73000)+seed,arm)
    for kap in ([.03] if a.mode=='benchmark' else [.003,.03]):
     for r in [1.,.5]:
      result={**meta,**mechanics(E,mask,L,kap,r)};records.append(result)
      (out/(a.mode+'.json')).write_text(json.dumps(dict(mode=a.mode,elapsed_seconds=time.monotonic()-start,records=records)))
    print(json.dumps({**meta,'completed_cases':len(records),'elapsed_seconds':time.monotonic()-start}),flush=True)
(out/(a.mode+'-complete.json')).write_text(json.dumps(dict(complete=len(records)==(8 if a.mode=='benchmark' else 1344),cases=len(records),planned_cases=8 if a.mode=='benchmark' else 1344,elapsed_seconds=time.monotonic()-start)))

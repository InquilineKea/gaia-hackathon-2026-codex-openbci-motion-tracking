import sys,json,time
from pathlib import Path
sys.path.insert(0,'/mnt/work')
from model import graph,mechanics
out=Path('/mnt/work/out');start=time.monotonic();records=[];planned=384
for z in [3.2,4.,4.8]:
 for seed in range(74000,74004):
  for arm in range(4):
   E,mask,meta=graph(24,z,seed,arm)
   configs=[(k,10.,dt) for k in [.003,.03] for dt in [.1,.05,.025]]
   if arm in [0,3]:configs += [(k,b,.1) for k in [0.,.003,.03] for b in [0.,10.] if k==0. or b==0.]
   for k,b,dt in configs:
    if time.monotonic()-start>2320:raise TimeoutError('Control deadline')
    result={**meta,**mechanics(E,mask,24,k,.5,dt=dt,beta=b)};records.append(result)
    assert result['converged'] and result['completed_internal_time']==5.,'Numerical correctness gate failed'
    (out/'controls.json').write_text(json.dumps(dict(records=records,elapsed_seconds=time.monotonic()-start)))
   print(json.dumps(dict(z=z,seed=seed,arm=arm,cases=len(records),elapsed_seconds=time.monotonic()-start)),flush=True)
assert len(records)==planned
(out/'controls-complete.json').write_text(json.dumps(dict(complete=True,cases=len(records),planned_cases=planned,elapsed_seconds=time.monotonic()-start)))

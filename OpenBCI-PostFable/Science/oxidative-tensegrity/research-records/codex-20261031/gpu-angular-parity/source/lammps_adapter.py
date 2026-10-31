"""Optional single-rank GPU angular callback for the commissioned 2D exporter.
Not enabled automatically. CPU/GPU device parity must pass before production use.
Native angle coefficients must remain zero. No full network/GPU speed claim.
"""
import json,math,pathlib
import numpy as np
if __package__:
    from .backend import GPU
else:
    from backend import GPU
class CudaAngularController:
    def __init__(self,lmp,meta,ptx):
        self.lmp=lmp;self.error=None;self.meta=meta;self.N=len(meta['reference_positions'])
        self.terms=meta['angle_terms'];self.nodes=[t['nodes'] for t in self.terms]
        self.gpu=GPU(pathlib.Path(ptx).read_bytes());lmp.set_fix_external_callback('anglelaw',self.callback)
    def callback(self,caller,step,nlocal,tags,x,fexternal):
        try:
            if nlocal!=self.N:raise ValueError('one MPI rank required')
            ids=np.asarray(tags,dtype=int)-1
            if len(np.unique(ids))!=self.N or np.min(ids)!=0 or np.max(ids)!=self.N-1:raise ValueError('unexpected atom tags')
            inverse=np.empty(self.N,int);inverse[ids]=np.arange(nlocal);xx=np.asarray(x)[inverse,:2]
            lo,hi,xy,yz,xz,periodic,changed=self.lmp.extract_box();H=np.array([[hi[0]-lo[0],xy],[0.,hi[1]-lo[1]]]);inv=np.linalg.inv(H)
            terms=[]
            for t in self.terms:
                a,c,b=t['nodes'];da=xx[a]-xx[c];db=xx[b]-xx[c]
                da=(da@inv.T-np.rint(da@inv.T))@H.T;db=(db@inv.T-np.rint(db@inv.T))@H.T
                bend=t['theta0_degrees']==180
                terms.append([*da,0.,*db,0.,t['stiffness'],0. if bend else math.pi/3,-1. if bend else 1.,1.,0.,1.])
            result=self.gpu.evaluate(terms,self.nodes,self.N);E,*tail=result['totals'];V=tail[:9];invalid=tail[9]
            if invalid or not np.isfinite(E) or not np.all(np.isfinite(result['forces'])):raise ValueError('invalid GPU angular state')
            fexternal[:]=np.asarray(result['forces']).reshape(self.N,3)[ids]
            self.lmp.fix_external_set_energy_global('anglelaw',E)
            self.lmp.fix_external_set_virial_global('anglelaw',[V[j] for j in (0,4,8,1,2,5)])
        except Exception as exc:
            self.error=type(exc).__name__+': '+str(exc);fexternal[:]=np.nan
            self.lmp.fix_external_set_energy_global('anglelaw',float('nan'))
    def close(self):self.gpu.close()

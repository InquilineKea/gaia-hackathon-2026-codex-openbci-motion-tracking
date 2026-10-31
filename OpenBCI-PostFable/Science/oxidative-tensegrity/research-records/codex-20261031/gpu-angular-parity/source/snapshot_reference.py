"""Run only inside the previously reviewed isolated GCP NumPy environment."""
import sys,json,pathlib,math
ROOT=pathlib.Path('/mnt/work');sys.path[:0]=[str(ROOT/'src'),'/mnt/reference',str(ROOT/'deps')]
import numpy as np
from lammps_export import AngularController
class Fake:
    def __init__(self,H):self.H=H
    def set_fix_external_callback(self,*args):pass
    def extract_box(self):return [0.,0.,-.5],[self.H[0,0],self.H[1,1],.5],self.H[0,1],0.,0.,[1,1,1],0
    def fix_external_set_energy_global(self,name,E):self.E=E
    def fix_external_set_virial_global(self,name,V):self.V=V
frames=[]
for folder in ('regenerated-W8','regenerated-W32'):
    for meta_path in sorted((pathlib.Path('/mnt/reference/out')/folder).glob('*.meta.json')):
        meta=json.loads(meta_path.read_text());x0=np.array(meta['reference_positions']);L=np.array(meta['box_lengths']) if 'box_lengths' in meta else None
        # Sidecar schema has box lengths under box; fail explicitly on schema drift.
        if L is None:L=np.array(meta['box'])[:2]
        for F in (np.array([[1.,.03],[0.,1.]]),np.array([[1.8,1.2],[0.,.6]])):
            H=F@np.diag(L);xx=x0@F.T
            xx+=np.random.default_rng(2026).normal(0.,.001,xx.shape)
            fake=Fake(H);ctrl=AngularController(fake,meta);force=np.zeros((len(xx),3));coords=np.column_stack([xx,np.zeros(len(xx))]);tags=np.arange(1,len(xx)+1)
            ctrl.callback(None,0,len(xx),tags,coords,force)
            if ctrl.error:raise ValueError(ctrl.error)
            terms=[];nodes=[]
            for term in meta['angle_terms']:
                ia,ic,ib=term['nodes'];a=xx[ia]-xx[ic];b=xx[ib]-xx[ic]
                a=(a@np.linalg.inv(H).T-np.rint(a@np.linalg.inv(H).T))@H.T
                b=(b@np.linalg.inv(H).T-np.rint(b@np.linalg.inv(H).T))@H.T
                bend=term['theta0_degrees']==180
                terms.append([*a,0.,*b,0.,term['stiffness'],0. if bend else math.pi/3,-1. if bend else 1.,1.,0.,1.]);nodes.append([ia,ic,ib])
            frames.append(dict(name=folder+'/'+meta_path.stem+('/severe' if F[0,0]>1 else '/shear'),F=F.tolist(),terms=terms,nodes=nodes,nn=len(xx),expected_energy=fake.E,expected_forces=force.reshape(-1).tolist(),expected_virial=fake.V))
(ROOT/'snapshots.json').write_text(json.dumps(frames,separators=(',',':')))
print(json.dumps(dict(frames=len(frames),terms=sum(len(f['terms']) for f in frames))))

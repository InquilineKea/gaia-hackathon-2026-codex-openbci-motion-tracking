"""Original stdlib-only readback; reads saved coordinates without running MD."""
import ast,json,math,statistics,struct
from pathlib import Path

base=Path('outputs/collagen-candidate-publication-20261031')
def npy(path):
 raw=path.read_bytes();assert raw[:6]==b'\x93NUMPY'
 n=struct.unpack('<H' if raw[6]==1 else '<I',raw[8:10] if raw[6]==1 else raw[8:12])[0];off=(10 if raw[6]==1 else 12)+n
 h=ast.literal_eval(raw[10:off].decode() if raw[6]==1 else raw[12:off].decode());assert h['descr']=='<f8' and not h['fortran_order']
 v=struct.unpack('<'+str(math.prod(h['shape']))+'d',raw[off:]);assert all(math.isfinite(x) for x in v)
 coords=[list(v[i:i+3]) for i in range(0,len(v),3)]
 if len(h['shape'])==2:return coords
 n=h['shape'][1];return [coords[i:i+n] for i in range(0,len(coords),n)]
def sub(a,b):return [x-y for x,y in zip(a,b)]
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def norm(a):return math.sqrt(dot(a,a))
def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def oop(x,center,left,right,tip):
 n=cross(sub(x[left],x[center]),sub(x[right],x[center]));v=sub(x[tip],x[center])
 return math.degrees(math.asin(min(1,abs(dot(n,v))/(norm(n)*norm(v)))))
def dihedral(x,inds):
 p=[x[i] for i in inds];b0=sub(p[0],p[1]);b1=sub(p[2],p[1]);b2=sub(p[3],p[2]);b1=[a/norm(b1) for a in b1]
 v=[a-dot(b0,b1)*b for a,b in zip(b0,b1)];w=[a-dot(b2,b1)*b for a,b in zip(b2,b1)]
 return math.degrees(math.atan2(dot(cross(b1,v),w),dot(v,w)))

records=[]
for case in ['DITY_CONTROL','DITY_LINKED']:
 d=json.loads((base/'prepared'/case/(case+'.json')).read_text());rids=[next(i for i,r in enumerate(d['residues']) if r['id']==j and r['name']=='TYR') for j in [4,6]]
 def find(ri,name):return next(i for i,a in enumerate(d['atoms']) if a['resindex']==ri and a['name']==name)
 ce2=[find(ri,'CE2') for ri in rids];cz=[find(ri,'CZ') for ri in rids]
 initial=[a['xyz'] for a in d['atoms']]
 for replica in range(3):
  root=base/'retrieved/attempt-002/run'/case/('replica_'+str(replica));frames=npy(root/'solute_frames_nm.npy');assert len(frames)==50
  tail=frames[20:];planes={};angles=[]
  for j,ri in enumerate(rids):
   center=find(ri,'CE2');tip=ce2[1-j] if case=='DITY_LINKED' else find(ri,'HE2')
   planes['Tyr'+str([4,6][j])+':CE2']=[oop(x,center,find(ri,'CD2'),find(ri,'CZ'),tip) for x in tail]
   planes['Tyr'+str([4,6][j])+':CZ']=[oop(x,find(ri,'CZ'),find(ri,'CE1'),find(ri,'CE2'),find(ri,'OH')) for x in tail]
  for x in tail:angles.append(dihedral(x,[cz[0],ce2[0],ce2[1],cz[1]]))
  records.append({'model':case,'replica':replica,'initial_site_CE2_distance_A':math.dist(initial[ce2[0]],initial[ce2[1]]),'free_tail_frames':30,
   'out_of_plane_angle_degrees':{k:{'mean':statistics.mean(v),'max':max(v)} for k,v in planes.items()},
   'central_site_dihedral_degrees_raw_range':[min(angles),max(angles)],
   'linked_bond_mean_A':statistics.mean(10*math.dist(x[ce2[0]],x[ce2[1]]) for x in tail) if case=='DITY_LINKED' else None})

d=json.loads((base/'prepared/GLU_CONTROL/GLU_CONTROL.json').read_text())
ri=[next(i for i,r in enumerate(d['residues']) if r.get('source',{}).get('published_source_index')==j) for j in [5084,5718]]
lys=[a for a in d['atoms'] if a['resindex']==ri[0] and a['name']=='NZ'][0]
arg=[a for a in d['atoms'] if a['resindex']==ri[1] and a['name'] in ['NE','CZ','NH1','NH2']]
result={'scope':'New coordinate-only analysis of existing inputs/trajectories, not a new simulation, pKa validation, force-field fit or chemical site validation.',
 'geometry_definition':'Out-of-plane angle is asin of the absolute projection of a third substituent bond on the normal of the plane defined by the two aromatic ring bonds. It is a diagnostic angle, not a fitted improper potential or an energetic/chemical validity threshold.',
 'DITY_records':records,'GLU_CONTROL_initial_LYS_NZ_to_ARG_guanidino_distances_A':{a['name']:math.dist(lys['xyz'],a['xyz']) for a in arg},
 'review_claim_disposition':['DITY starting CE2-CE2 separation of 8.6303945 A is confirmed directly. This does not prove a final artifact or biological site assignment.','The old linked AGS-LGX bond length of 1.457875 A is not the restored ARG-LYS separation in GLU_CONTROL.','No causal assignment of replica differences to precision is possible because seed and precision were changed together.','A harmonic bond term retained on a constrained pair is not by itself a confirmed double-counting defect. No force-field term should be deleted solely on this reviewer assertion.','Absolute stereochemical assignment and microstate validation require additional chemical evidence; relative sign retention does not establish them.']}
Path('outputs/collagen-argon-swarm-20261031/ADDITIONAL_GEOMETRY_READBACK.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'linked_initial_distance_A':records[3]['initial_site_CE2_distance_A'],'max_linked_out_of_plane_angle_degrees':max(x['max'] for r in records if r['model']=='DITY_LINKED' for x in r['out_of_plane_angle_degrees'].values()),'control_initial_LYS_NZ_to_ARG_guanidino_distances_A':result['GLU_CONTROL_initial_LYS_NZ_to_ARG_guanidino_distances_A']}))

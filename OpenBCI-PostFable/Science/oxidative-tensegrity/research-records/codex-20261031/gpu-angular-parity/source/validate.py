"""CPU differential tests; optional bounded CUDA parity. Stdlib only."""
import argparse, json, math, pathlib, random, time, hashlib
from backend import cpu, reference, GPU, compile_ptx, csr

def cases():
    rng=random.Random(20261031);terms=[];labels=[]
    for mode in range(4):
        for j in range(200):
            if mode<=1:
                theta=rng.uniform(.15,2.8) if mode==0 else rng.uniform(-2.9,2.9)
                phi=rng.uniform(-2.,2.);a=[math.cos(phi),math.sin(phi),0.];b=[math.cos(phi+theta),math.sin(phi+theta),0.]
            else:
                a=[rng.uniform(-1.,1.) for _ in range(3)];b=[rng.uniform(-1.,1.) for _ in range(3)]
            a=[x*rng.uniform(.7,1.7) for x in a];b=[x*rng.uniform(.7,1.7) for x in b]
            # Include actual crosslink-rest geometries, noncollinear 3D bending.
            rest=math.pi/3 if mode==0 else (rng.uniform(-2.,2.) if mode==1 else (rng.choice([-.5,0.,.5,1.]) if mode==2 else 0.))
            sa=rng.choice([-1.,1.]) if mode>=2 else 1.;sb=rng.choice([-1.,1.]) if mode>=2 else 1.
            terms.append(a+b+[10**rng.uniform(-3,2),rest,sa,sb,float(mode),1.]);labels.append('random-'+str(mode))
    for th in (1e-12,1e-9,1e-6,1e-3,.02):
        for mode in (0,3):
            terms.append([1.,0.,0.,math.cos(th),math.sin(th),0.,2.,0.,1.,1.,float(mode),1.]);labels.append('near-straight')
    for mode in range(4):
        p=[1.,0.,0.,.5,.8,0.,3.,.4,1.,1.,float(mode),0.];terms.append(p);labels.append('dead')
    terms.append([1.,0.,0.,1.,0.,0.,2.,0.,1.,1.,3.,1.]);labels.append('straight-3d')
    # Actual 2D incoming bend representation and reverse signed branch.
    for th in (-.2,-1e-8,.1):
        terms.append([-1.,0.,0.,math.cos(th),math.sin(th),0.,.7,0.,-1.,1.,0.,1.]);labels.append('incoming-bend')
    return terms,labels

def discrepancy(a,b):return max((abs(x-y)/(1+abs(x)+abs(y)) for x,y in zip(a,b)),default=0.)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--cpu-library',required=True);ap.add_argument('--output',required=True);ap.add_argument('--nvrtc');ap.add_argument('--gpu',action='store_true');ap.add_argument('--compile-only',action='store_true');args=ap.parse_args()
    terms,labels=cases();out=cpu(terms,args.cpu_library);checks=[];metrics={}
    def check(name,passed,**data):checks.append(dict(name=name,passed=bool(passed),**data))
    check('all legal terms accepted',all(row[19]==0 and all(math.isfinite(v) for v in row) for row in out))
    errs=[discrepancy(o,reference(p)) for p,o,label in zip(terms,out,labels) if label!='near-straight']
    metrics['independent_reference_max_scaled']=max(errs);check('independent scalar reference',max(errs)<2e-12)
    fd=0.;stressfd=0.;balance=0.;torque=0.
    for p,o,label in zip(terms,out,labels):
        if label.startswith('random'):
            for coord in range(6):
                h=1e-4;points=[]
                for mult in (2,1,-1,-2):
                    q=p.copy();q[coord]+=mult*h;points.append(q)
                energies=[r[0] for r in cpu(points,args.cpu_library)];grad=(-energies[0]+8*energies[1]-8*energies[2]+energies[3])/(12*h)
                force=o[1+coord] if coord<3 else o[7+coord-3]
                fd=max(fd,abs(grad+force)/(1+abs(grad)+abs(force)))
            # Virtual affine deformation: dE/dF_j_i = -virial_i_j.
            for i in range(3):
                for j in range(3):
                    h=1e-4;points=[]
                    if p[10]<=1 and j==2:continue
                    for mult in (2,1,-1,-2):
                        q=p.copy();q[j]+=mult*h*p[i];q[3+j]+=mult*h*p[3+i];points.append(q)
                    energies=[r[0] for r in cpu(points,args.cpu_library)];der=(-energies[0]+8*energies[1]-8*energies[2]+energies[3])/(12*h);v=o[10+3*i+j]
                    stressfd=max(stressfd,abs(der+v)/(1+abs(der)+abs(v)))
        for d in range(3):balance=max(balance,abs(o[1+d]+o[4+d]+o[7+d]))
        a,b=p[:3],p[3:6];fa,fb=o[1:4],o[7:10]
        for i,j in ((0,1),(1,2),(2,0)):torque=max(torque,abs(a[i]*fa[j]-a[j]*fa[i]+b[i]*fb[j]-b[j]*fb[i]))
    metrics.update(force_fd_max_scaled=fd,virial_fd_max_scaled=stressfd,net_force_max_abs=balance,net_torque_max_abs=torque)
    check('force finite differences',fd<2e-8);check('affine virial finite differences',stressfd<2e-8)
    check('translation conservation',balance<1e-12);check('rotation conservation',torque<1e-11)
    check('broken terms exactly zero',all(all(x==0 for x in o) for o,l in zip(out,labels) if l=='dead'))
    check('small bending force has no sine floor',all(abs(o[2]-2*p[4])<1e-12 for p,o,l in zip(terms,out,labels) if l=='near-straight' and p[10]==0 and p[4]<1e-5))
    bad=[]
    for p in (terms[0],terms[400],terms[600]):
        q=p.copy();q[:3]=[0.,0.,0.];bad.append(q)
    bad.append([1.,0.,0.,0.,-1.,0.,1.,math.pi/3,1.,1.,0.,1.])
    q=terms[0].copy();q[6]=-1.;bad.append(q)
    q=terms[0].copy();q[0]=float('nan');bad.append(q)
    bad.append([1.,0.,0.,-1.,0.,0.,1.,0.,1.,1.,3.,1.])
    check('invalid geometry and branch rejection',all(o[19]!=0 and math.isnan(o[0]) for o in cpu(bad,args.cpu_library)))
    ptx=None
    if args.nvrtc:
        ptx,log=compile_ptx(args.nvrtc);metrics['ptx_sha256']=hashlib.sha256(ptx).hexdigest();metrics['compiler_log']=log
        pathlib.Path(args.output).with_suffix('.ptx').write_bytes(ptx);check('NVRTC CUDA compile',True)
    if args.gpu:
        if ptx is None:raise ValueError('--gpu requires --nvrtc')
        gpu=GPU(ptx)
        try:
            # Shared-center graph exercises nontrivial scatter and repeated roles.
            nodes=[(i%17,17,(i*7+3)%17) for i in range(len(terms))];nn=18
            got=gpu.evaluate(terms,nodes,nn);diff=max(discrepancy(a,b) for a,b in zip(out,got['terms']))
            check('GPU per-term CPU parity',diff<2e-11,max_scaled=diff)
            fs=[0.]*(3*nn)
            for row,triple in zip(out,nodes):
                for role,node in enumerate(triple):
                    for d in range(3):fs[3*node+d]+=row[1+3*role+d]
            check('GPU CSR force assembly',discrepancy(fs,got['forces'])<2e-11)
            totals=[sum(row[0] for row in out)]+[sum(row[10+j] for row in out) for j in range(9)]+[0.]
            check('GPU energy and full virial reductions',discrepancy(totals,got['totals'])<2e-11)
            repeat=gpu.evaluate(terms,nodes,nn);check('GPU deterministic repeat',repeat==got)
            # New mask, same geometry; no topology rebuild needed.
            damaged=[p[:11]+[0. if i%3==0 else p[11]] for i,p in enumerate(terms)]
            ref=cpu(damaged,args.cpu_library);res=gpu.evaluate(damaged,nodes,nn)
            check('GPU frozen-damage mask parity',max(discrepancy(a,b) for a,b in zip(ref,res['terms']))<2e-11)
            invalid=gpu.evaluate(bad,[(0,1,2)]*len(bad),3)
            check('GPU invalid terms counted',invalid['totals'][10]==len(bad) and math.isnan(invalid['totals'][0]))
            zero=gpu.evaluate([],[],3);check('GPU empty topology',all(x==0 for x in zero['forces']+zero['totals']))
            # Device construction of explicit periodic arms and fixed-x dE/dF.
            F=[1.8,1.2,0.,0.,.6,0.,0.,0.,.8];images=[];positions=[];triples=[]
            for t,p in enumerate(terms[:800]):
                im=[.1,.2,0.,-.1,.1,0.];images.append(im)
                center=[0.,0.,0.];a=[p[d]-sum(F[3*d+j]*im[j] for j in range(3)) for d in range(3)];b=[p[3+d]-sum(F[3*d+j]*im[3+j] for j in range(3)) for d in range(3)]
                positions.extend([a,center,b]);triples.append((3*t,3*t+1,3*t+2))
            geom=gpu.geometry(positions,triples,images,F,[p[6:] for p in terms[:800]])
            check('GPU periodic arm construction',discrepancy(geom['inputs'],[v for p in terms[:800] for v in p])<2e-13)
            check('GPU built-geometry angular parity',discrepancy(geom['terms'],[v for row in out[:800] for v in row])<2e-11)
            expected=[]
            for row,im in zip(out,images):
                expected.extend([-row[1+i]*im[j]-row[7+i]*im[3+j] for i in range(3) for j in range(3)])
            check('GPU fixed-coordinate deformation derivative',discrepancy(geom['dEdF'],expected)<2e-11)

        finally:gpu.close()
    report=dict(schema=1,case_count=len(terms),checks=checks,passed=all(c['passed'] for c in checks),metrics=metrics,gpu_executed=args.gpu)
    pathlib.Path(args.output).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
    if not report['passed']:raise SystemExit(1)
if __name__=='__main__':main()

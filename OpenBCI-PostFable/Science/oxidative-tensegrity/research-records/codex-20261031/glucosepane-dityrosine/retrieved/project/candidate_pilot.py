"""Original bounded paired chemistry pilot; execute only in reviewed isolation."""
import collections,gc,io,json,math,random,time,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
import openmm as mm
from openmm import unit as u
from openmm.app import Topology,ForceField,Modeller,PDBxFile,GromacsTopFile,element,NoCutoff,PME,HBonds

ROOT=Path('/project');OUT=Path('/results/run');OUT.mkdir(exist_ok=False)
CASES=['GLU_CONTROL','GLU_LINKED','DITY_CONTROL','DITY_LINKED']
SEED=20261101
def dump(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def nb(s):return next(f for f in s.getForces() if isinstance(f,mm.NonbondedForce))
def topology(d):
    t=Topology();chains={};rs=[];ats=[]
    for r in d['residues']:
        c=r.get('chain','A')
        if c not in chains:chains[c]=t.addChain(c)
        rs.append(t.addResidue(r['name'],chains[c],str(r['id'])))
    for a in d['atoms']:ats.append(t.addAtom(a['name'],element.get_by_symbol(a['element']),rs[a['resindex']]))
    for i,j in d['bonds']:t.addBond(ats[i],ats[j])
    return t
def amber_system(d):
    s=mm.System();bond=mm.HarmonicBondForce();angle=mm.HarmonicAngleForce();proper=mm.PeriodicTorsionForce();improper=mm.PeriodicTorsionForce();non=mm.NonbondedForce()
    for a in d['atoms']:s.addParticle(a['mass']);non.addParticle(a['q'],a['sigma'],a['epsilon'])
    for i,j,r,k in d['terms']['bonds']:bond.addBond(i,j,r,k)
    for i,j,k,t,v in d['terms']['angles']:angle.addAngle(i,j,k,math.radians(t),v)
    for name,force in [('proper',proper),('improper',improper)]:
        for i,j,k,l,phase,v,n in d['terms'][name]:
            if v==0:continue
            assert n>0;force.addTorsion(i,j,k,l,n,math.radians(phase),v)
    for i,j,qq,lj in d['terms']['exceptions']:
        a,b=d['atoms'][i],d['atoms'][j];non.addException(i,j,a['q']*b['q']*qq,(a['sigma']+b['sigma'])/2,math.sqrt(a['epsilon']*b['epsilon'])*lj)
    for f in (bond,angle,proper,improper,non):s.addForce(f)
    return s
def context(s,platform='CUDA',seed=SEED,temperature=310):
    it=mm.LangevinMiddleIntegrator(temperature*u.kelvin,1/u.picosecond,.001*u.picosecond);it.setRandomNumberSeed(seed);it.setConstraintTolerance(1e-6)
    props={'Precision':'double','DeterministicForces':'true'} if platform=='CUDA' else {'Threads':'2'} if platform=='CPU' else {}
    return mm.Context(s,it,mm.Platform.getPlatformByName(platform),props),it
def energy_forces(s,x,platform):
    c,i=context(s,platform);c.setPositions(x);st=c.getState(getEnergy=True,getForces=True)
    e=float(st.getPotentialEnergy()/u.kilojoule_per_mole);f=st.getForces(asNumpy=True).value_in_unit(u.kilojoule_per_mole/u.nanometer)
    del c,i;gc.collect();return e,f
def centers(d):
    adj=[set() for _ in d['atoms']]
    for i,j in d['bonds']:adj[i].add(j);adj[j].add(i)
    return [(i,sorted(j for j in ns if d['atoms'][j]['element']!='H')[:3]) for i,ns in enumerate(adj) if len(ns)==4 and d['atoms'][i]['element']=='C' and sum(d['atoms'][j]['element']!='H' for j in ns)>=3]
def signs(x,cs):return np.array([np.linalg.det(x[js]-x[i]) for i,js in cs])
def chemical_bond_parameters(s,d):
    pairs={tuple(sorted(p)) for p in d['bonds']};out=[]
    for f in s.getForces():
        if isinstance(f,mm.HarmonicBondForce):
            for k in range(f.getNumBonds()):
                i,j,r,v=f.getBondParameters(k)
                if tuple(sorted((i,j))) in pairs:out.append([i,j,float(r/u.nanometer)])
    assert len(out)==len(pairs),(len(out),len(pairs))
    return out
def prepare(case):
    path=ROOT/'prepared'/case;d=json.loads((path/(case+'.json')).read_text());folder=OUT/case;folder.mkdir()
    t=topology(d);x=np.array([a['xyz'] for a in d['atoms']])*.1;x-=x.mean(0);cs=centers(d);sg=signs(x,cs)
    assert np.min(abs(sg))>1e-8,'Degenerate stereocenter seed'
    if case.startswith('GLU'):
        s=amber_system(d);ff=None
    else:
        ff=ForceField(str(ROOT/'parameters/charmm36_dity.xml'),'charmm36/water.xml')
        s=ff.createSystem(t,nonbondedMethod=NoCutoff,constraints=None,rigidWater=False,removeCMMotion=False)
    physical_xml=mm.XmlSerializer.serialize(s);bonds=chemical_bond_parameters(s,d)
    rest=mm.CustomExternalForce('0.5*k*((x-x0)^2+(y-y0)^2+(z-z0)^2)');rest.addGlobalParameter('k',1000.)
    for name in ('x0','y0','z0'):rest.addPerParticleParameter(name)
    for i,a in enumerate(d['atoms']):
        if a['name'] in ('N','CA','C','O'):rest.addParticle(i,x[i])
    s.addForce(rest);c,it=context(s,'Reference');c.setPositions(x);start=time.monotonic()
    mm.LocalEnergyMinimizer.minimize(c,20.,2000)
    xx=c.getState(getPositions=True).getPositions(asNumpy=True).value_in_unit(u.nanometer);del c,it;gc.collect()
    phys=mm.XmlSerializer.deserialize(physical_xml);er,fr=energy_forces(phys,xx,'Reference');eg,fg=energy_forces(phys,xx,'CUDA')
    compare={'energy_difference_per_atom':abs(er-eg)/len(x),'force_rms':float(np.sqrt(np.mean((fr-fg)**2)))}
    compare['pass']=compare['energy_difference_per_atom']<1e-4 and compare['force_rms']<.01
    errors=[abs(np.linalg.norm(xx[i]-xx[j])-r)*10 for i,j,r in bonds]
    inversions=int(np.sum(signs(xx,cs)*sg<0));finite=bool(np.isfinite(xx).all() and np.isfinite(fr).all() and math.isfinite(er))
    cross=None
    if case.startswith('GLU'):
        source=GromacsTopFile(str(path/(case+'.source.top')),includeDir=str(ROOT/'parameters/amber99sb-star-ildnp.ff'))
        other=source.createSystem(nonbondedMethod=NoCutoff,constraints=None,rigidWater=False,removeCMMotion=False)
        eo,fo=energy_forces(other,xx,'Reference');cross={'energy_difference_per_atom':abs(er-eo)/len(x),'force_rms':float(np.sqrt(np.mean((fr-fo)**2)))}
        cross['pass']=cross['energy_difference_per_atom']<1e-5 and cross['force_rms']<.01
    q=sum(float(nb(phys).getParticleParameters(i)[0]/u.elementary_charge) for i in range(phys.getNumParticles()))
    report={'model':case,'atoms':len(x),'charge_e':q,'finite':finite,'stereocenters':len(cs),'stereocenter_inversions':inversions,'max_chemical_bond_deviation_A':max(errors),'reference_cuda':compare,'source_gromacs_reader':cross,'preparation_seconds':time.monotonic()-start}
    report['pass']=finite and inversions==0 and max(errors)<.4 and compare['pass'] and (cross is None or cross['pass'])
    dump(folder/'dry-check.json',report);np.save(folder/'dry_positions_nm.npy',xx,allow_pickle=False);(folder/'dry_system.xml').write_text(physical_xml)
    assert report['pass'],report
    return {'d':d,'top':t,'x':xx,'phys':phys,'ff':ff,'folder':folder,'centers':cs,'signs':signs(xx,cs),'bonds':bonds}
def radius_ff(d):
    r=ET.Element('ForceField');types=ET.SubElement(r,'AtomTypes');rs=ET.SubElement(r,'Residues');non=ET.SubElement(r,'NonbondedForce',coulomb14scale='.8333333333333334',lj14scale='.5');templates=[]
    for ri,res in enumerate(d['residues']):templates.append(ET.SubElement(rs,'Residue',name='R'+str(ri)))
    for i,a in enumerate(d['atoms']):
        typ='P'+str(i);ET.SubElement(types,'Type',name=typ,**{'class':typ,'element':a['element'],'mass':str(a['mass'])});ET.SubElement(templates[a['resindex']],'Atom',name=a['name'],type=typ);ET.SubElement(non,'Atom',type=typ,charge=str(a['q']),sigma=str(a['sigma']),epsilon=str(a['epsilon']))
    for i,j in d['bonds']:
        a,c=d['atoms'][i],d['atoms'][j]
        if a['resindex']==c['resindex']:ET.SubElement(templates[a['resindex']],'Bond',atomName1=a['name'],atomName2=c['name'])
        else:
            for v in (a,c):ET.SubElement(templates[v['resindex']],'ExternalBond',atomName=v['name'])
    return ET.tostring(r,encoding='unicode')
def amber_solvent_parameters():
    t=Topology();c=t.addChain();r=t.addResidue('HOH',c);o=t.addAtom('O',element.oxygen,r);a=t.addAtom('H1',element.hydrogen,r);b=t.addAtom('H2',element.hydrogen,r);t.addBond(o,a);t.addBond(o,b)
    for name,e in [('NA',element.sodium),('CL',element.chlorine)]:t.addAtom(name,e,t.addResidue(name,c))
    s=ForceField('amber14/tip3p.xml').createSystem(t,rigidWater=True,removeCMMotion=False);n=nb(s);out={}
    for name,ids in [('HOH',[0,1,2]),('NA',[3]),('CL',[4])]:out[name]=[[float(s.getParticleMass(i)/u.dalton),float(n.getParticleParameters(i)[0]/u.elementary_charge),float(n.getParticleParameters(i)[1]/u.nanometer),float(n.getParticleParameters(i)[2]/u.kilojoule_per_mole)] for i in ids]
    out['constraints']=[[int(i),int(j),float(d/u.nanometer)] for i,j,d in (s.getConstraintParameters(k) for k in range(s.getNumConstraints()))];return out
def solvate(case,m):
    d=m['d'];x=m['x'];n=len(x);center=x.mean(0);_,rot=np.linalg.eigh((x-center).T@(x-center))
    if np.linalg.det(rot)<0:rot[:,0]*=-1
    x=(x-center)@rot;box=np.ptp(x,axis=0)+2.4;x+=1.2-x.min(0);random.seed(SEED)
    ff=m['ff'] or ForceField('amber14/tip3p.xml',io.StringIO(radius_ff(d)))
    modeller=Modeller(m['top'],x*u.nanometer);kwargs={}
    if m['ff'] is None:kwargs['residueTemplates']={r:'R'+str(i) for i,r in enumerate(m['top'].residues())}
    modeller.addSolvent(ff,model='tip3p',boxSize=mm.Vec3(*box)*u.nanometer,ionicStrength=.15*u.molar,neutralize=True,**kwargs)
    xx=np.asarray(modeller.positions.value_in_unit(u.nanometer));assert len(xx)<100000
    counts=collections.Counter(r.name for r in modeller.topology.residues() if next(r.atoms()).index>=n)
    if m['ff'] is not None:
        s=ff.createSystem(modeller.topology,nonbondedMethod=PME,nonbondedCutoff=1*u.nanometer,constraints=HBonds,rigidWater=True,removeCMMotion=False,ewaldErrorTolerance=1e-5)
    else:
        s=mm.XmlSerializer.deserialize(mm.XmlSerializer.serialize(m['phys']));non=nb(s);water=amber_solvent_parameters()
        for i,j,r in m['bonds']:
            if 'H' in (d['atoms'][i]['element'],d['atoms'][j]['element']):s.addConstraint(i,j,r)
        for r in modeller.topology.residues():
            ids=[a.index for a in r.atoms()]
            if ids[0]<n:continue
            for i,p in zip(ids,water[r.name]):assert s.addParticle(p[0])==i;non.addParticle(*p[1:])
            if r.name=='HOH':
                for i,j,length in water['constraints']:s.addConstraint(ids[i],ids[j],length)
                for i,j in ((0,1),(0,2),(1,2)):non.addException(ids[i],ids[j],0,1,0)
        non.setNonbondedMethod(mm.NonbondedForce.PME);non.setCutoffDistance(1.);non.setEwaldErrorTolerance(1e-5);non.setUseDispersionCorrection(True)
        s.setDefaultPeriodicBoxVectors(*[mm.Vec3(*(np.eye(3)[i]*box))*u.nanometer for i in range(3)])
    q=sum(float(nb(s).getParticleParameters(i)[0]/u.elementary_charge) for i in range(len(xx)));assert abs(q)<1e-4
    p=m['folder'];np.save(p/'wet_positions_nm.npy',xx,allow_pickle=False);(p/'wet_system.xml').write_text(mm.XmlSerializer.serialize(s))
    with (p/'solvated.cif').open('w') as f:PDBxFile.writeFile(modeller.topology,xx*u.nanometer,f)
    dump(p/'solvation.json',{'atoms':len(xx),'solute_atoms':n,'counts':dict(counts),'box_nm':box.tolist(),'net_charge_e':q,'rotation_determinant':float(np.linalg.det(rot)),'requested_salt_M':.15,'force_field_family':'Amber99/ColBuilder' if case.startswith('GLU') else 'CHARMM36/CGenFF','solvent':'TIP3P/Joung-Cheatham' if case.startswith('GLU') else 'CHARMM modified TIP3P and native ion parameters'})
    m.update(wet=s,wet_x=xx);return m
def run(case,m,replica):
    p=m['folder']/('replica_'+str(replica));p.mkdir();s=mm.XmlSerializer.deserialize(mm.XmlSerializer.serialize(m['wet']));x=m['wet_x'];n=len(m['d']['atoms']);seed=SEED+CASES.index(case)*100+replica
    rest=mm.CustomExternalForce('0.5*k*periodicdistance(x,y,z,x0,y0,z0)^2');rest.addGlobalParameter('k',1000.)
    for a in ('x0','y0','z0'):rest.addPerParticleParameter(a)
    for i,a in enumerate(m['d']['atoms']):
        if a['element']!='H':rest.addParticle(i,x[i])
    s.addForce(rest);baro=mm.MonteCarloBarostat(1*u.bar,310*u.kelvin,0);baro.setRandomNumberSeed(seed+10);s.addForce(baro);s.addForce(mm.CMMotionRemover(1));c,it=context(s,'CUDA',seed);c.setPositions(x);c.applyConstraints(1e-6);start=time.monotonic()
    mm.LocalEnergyMinimizer.minimize(c,20.,2000);st=c.getState(getPositions=True);xm=st.getPositions(asNumpy=True).value_in_unit(u.nanometer);np.save(p/'minimized_positions_nm.npy',xm,allow_pickle=False)
    eg,fg=energy_forces(m['wet'],xm,'CUDA');ec,fc=energy_forces(m['wet'],xm,'CPU');comp={'energy_difference_per_atom':abs(eg-ec)/len(x),'force_rms':float(np.sqrt(np.mean((fg-fc)**2)))};comp['pass']=comp['energy_difference_per_atom']<.01 and comp['force_rms']<1;dump(p/'wet-platform-check.json',comp);assert comp['pass'],comp
    c.setVelocitiesToTemperature(100*u.kelvin,seed);c.applyVelocityConstraints(1e-6);dof=3*len(x)-s.getNumConstraints()-3;mass=sum(float(s.getParticleMass(i)/u.dalton) for i in range(len(x)))
    constraints=np.array([[i,j,float(r/u.nanometer)] for i,j,r in (s.getConstraintParameters(k) for k in range(s.getNumConstraints()))]);cs=m['centers'];initial_signs=signs(xm,cs);records=[];frames=[];steps=0
    for stage,duration,k,pressure in [('heat',2,1000,False),('NVT',8,500,False),('NPT',10,100,True),('NPT_free',30,0,True)]:
        c.setParameter('k',k)
        if pressure and baro.getFrequency()==0:baro.setFrequency(25);c.reinitialize(preserveState=True)
        for chunk in range(duration):
            temp=100+210*(chunk+1)/duration if stage=='heat' else 310;it.setTemperature(temp*u.kelvin);it.step(1000);steps+=1000
            st=c.getState(getPositions=True,getForces=True,getEnergy=True);xx=st.getPositions(asNumpy=True).value_in_unit(u.nanometer);forces=st.getForces(asNumpy=True).value_in_unit(u.kilojoule_per_mole/u.nanometer);pe=float(st.getPotentialEnergy()/u.kilojoule_per_mole);ke=float(st.getKineticEnergy()/u.kilojoule_per_mole);bv=st.getPeriodicBoxVectors(asNumpy=True).value_in_unit(u.nanometer);volume=float(np.linalg.det(bv));diff=xx[constraints[:,0].astype(int)]-xx[constraints[:,1].astype(int)];diff-=np.round(diff/np.diag(bv))*np.diag(bv);cerr=float(np.max(abs(np.linalg.norm(diff,axis=1)-constraints[:,2])))
            inv=int(np.sum(signs(xx,cs)*initial_signs<0));rec={'stage':stage,'time_ps':float(st.getTime()/u.picosecond),'step':steps,'temperature_K':2*ke/(dof*.00831446261815324),'density_g_ml':mass/(602.214076*volume),'potential_kJ_mol':pe,'constraint_error_nm':cerr,'stereocenter_inversions':inv,'restraint_k':k,'wall_seconds':time.monotonic()-start}
            assert np.isfinite(xx).all() and np.isfinite(forces).all() and math.isfinite(pe) and math.isfinite(ke);assert not inv and cerr<1e-4 and 20<rec['temperature_K']<650 and .5<rec['density_g_ml']<1.5,rec
            assert c.getStepCount()==steps;records.append(rec);frames.append(xx[:n].copy());dump(p/'progress.json',records)
    final=c.getState(getPositions=True,getVelocities=True,getParameters=True,getEnergy=True);(p/'final_state.xml').write_text(mm.XmlSerializer.serialize(final));(p/'final_system.xml').write_text(mm.XmlSerializer.serialize(s));np.save(p/'solute_frames_nm.npy',np.array(frames),allow_pickle=False);np.save(p/'final_positions_nm.npy',final.getPositions(asNumpy=True).value_in_unit(u.nanometer),allow_pickle=False)
    report={'model':case,'replica':replica,'seed':seed,'steps':steps,'time_ps':50,'unrestrained_tail_ps':30,'n_solute_atoms':n,'n_atoms':len(x),'all_checks_pass':True,'last_frame':records[-1],'wall_seconds':time.monotonic()-start,'physical_accuracy_or_convergence_established':False};dump(p/'result.json',report);del c,it;gc.collect();return report
def main():
    prepared={};summary={'prepared':[],'replicas':[],'all_complete':False};dump(OUT/'summary.json',summary)
    for case in CASES:
        prepared[case]=prepare(case);summary['prepared'].append(case);dump(OUT/'summary.json',summary)
    for case in CASES:prepared[case]=solvate(case,prepared[case])
    for case in CASES:
        for replica in range(3):summary['replicas'].append(run(case,prepared[case],replica));dump(OUT/'summary.json',summary)
    summary.update(all_complete=True,total_ps=600,total_steps=600000,mechanical_ranking_established=False,reaction_dynamics_run=False);dump(OUT/'summary.json',summary)
if __name__=='__main__':main()

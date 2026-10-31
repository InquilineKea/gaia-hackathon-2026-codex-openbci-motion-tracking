#!/usr/bin/env python3
"""Original bounded preparation/equilibration driver. Run only in reviewed isolation.

No force-field fitting, automatic parameter substitution, pulling, or production MD.
"""
import argparse, collections, gc, hashlib, io, json, math, os, random, sys, time
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
import openmm as mm
from openmm import unit
from openmm.app import Topology, ForceField, Modeller, PDBxFile, element

parser=argparse.ArgumentParser()
parser.add_argument('phase',choices=['build','equilibrate'])
parser.add_argument('--case',required=True,choices=['PYD','DPD'])
parser.add_argument('--replica',type=int,choices=[0,1,2],default=0)
args=parser.parse_args()
ROOT=Path('/project')
OUT=Path('/results')/(args.case+'_build' if args.phase=='build' else args.case+'_replica_'+str(args.replica))/'run'
OUT.mkdir(parents=True,exist_ok=False)
DRY=ROOT/'inputs'/args.case
SEED=20261031 + (100 if args.case=='DPD' else 0) + args.replica
def dump(path,obj):path.write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')
def msg(s):print(s,flush=True)
def nbforce(s):return next(f for f in s.getForces() if isinstance(f,mm.NonbondedForce))
def topology(data):
    top=Topology(); chains={}; residues=[]; atoms=[]
    for r in data['residues']:
        if r['chain'] not in chains:chains[r['chain']]=top.addChain(r['chain'])
        residues.append(top.addResidue(r['name'],chains[r['chain']],str(r['id'])))
    for a in data['atoms']:atoms.append(top.addAtom(a['name'],element.get_by_symbol(a['element']),residues[a['resindex']]))
    for i,j in data['bonds']:top.addBond(atoms[i],atoms[j])
    return top
def radius_ff(data):
    # Used ONLY by Modeller for solute exclusion radii and charge. The physical
    # solute system is copied from the accepted explicit mixed-force-field XML.
    root=ET.Element('ForceField'); types=ET.SubElement(root,'AtomTypes'); rs=ET.SubElement(root,'Residues')
    nb=ET.SubElement(root,'NonbondedForce',coulomb14scale='0.8333333333333334',lj14scale='0.5')
    rt=[]
    for ri,r in enumerate(data['residues']):rt.append(ET.SubElement(rs,'Residue',name='R'+str(ri)))
    for i,a in enumerate(data['atoms']):
        typ='P'+str(i)
        ET.SubElement(types,'Type',name=typ,**{'class':typ,'element':a['element'],'mass':str(a['mass'])})
        ET.SubElement(rt[a['resindex']],'Atom',name=a['name'],type=typ)
        ET.SubElement(nb,'Atom',type=typ,charge=str(a['q']),sigma=str(a['sigma']),epsilon=str(a['epsilon']))
    for i,j in data['bonds']:
        a,b=data['atoms'][i],data['atoms'][j]
        if a['resindex']==b['resindex']:ET.SubElement(rt[a['resindex']],'Bond',atomName1=a['name'],atomName2=b['name'])
        else:
            for x in (a,b):ET.SubElement(rt[x['resindex']],'ExternalBond',atomName=x['name'])
    return ET.tostring(root,encoding='unicode')
def solvent_templates():
    # Obtain a unit water and monovalent ions from the approved wheel data.
    top=Topology(); c=top.addChain(); r=top.addResidue('HOH',c)
    o=top.addAtom('O',element.oxygen,r);h1=top.addAtom('H1',element.hydrogen,r);h2=top.addAtom('H2',element.hydrogen,r)
    top.addBond(o,h1);top.addBond(o,h2)
    for n,e in [('NA',element.sodium),('CL',element.chlorine)]:top.addAtom(n,e,top.addResidue(n,c))
    s=ForceField('amber14/tip3p.xml').createSystem(top,rigidWater=True,removeCMMotion=False)
    n=nbforce(s); info={}
    for name,ids in [('HOH',[0,1,2]),('NA',[3]),('CL',[4])]:
        info[name]={'particles':[[float(s.getParticleMass(i)/unit.dalton),float(n.getParticleParameters(i)[0]/unit.elementary_charge),float(n.getParticleParameters(i)[1]/unit.nanometer),float(n.getParticleParameters(i)[2]/unit.kilojoule_per_mole)] for i in ids]}
    info['HOH']['constraints']=[[int(i),int(j),float(d/unit.nanometer)] for i,j,d in (s.getConstraintParameters(k) for k in range(s.getNumConstraints()))]
    for f in s.getForces():
        if isinstance(f,mm.HarmonicBondForce):assert f.getNumBonds()==0
        elif isinstance(f,mm.HarmonicAngleForce):assert f.getNumAngles()==0
        elif not isinstance(f,mm.NonbondedForce):raise ValueError('Unexpected water force '+type(f).__name__)
    return info
def build():
    start=time.monotonic();data=json.loads((DRY/'prepared.json').read_text());n=len(data['atoms']);assert n=={'PYD':1793,'DPD':1792}[args.case]
    x=np.load(DRY/'positions_nm.npy',allow_pickle=False);center=x.mean(0)
    _,rot=np.linalg.eigh((x-center).T@(x-center));
    if np.linalg.det(rot)<0:rot[:,0]*=-1
    xr=(x-center)@rot;box=np.ptp(xr,axis=0)+2.4;shift=1.2-xr.min(0);xr+=shift
    assert np.linalg.det(rot)>0 and box.min()>2.4
    top=topology(data);ff=ForceField('amber14/tip3p.xml',io.StringIO(radius_ff(data)))
    modeller=Modeller(top,xr*unit.nanometer);random.seed(SEED)
    msg({'stage':'adding_water','box_nm':box.tolist(),'volume_nm3':float(np.prod(box))})
    modeller.addSolvent(ff,model='tip3p',boxSize=mm.Vec3(*box)*unit.nanometer,ionicStrength=.15*unit.molar,
        positiveIon='Na+',negativeIon='Cl-',neutralize=True,residueTemplates={r:'R'+str(i) for i,r in enumerate(top.residues())})
    natoms=modeller.topology.getNumAtoms();assert natoms<150000, 'Atom limit exceeded'
    xp=np.asarray(modeller.positions.value_in_unit(unit.nanometer));assert np.max(abs(xp[:n]-xr))<1e-12
    msg({'stage':'water_added','atoms':natoms})
    s=mm.XmlSerializer.deserialize((DRY/'physical_system.xml').read_text());nb=nbforce(s);water=solvent_templates()
    # Preserve every solute force/exception. Constrain only H-bond lengths at
    # their source equilibrium values; retain their harmonic terms (zero on manifold).
    for i,j,r,k in data['terms']['bonds']:
        if 'H' in (data['atoms'][i]['element'],data['atoms'][j]['element']):s.addConstraint(i,j,r)
    counts=collections.Counter(); waters=[]; species=[]
    for r in modeller.topology.residues():
        ids=[a.index for a in r.atoms()]
        if ids[0]<n:continue
        name=r.name;counts[name]+=1;assert name in water
        assert len(ids)==len(water[name]['particles'])
        for i,p in zip(ids,water[name]['particles']):assert s.addParticle(p[0])==i;nb.addParticle(*p[1:])
        if name=='HOH':
            waters.append(ids)
            for i,j,d in water[name]['constraints']:s.addConstraint(ids[i],ids[j],d)
            for i,j in ((0,1),(0,2),(1,2)):nb.addException(ids[i],ids[j],0,1,0)
        else:species.append([ids[0],name])
    nb.setNonbondedMethod(mm.NonbondedForce.PME);nb.setCutoffDistance(1.0);nb.setEwaldErrorTolerance(1e-5)
    nb.setUseDispersionCorrection(True);nb.setUseSwitchingFunction(False)
    s.setDefaultPeriodicBoxVectors(*[mm.Vec3(*(np.eye(3)[i]*box))*unit.nanometer for i in range(3)])
    assert s.getNumParticles()==natoms
    charge=sum(float(nb.getParticleParameters(i)[0]/unit.elementary_charge) for i in range(natoms))
    neutralizing=round(-sum(a['q'] for a in data['atoms']))
    assert abs(charge)<1e-4 and counts['NA']-counts['CL']==neutralizing
    # Structural audit: solvent assembly cannot alter any solute atom parameter,
    # bond/angle/torsion, or original 1-4 exception.
    old=mm.XmlSerializer.deserialize((DRY/'physical_system.xml').read_text());onb=nbforce(old)
    for i in range(n):assert nb.getParticleParameters(i)==onb.getParticleParameters(i)
    for i in range(onb.getNumExceptions()):assert nb.getExceptionParameters(i)==onb.getExceptionParameters(i)
    for f,g in zip(list(old.getForces())[:4],list(s.getForces())[:4]):assert mm.XmlSerializer.serialize(f)==mm.XmlSerializer.serialize(g)
    np.save(OUT/'positions_nm.npy',xp,allow_pickle=False);np.save(OUT/'water_atom_indices.npy',np.array(waters,dtype=np.int32),allow_pickle=False)
    (OUT/'physical_system.xml').write_text(mm.XmlSerializer.serialize(s))
    with (OUT/'solvated.cif').open('w') as f:PDBxFile.writeFile(modeller.topology,xp*unit.nanometer,f,keepIds=False)
    report={'status':'prepared','n_solute_atoms':n,'n_atoms':natoms,'counts':dict(counts),'charge_e':charge,'box_nm':box.tolist(),'volume_nm3':float(np.prod(box)),
        'salt_molarity_from_pairs_and_box':counts['CL']/(.602214076*float(np.prod(box))),'neutralizing_Na':neutralizing,
        'water_and_ion_parameters':water,'rotation':rot.tolist(),'rotation_center_nm':center.tolist(),'translation_after_rotation_nm':shift.tolist(),
        'seed':SEED,'padding_nm':1.2,'solute_parameters_preserved':True,'constraints':s.getNumConstraints(),'physical_model':'TIP3P + Joung-Cheatham Na/Cl; explicit ColBuilder Amber99SB-star-ILDNP native-crosslink solute',
        'no_production_simulation':True,'build_wall_seconds':time.monotonic()-start}
    dump(OUT/'solvation.json',report);msg(report)

def context(s,platform='CUDA',precision='mixed'):
    i=mm.LangevinMiddleIntegrator(310*unit.kelvin,1/unit.picosecond,.001*unit.picoseconds);i.setConstraintTolerance(1e-6);i.setRandomNumberSeed(SEED)
    p={'Precision':precision,'DeterministicForces':'true'} if platform=='CUDA' else {'Threads':'2'}
    return mm.Context(s,i,mm.Platform.getPlatformByName(platform),p),i

def equilibrate():
    seed=Path('/results')/(args.case+'_build')/'run';report=json.loads((seed/'solvation.json').read_text());data=json.loads((DRY/'prepared.json').read_text())
    accepted=json.loads((DRY/'validation.json').read_text());assert accepted['all_preparation_checks_pass']
    validation=None
    s=mm.XmlSerializer.deserialize((seed/'physical_system.xml').read_text());x=np.load(seed/'positions_nm.npy',allow_pickle=False);n=len(data['atoms'])
    heavy=[i for i,a in enumerate(data['atoms']) if a['element']!='H']
    rest=mm.CustomExternalForce('0.5*k*periodicdistance(x,y,z,x0,y0,z0)^2');rest.addGlobalParameter('k',1000.)
    for nm in ('x0','y0','z0'):rest.addPerParticleParameter(nm)
    for i in heavy:rest.addParticle(i,x[i])
    rest.setForceGroup(5);s.addForce(rest)
    baro=mm.MonteCarloBarostat(1*unit.bar,310*unit.kelvin,0);baro.setRandomNumberSeed(SEED+1);s.addForce(baro)
    # COM removal has 3 degrees of freedom; no hydrogen mass repartitioning.
    s.addForce(mm.CMMotionRemover(1));(OUT/'equilibration_system.xml').write_text(mm.XmlSerializer.serialize(s))
    ctx,integ=context(s);ctx.setPositions(x);ctx.applyConstraints(1e-6)
    start=time.monotonic();msg({'stage':'solvent_minimization','n_atoms':len(x)})
    mm.LocalEnergyMinimizer.minimize(ctx,20.,2000)
    st=ctx.getState(getPositions=True,getEnergy=True,getForces=True);xm=st.getPositions(asNumpy=True).value_in_unit(unit.nanometer)
    assert np.isfinite(st.getPotentialEnergy().value_in_unit(unit.kilojoule_per_mole))
    np.save(OUT/'minimized_positions_nm.npy',xm,allow_pickle=False)
    # Independent platform check of periodic water/ions and the physical mixed
    # solute at the same constrained/minimized coordinates, without restraints.
    phys=mm.XmlSerializer.deserialize((seed/'physical_system.xml').read_text())
    pc,pi=context(phys,'CUDA','double');pc.setPositions(xm);ps=pc.getState(getEnergy=True,getForces=True)
    eg=float(ps.getPotentialEnergy()/unit.kilojoule_per_mole);fg=ps.getForces(asNumpy=True).value_in_unit(unit.kilojoule_per_mole/unit.nanometer)
    pme=nbforce(phys).getPMEParametersInContext(pc);del pc,pi;gc.collect()
    cc,ci=context(phys,'CPU');cc.setPositions(xm);cs=cc.getState(getEnergy=True,getForces=True)
    ec=float(cs.getPotentialEnergy()/unit.kilojoule_per_mole);fc=cs.getForces(asNumpy=True).value_in_unit(unit.kilojoule_per_mole/unit.nanometer)
    cross={'energy_difference_per_atom':abs(eg-ec)/len(x),'force_rms_difference':float(np.sqrt(np.mean((fg-fc)**2))),
        'cuda_energy':eg,'cpu_energy':ec,'PME_alpha_per_nm':float(pme[0]),'PME_grid':list(pme[1:])}
    cross['pass']=cross['energy_difference_per_atom']<.01 and cross['force_rms_difference']<1.
    dump(OUT/'solvated-platform-check.json',cross);assert cross['pass'],cross
    del cc,ci,phys,fg,fc;gc.collect()
    ctx.setVelocitiesToTemperature(100*unit.kelvin,SEED);ctx.applyVelocityConstraints(1e-6)
    dof=3*s.getNumParticles()-s.getNumConstraints()-3;mass=sum(float(s.getParticleMass(i)/unit.dalton) for i in range(s.getNumParticles()))
    constraints=np.array([[int(a),int(b),float(d/unit.nanometer)] for a,b,d in (s.getConstraintParameters(k) for k in range(s.getNumConstraints()))])
    adj=[set() for _ in range(n)]
    for a,b in data['bonds']:adj[a].add(b);adj[b].add(a)
    ch=[(i,sorted(j for j in adj[i] if data['atoms'][j]['element']!='H')[:3]) for i,a in enumerate(data['atoms']) if len(adj[i])==4 and sum(data['atoms'][j]['element']!='H' for j in adj[i])>=3 and a['type'] in ('CT','Cg','Cy')]
    signs=np.array([np.linalg.det(xm[js]-xm[i]) for i,js in ch]);records=[];frames=[];steps=0
    for stage,chunks,target,k,pressure in [('heat',2,310,1000,False),('NVT',8,310,500,False),('NPT',10,310,100,True)]:
        ctx.setParameter('k',k)
        if pressure:
            baro.setFrequency(25);ctx.reinitialize(preserveState=True)
        for chunk in range(chunks):
            temp=100+(target-100)*(chunk+1)/chunks if stage=='heat' else target;integ.setTemperature(temp*unit.kelvin)
            integ.step(1000);steps+=1000
            st=ctx.getState(getEnergy=True,getPositions=True,getForces=True);xx=st.getPositions(asNumpy=True).value_in_unit(unit.nanometer)
            pe=float(st.getPotentialEnergy()/unit.kilojoule_per_mole);ke=float(st.getKineticEnergy()/unit.kilojoule_per_mole)
            forces=st.getForces(asNumpy=True).value_in_unit(unit.kilojoule_per_mole/unit.nanometer)
            box=np.array(st.getPeriodicBoxVectors(asNumpy=True).value_in_unit(unit.nanometer));vol=float(np.linalg.det(box));diff=xx[constraints[:,0].astype(int)]-xx[constraints[:,1].astype(int)]
            diff-=np.round(diff/np.diag(box))*np.diag(box);cerr=float(np.max(abs(np.linalg.norm(diff,axis=1)-constraints[:,2])))
            inversion=sum(np.linalg.det(xx[js]-xx[i])*sg<0 for (i,js),sg in zip(ch,signs))
            assert ctx.getStepCount()==steps and abs(float(st.getTime()/unit.picosecond)-steps*.001)<1e-7
            rec={'stage':stage,'step':steps,'time_ps':float(st.getTime()/unit.picosecond),'target_K':temp,'temperature_K':2*ke/(dof*.00831446261815324),
                 'potential_kJ_mol':pe,'kinetic_kJ_mol':ke,'volume_nm3':vol,'density_g_ml':mass/(602.214076*vol),
                 'max_constraint_error_nm':cerr,'solute_chirality_inversions':int(inversion),'max_abs_force':float(np.max(abs(forces))),
                 'box_diagonal_nm':np.diag(box).tolist(),'restraint_k':k,'elapsed_seconds':time.monotonic()-start}
            assert np.isfinite(xx).all() and np.isfinite(forces).all() and math.isfinite(pe) and math.isfinite(ke)
            assert cerr<1e-4 and not inversion and 20<rec['temperature_K']<650 and .5<rec['density_g_ml']<1.5,rec
            records.append(rec);frames.append(xx[:n].copy());dump(OUT/'progress.json',records);msg(rec)
            (OUT/'latest.chk').write_bytes(ctx.createCheckpoint())
    final=ctx.getState(getPositions=True,getVelocities=True,getEnergy=True,getParameters=True)
    np.save(OUT/'final_positions_nm.npy',final.getPositions(asNumpy=True).value_in_unit(unit.nanometer),allow_pickle=False)
    np.save(OUT/'solute_frames_nm.npy',np.array(frames),allow_pickle=False)
    (OUT/'final_state.xml').write_text(mm.XmlSerializer.serialize(final));(OUT/'final_system.xml').write_text(mm.XmlSerializer.serialize(s))
    result={'status':'bounded_equilibration_test_passed','steps':steps,'time_ps':20,'timestep_fs':1,'stages_ps':{'heat':2,'NVT':8,'NPT':10},
        'n_atoms':s.getNumParticles(),'constraint_tolerance':1e-6,'temperature_target_K':310,'pressure_bar':1,'seed':SEED,'all_stability_checks_pass':True,
        'wall_seconds':time.monotonic()-start,'last_frame':records[-1],'full_equilibration_established':False,'binding_pose_validated':False,
        'native_gromacs_crossvalidation_passed':False,'dry_source_reader_and_derivative_checks':accepted,'accepted_dry_parameter_and_derivative_checks_passed':True,'production_or_axial_loading_run':False,
        'limitations':['20 ps with heavy-solute restraints is a runtime/stability test only','native PYD/DPD controls do not represent AGE or oxidative candidate chemistry','single collagen crosslink coupon does not represent bulk tendon mechanics','three short restrained replicas cannot establish equilibrium or rank mechanical stiffness']}
    dump(OUT/'equilibration-result.json',result);msg(result)

if __name__=='__main__':
    if args.phase=='build':build()
    elif args.phase=='equilibrate':equilibrate()
    else:raise ValueError('Unknown phase')

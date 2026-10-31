"""Independent local numeric readback using Python's standard library only."""
import ast,collections,csv,json,math,pathlib,statistics,struct,xml.etree.ElementTree as ET
BASE=pathlib.Path('outputs/collagen-glucosepane-dityrosine-20261031');RAW=BASE/'retrieved/attempt-002/run'
def read(p):return json.loads(p.read_text())
def npy(p):
    raw=p.read_bytes();assert raw[:6]==b'\x93NUMPY'
    if raw[6]==1:n=struct.unpack('<H',raw[8:10])[0];offset=10
    else:n=struct.unpack('<I',raw[8:12])[0];offset=12
    h=ast.literal_eval(raw[offset:offset+n].decode());assert h['descr']=='<f8' and not h['fortran_order']
    vals=struct.unpack('<'+str(math.prod(h['shape']))+'d',raw[offset+n:]);assert all(math.isfinite(x) for x in vals)
    if len(h['shape'])==2:return [vals[i:i+3] for i in range(0,len(vals),3)]
    assert len(h['shape'])==3 and h['shape'][2]==3;n=h['shape'][1]
    return [[vals[(f*n+i)*3:(f*n+i+1)*3] for i in range(n)] for f in range(h['shape'][0])]
def dist(a,b,box=None):
    v=[x-y for x,y in zip(a,b)]
    if box:v=[x-round(x/l)*l for x,l in zip(v,box)]
    return math.sqrt(sum(x*x for x in v))
def volume(x,i,js):
    a,b,c=[[x[j][k]-x[i][k] for k in range(3)] for j in js]
    return a[0]*(b[1]*c[2]-b[2]*c[1])-a[1]*(b[0]*c[2]-b[2]*c[0])+a[2]*(b[0]*c[1]-b[1]*c[0])
def main():
    summary=read(RAW/'summary.json');rows=[]
    for rr in summary['replicas']:
        case=rr['model'];replica=rr['replica'];d=read(BASE/'prepared'/case/(case+'.json'));p=RAW/case/('replica_'+str(replica))
        x=npy(p/'final_positions_nm.npy');xm=npy(p/'minimized_positions_nm.npy');frames=npy(p/'solute_frames_nm.npy');progress=read(p/'progress.json');n=len(d['atoms']);assert len(frames)==50 and len(progress)==50
        state=ET.parse(p/'final_state.xml').getroot();assert int(state.attrib['stepCount'])==50000 and abs(float(state.attrib['time'])-50)<1e-6
        params=state.find('Parameters');assert float(params.attrib['k'])==0
        bv=state.find('PeriodicBoxVectors');box=[float(bv.find(a).attrib[c]) for a,c in [('A','x'),('B','y'),('C','z')]]
        adj=[set() for _ in range(n)]
        for i,j in d['bonds']:adj[i].add(j);adj[j].add(i)
        centers=[(i,sorted(j for j in ns if d['atoms'][j]['element']!='H')[:3]) for i,ns in enumerate(adj) if len(ns)==4 and d['atoms'][i]['element']=='C' and sum(d['atoms'][j]['element']!='H' for j in ns)>=3]
        inversions=sum(volume(x,i,js)*volume(xm,i,js)<0 for i,js in centers)
        force_root=ET.parse(RAW/case/'dry_system.xml').getroot();pairs={tuple(sorted(v)) for v in d['bonds']};bond_parameters={};inventory=[]
        for f in force_root.find('Forces'):
            record={'type':f.attrib['type'],'child_counts':{c.tag:len(c) for c in f}}
            inventory.append(record)
            if f.attrib['type']=='HarmonicBondForce':
                for b in f.find('Bonds'):
                    pair=tuple(sorted((int(b.attrib['p1']),int(b.attrib['p2']))))
                    if pair in pairs:bond_parameters[pair]=float(b.attrib['d'])
        assert len(bond_parameters)==len(pairs)
        maxdev=max(abs(dist(x[i],x[j])-length)*10 for (i,j),length in bond_parameters.items())
        heavy=[i for i,a in enumerate(d['atoms']) if a['element']!='H'];rms=10*math.sqrt(sum(dist(x[i],xm[i])**2 for i in heavy)/len(heavy))
        if case.startswith('GLU'):
            meta=read(BASE/'prepared'/case/'MODEL_PROVENANCE.json');pair=meta['published_pair'];targets=[pair['lgx_index'],pair['ags_index']]
            rids=[next(i for i,r in enumerate(d['residues']) if r.get('source',{}).get('published_source_index')==site) for site in targets]
        else:rids=[next(i for i,r in enumerate(d['residues']) if r['id']==j and r['name']=='TYR') for j in (4,6)]
        def find(ri,name):return next(i for i,a in enumerate(d['atoms']) if a['resindex']==ri and a['name']==name)
        ca=[find(ri,'CA') for ri in rids];tail=[];link=[]
        if case=='GLU_LINKED':link=[find(rids[0],'CE'),find(rids[1],'NZ')]
        elif case=='DITY_LINKED':link=[find(ri,'CE2') for ri in rids]
        linkdist=[]
        for f,rec in zip(frames,progress):
            if rec['stage']!='NPT_free':continue
            scale=(progress[-1]['density_g_ml']/rec['density_g_ml'])**(1/3);current_box=[l*scale for l in box]
            tail.append(10*dist(f[ca[0]],f[ca[1]],current_box))
            if link:linkdist.append(10*dist(f[link[0]],f[link[1]]))
        assert len(tail)==30 and not inversions and all(r['stereocenter_inversions']==0 for r in progress)
        record={'model':case,'replica':replica,'seed':rr['seed'],'time_ps':rr['time_ps'],'free_tail_ps':30,'n_atoms':rr['n_atoms'],'n_solute_atoms':n,
            'final_temperature_K':progress[-1]['temperature_K'],'final_density_g_ml':progress[-1]['density_g_ml'],'max_constraint_error_nm':max(r['constraint_error_nm'] for r in progress),
            'monitored_centers':len(centers),'final_stereocenter_inversions':inversions,'final_max_chemical_bond_deviation_A':maxdev,'final_heavy_solute_displacement_A':rms,
            'free_tail_CA_marker_mean_A':statistics.mean(tail),'free_tail_CA_marker_SD_A':statistics.stdev(tail),'free_tail_link_bond_mean_A':statistics.mean(linkdist) if linkdist else None,
            'force_inventory':inventory,'final_state_step':int(state.attrib['stepCount']),'final_state_time_ps':float(state.attrib['time']),'final_solute_restraint_k':float(params.attrib['k']),
            'wet_platform_check':read(p/'wet-platform-check.json'),'all_runtime_checks_pass':rr['all_checks_pass'],'integration_precision':rr.get('integration_precision','double'),'origin_attempt':rr.get('origin_attempt','attempt-001')}
        (p/'local-independent-analysis.json').write_text(json.dumps(record,indent=2)+'\n');rows.append(record)
    result={'all_complete':summary['all_complete'],'completed_replicas':len(rows),'total_ps':sum(r['time_ps'] for r in rows),'total_steps':sum(r['final_state_step'] for r in rows),'rows':rows,
        'cross_chemistry_mechanical_ranking_established':False,'reaction_dynamics_run':False,'physical_parameter_accuracy_established':False}
    (BASE/'RESULT_SUMMARY.json').write_text(json.dumps(result,indent=2)+'\n')
    keys=[k for k in rows[0] if k not in ('force_inventory','wet_platform_check')]
    with (BASE/'replica_summary.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows({k:r[k] for k in keys} for r in rows)
    print(json.dumps({'all_complete':result['all_complete'],'replicas':len(rows),'total_ps':result['total_ps'],'rows':[{k:r[k] for k in ['model','replica','final_temperature_K','final_density_g_ml','final_max_chemical_bond_deviation_A','free_tail_CA_marker_mean_A','free_tail_link_bond_mean_A']} for r in rows]},indent=2))
if __name__=='__main__':main()

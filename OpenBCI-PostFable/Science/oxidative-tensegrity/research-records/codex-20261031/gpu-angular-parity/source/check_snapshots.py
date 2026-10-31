import argparse,json,pathlib,math
from backend import cpu,GPU

def scaled(a,b):return max((abs(x-y)/(1+abs(x)+abs(y)) for x,y in zip(a,b)),default=0.)
def assemble(rows,nodes,nn):
    force=[0.]*(3*nn);virial=[0.]*9;energy=0.
    for row,triple in zip(rows,nodes):
        if row[19]!=0 or not all(math.isfinite(v) for v in row):raise ValueError('invalid angular term')
        energy+=row[0]
        for role,node in enumerate(triple):
            for d in range(3):force[3*node+d]+=row[1+3*role+d]
        for j in range(9):virial[j]+=row[10+j]
    return energy,force,[virial[j] for j in (0,4,8,1,2,5)]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--fixtures',required=True);ap.add_argument('--cpu-library',required=True);ap.add_argument('--output',required=True);ap.add_argument('--ptx');args=ap.parse_args()
    frames=json.loads(pathlib.Path(args.fixtures).read_text());gpu=GPU(pathlib.Path(args.ptx).read_bytes()) if args.ptx else None;records=[]
    try:
        for f in frames:
            rows=cpu(f['terms'],args.cpu_library);E,forces,V=assemble(rows,f['nodes'],f['nn'])
            err=dict(energy=scaled([E],[f['expected_energy']]),forces=scaled(forces,f['expected_forces']),virial=scaled(V,f['expected_virial']))
            if gpu:
                r=gpu.evaluate(f['terms'],f['nodes'],f['nn']);e,ff,vv=assemble(r['terms'],f['nodes'],f['nn'])
                err.update(gpu_terms=max(scaled(x,y) for x,y in zip(rows,r['terms'])),gpu_force_gather=scaled(forces,r['forces']),gpu_total=scaled([E]+[sum(row[10+j] for row in rows) for j in range(9)]+[0.],r['totals']))
            records.append(dict(name=f['name'],terms=len(rows),passed=max(err.values())<2e-11,errors=err))
    finally:
        if gpu:gpu.close()
    report=dict(passed=all(r['passed'] for r in records),frames=len(frames),terms=sum(r['terms'] for r in records),gpu_executed=gpu is not None,records=records)
    pathlib.Path(args.output).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='records'}))
    if not report['passed']:raise SystemExit(1)
if __name__=='__main__':main()

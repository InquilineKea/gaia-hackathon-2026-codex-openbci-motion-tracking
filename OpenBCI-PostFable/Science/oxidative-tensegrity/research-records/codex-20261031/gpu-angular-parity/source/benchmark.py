"""Bounded informational timings. No physical trajectories or auto-expansion."""
import argparse,json,time,pathlib,ctypes as C
from backend import GPU,cpu,csr,I,D
from validate import cases,discrepancy
ap=argparse.ArgumentParser();ap.add_argument('--cpu-library',required=True);ap.add_argument('--ptx',required=True);ap.add_argument('--output',required=True);args=ap.parse_args()
pool,_=cases();gpu=GPU(pathlib.Path(args.ptx).read_bytes());records=[]
try:
 for n in (1024,16384,65536,262144):
    terms=[pool[i%len(pool)] for i in range(n)];nn=4096
    nodes=[(i%nn,0 if i%10==0 else (i+1)%nn,(i+2)%nn) for i in range(n)]
    start=time.perf_counter();ref=cpu(terms,args.cpu_library);cpu_seconds=time.perf_counter()-start
    start=time.perf_counter();got=gpu.evaluate(terms,nodes,nn);adapter_seconds=time.perf_counter()-start
    err=max(discrepancy(a,b) for a,b in zip(ref,got['terms']))
    if err>=2e-11 or got['totals'][10]!=0:raise RuntimeError('benchmark parity failed')
    off,entry=csr(nodes,nn);tiles=(n+255)//256;workspace=len(gpu.buffers)
    try:
      inp=gpu.put([v for p in terms for v in p]);out=gpu.alloc(20*n*8);offset=gpu.put(off,I);ent=gpu.put(entry,I);force=gpu.alloc(3*nn*8);part=gpu.alloc(11*tiles*8);total=gpu.alloc(88)
      def launch():
        gpu.launch_terms(n,inp,out);gpu.launch('oxt_gather',nn,[I(nn),offset,ent,out,force]);gpu.launch('oxt_partial',tiles,[I(n),out,part]);gpu.launch('oxt_total',11,[I(tiles),part,total],32)
      launch();gpu.ck(gpu.d.cuCtxSynchronize());t=time.perf_counter()
      for _ in range(10):launch()
      gpu.ck(gpu.d.cuCtxSynchronize());resident_seconds=(time.perf_counter()-t)/10
      records.append(dict(terms=n,nodes=nn,term_parity_max_scaled=err,cpu_host_adapter_seconds=cpu_seconds,gpu_host_adapter_seconds=adapter_seconds,gpu_resident_kernel_chain_seconds=resident_seconds,resident_repeats=10))
    finally:
      for p in reversed(gpu.buffers[workspace:]):gpu.ck(gpu.d.cuMemFree_v2(p))
      del gpu.buffers[workspace:]
finally:gpu.close()
pathlib.Path(args.output).write_text(json.dumps(dict(passed=True,informational=True,records=records),indent=2)+'\n')

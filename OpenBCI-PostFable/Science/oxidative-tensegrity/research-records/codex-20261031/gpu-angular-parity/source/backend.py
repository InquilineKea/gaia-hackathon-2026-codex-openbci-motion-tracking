"""Original stdlib-only CPU/CUDA operator bindings. No package installation or network.
GPU terms, gather and reductions stay on device; evaluate() is a host parity adapter.
Not a LAMMPS Kokkos plugin or a full network integrator.
"""
import ctypes as C
import pathlib
import math
import time
D=C.c_double; I=C.c_int; U=C.c_uint; P=C.c_void_p; Z=C.c_size_t; Q=C.c_uint64
ROOT=pathlib.Path(__file__).resolve().parent

def cpu(terms,library):
    if not terms:return []
    a=(D*(12*len(terms)))(*(v for t in terms for v in t));b=(D*(20*len(terms)))()
    lib=C.CDLL(str(library));lib.oxt_cpu.argtypes=[I,C.POINTER(D),C.POINTER(D)]
    lib.oxt_cpu(len(terms),a,b)
    return [list(b[20*i:20*i+20]) for i in range(len(terms))]

def reference(p):
    """Independent scalar CPU reference, same equations as source models."""
    a,b,k,r,sa,sb,mode,active=p[:3],p[3:6],*p[6:]
    if not active:return [0.]*20
    u=[sa*x for x in a];v=[sb*x for x in b]
    aa=sum(x*x for x in u);bb=sum(x*x for x in v);dot=sum(x*y for x,y in zip(u,v))
    if mode in (0,1):
        th=math.atan2(u[0]*v[1]-u[1]*v[0],dot);d=th-r
        if mode==1:d=math.atan2(math.sin(d),math.cos(d))
        gu=[k*d*u[1]/aa,-k*d*u[0]/aa,0.];gv=[-k*d*v[1]/bb,k*d*v[0]/bb,0.]
    elif mode==2:
        den=max(math.sqrt(aa*bb),1e-9);c=dot/den;d=c-r
        gu=[k*d*(v[j]/den-(c*u[j]/aa if den>1e-9 else 0.)) for j in range(3)]
        gv=[k*d*(u[j]/den-(c*v[j]/bb if den>1e-9 else 0.)) for j in range(3)]
    else:
        den=math.sqrt(aa*bb);c=max(-1.,min(1.,dot/den));cr=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
        sn=math.sqrt(sum(x*x for x in cr));th=math.atan2(sn,dot);d=th-r
        if sn==0. and d==0.:return [0.]*20
        gu=[k*d*(dot*u[j]/aa-v[j])/sn for j in range(3)]
        gv=[k*d*(dot*v[j]/bb-u[j])/sn for j in range(3)]
    ga=[sa*x for x in gu];gb=[sb*x for x in gv]
    return [.5*k*d*d]+[-x for x in ga]+[ga[j]+gb[j] for j in range(3)]+[-x for x in gb]+[-a[i]*ga[j]-b[i]*gb[j] for i in range(3) for j in range(3)]+[0.]

def csr(nodes,nn):
    rows=[[] for _ in range(nn)]
    for t,triple in enumerate(nodes):
        if len(triple)!=3:raise ValueError('three node IDs required')
        for role,node in enumerate(triple):
            if not 0<=node<nn:raise ValueError('node ID out of range')
            rows[node].append(3*t+role)
    offsets=[0];entries=[]
    for row in rows:entries.extend(row);offsets.append(len(entries))
    return offsets,entries

def compile_ptx(nvrtc_path,arch='compute_80'):
    # NVRTC can compile without a GPU. Only local, reviewed source is accepted.
    nv=C.CDLL(str(nvrtc_path));prog=P()
    def ck(code):
        if code:raise RuntimeError('NVRTC status '+str(code))
    source=(ROOT/'angular.cu').read_text().replace('#include "angular.h"',(ROOT/'angular.h').read_text()).encode()
    nv.nvrtcCreateProgram.argtypes=[C.POINTER(P),C.c_char_p,C.c_char_p,I,P,P]
    ck(nv.nvrtcCreateProgram(C.byref(prog),source,b'oxt.cu',0,None,None))
    opts=[b'--std=c++17',('--gpu-architecture='+arch).encode(),b'--fmad=false']
    opt=(C.c_char_p*len(opts))(*opts)
    try:
        nv.nvrtcCompileProgram.argtypes=[P,I,C.POINTER(C.c_char_p)]
        status=nv.nvrtcCompileProgram(prog,len(opts),opt)
        size=Z();nv.nvrtcGetProgramLogSize.argtypes=[P,C.POINTER(Z)];nv.nvrtcGetProgramLogSize(prog,C.byref(size))
        log=C.create_string_buffer(max(1,size.value));nv.nvrtcGetProgramLog.argtypes=[P,P];nv.nvrtcGetProgramLog(prog,log)
        if status:raise RuntimeError('NVRTC '+str(status)+': '+log.value.decode())
        nv.nvrtcGetPTXSize.argtypes=[P,C.POINTER(Z)];ck(nv.nvrtcGetPTXSize(prog,C.byref(size)))
        ptx=C.create_string_buffer(size.value);nv.nvrtcGetPTX.argtypes=[P,P];ck(nv.nvrtcGetPTX(prog,ptx))
        return ptx.raw,log.value.decode()
    finally:
        nv.nvrtcDestroyProgram.argtypes=[C.POINTER(P)];nv.nvrtcDestroyProgram(C.byref(prog))

class GPU:
    """Single device/context. Caller owns explicit image selection and alive masks.
    Device buffers remain allocated across launch() calls. No source downloads.
    """
    def __init__(self,ptx):
        self.d=C.CDLL('libcuda.so.1');self.buffers=[];self.closed=False
        signatures={'cuInit':[U],'cuDeviceGet':[C.POINTER(I),I], 'cuCtxCreate_v2':[C.POINTER(P),U,I], 'cuCtxDestroy_v2':[P], 'cuModuleLoadData':[C.POINTER(P),P], 'cuModuleUnload':[P], 'cuModuleGetFunction':[C.POINTER(P),P,C.c_char_p], 'cuMemAlloc_v2':[C.POINTER(Q),Z], 'cuMemFree_v2':[Q], 'cuMemcpyHtoD_v2':[Q,P,Z], 'cuMemcpyDtoH_v2':[P,Q,Z], 'cuCtxSynchronize':[], 'cuLaunchKernel':[P,U,U,U,U,U,U,U,P,C.POINTER(P),P]}
        for name,args in signatures.items():getattr(self.d,name).argtypes=args
        self.ck(self.d.cuInit(0));dev=I();self.ck(self.d.cuDeviceGet(C.byref(dev),0));self.ctx=P();self.ck(self.d.cuCtxCreate_v2(C.byref(self.ctx),0,dev))
        self.module=P();blob=C.create_string_buffer(ptx);self.ck(self.d.cuModuleLoadData(C.byref(self.module),blob));self.fun={}
        for name in ('oxt_terms','oxt_gather','oxt_partial','oxt_total','oxt_build','oxt_dEdF'):
            f=P();self.ck(self.d.cuModuleGetFunction(C.byref(f),self.module,name.encode()));self.fun[name]=f
    def ck(self,status):
        if status:raise RuntimeError('CUDA driver status '+str(status))
    def alloc(self,n):
        p=Q();self.ck(self.d.cuMemAlloc_v2(C.byref(p),max(8,n)));self.buffers.append(p);return p
    def put(self,values,kind=D):
        a=(kind*len(values))(*values);p=self.alloc(C.sizeof(a));self.ck(self.d.cuMemcpyHtoD_v2(p,a,C.sizeof(a)));return p
    def get(self,p,n,kind=D):
        a=(kind*n)();self.ck(self.d.cuMemcpyDtoH_v2(a,p,C.sizeof(a)));return list(a)
    def launch(self,name,count,args,threads=128):
        if count==0:return
        params=(P*len(args))(*(C.cast(C.byref(a),P) for a in args))
        self.ck(self.d.cuLaunchKernel(self.fun[name],(count+threads-1)//threads,1,1,threads,1,1,0,None,params,None))
    def launch_terms(self,n,inputs,terms):self.launch('oxt_terms',n,[I(n),inputs,terms])
    def evaluate(self,terms,nodes,nn):
        if len(terms)!=len(nodes):raise ValueError('topology size mismatch')
        off,entries=csr(nodes,nn);n=len(terms);tiles=(n+255)//256
        # Release this call's workspace even on failure; long-lived integrations use alloc/launch.
        start=len(self.buffers)
        try:
            inp=self.put([x for t in terms for x in t]);out=self.alloc(20*n*8)
            offsets=self.put(off,I);ent=self.put(entries,I);force=self.alloc(3*nn*8);part=self.alloc(11*max(1,tiles)*8);total=self.alloc(11*8)
            self.launch_terms(n,inp,out);self.launch('oxt_gather',nn,[I(nn),offsets,ent,out,force]);self.launch('oxt_partial',tiles,[I(n),out,part]);self.launch('oxt_total',11,[I(tiles),part,total],32)
            self.ck(self.d.cuCtxSynchronize());raw=self.get(out,20*n)
            return dict(terms=[raw[20*i:20*i+20] for i in range(n)],forces=self.get(force,3*nn),totals=self.get(total,11))
        finally:
            for p in reversed(self.buffers[start:]):self.ck(self.d.cuMemFree_v2(p))
            del self.buffers[start:]
    def geometry(self,positions,nodes,images,F,params):
        n=len(nodes)
        if len(images)!=n or len(params)!=n:raise ValueError('geometry size mismatch')
        csr(nodes,len(positions))
        if any(len(x)!=3 for x in positions) or any(len(x)!=6 for x in images+params) or len(F)!=9:raise ValueError('geometry shape mismatch')
        start=len(self.buffers)
        try:
            x=self.put([v for row in positions for v in row]);ids=self.put([v for row in nodes for v in row],I)
            img=self.put([v for row in images for v in row]);f=self.put(F);spec=self.put([v for row in params for v in row]);inp=self.alloc(12*n*8);terms=self.alloc(20*n*8);deriv=self.alloc(9*n*8)
            self.launch('oxt_build',n,[I(n),x,ids,img,f,spec,inp]);self.launch_terms(n,inp,terms)
            self.launch('oxt_dEdF',n,[I(n),terms,img,deriv]);self.ck(self.d.cuCtxSynchronize())
            return dict(inputs=self.get(inp,12*n),terms=self.get(terms,20*n),dEdF=self.get(deriv,9*n))
        finally:
            for p in reversed(self.buffers[start:]):self.ck(self.d.cuMemFree_v2(p))
            del self.buffers[start:]
    def close(self):
        if self.closed:return
        for p in reversed(self.buffers):self.ck(self.d.cuMemFree_v2(p))
        self.buffers=[];self.ck(self.d.cuModuleUnload(self.module));self.ck(self.d.cuCtxDestroy_v2(self.ctx));self.closed=True

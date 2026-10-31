import sys,json,pathlib,hashlib
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
from backend import compile_ptx
ptx,log=compile_ptx(sys.argv[1])
out=pathlib.Path(sys.argv[2]);out.write_bytes(ptx)
print(json.dumps(dict(compiled=True,bytes=len(ptx),sha256=hashlib.sha256(ptx).hexdigest(),log=log)))

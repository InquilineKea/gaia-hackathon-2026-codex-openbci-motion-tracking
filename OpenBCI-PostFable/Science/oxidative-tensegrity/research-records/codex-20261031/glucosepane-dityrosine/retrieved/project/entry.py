"""Original offline installer and bounded pilot supervisor, inside isolation."""
import hashlib, json, os, platform, socket, subprocess, sys, time, venv
from pathlib import Path

ROOT=Path('/project'); OUT=Path('/results')
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(name,obj): (OUT/name).write_text(json.dumps(obj,indent=2)+'\n')
def main():
    status=dict(line.split(':',1) for line in Path('/proc/self/status').read_text().splitlines() if ':' in line)
    checks={'nonroot':os.geteuid()!=0,'no_new_privileges':status['NoNewPrivs'].strip()=='1',
        'no_capabilities':int(status['CapEff'].strip(),16)==0,'seccomp':status['Seccomp'].strip()=='2',
        'network_only_loopback':set(n for _,n in socket.if_nameindex())<={'lo'},
        'readonly_root':bool(os.statvfs('/').f_flag & os.ST_RDONLY),
        'readonly_project':bool(os.statvfs(ROOT).f_flag & os.ST_RDONLY),
        'readonly_wheels':bool(os.statvfs('/wheels').f_flag & os.ST_RDONLY),
        'executable_runtime':not bool(os.statvfs('/runtime').f_flag & os.ST_NOEXEC),
        'python_312':sys.version_info[:2]==(3,12),'x86_64':platform.machine()=='x86_64'}
    dump('isolation.json',{'checks':checks,'python':sys.version,'libc':platform.libc_ver(),'uid':os.geteuid()})
    assert all(checks.values()),checks
    approval=json.loads((ROOT/'approval.json').read_text())
    assert approval['approved'] is True and approval['scope']=='paired_glucosepane_dityrosine_12x50ps'
    assert approval['maximum_compute_wall_seconds']==3600
    assert approval['review_sha256']==sha(ROOT/'SECURITY_REVIEW.md')
    assert approval['manifest_sha256']==sha(ROOT/'MANIFEST.json')
    for name,h in json.loads((ROOT/'MANIFEST.json').read_text()).items():
        path=ROOT/name
        assert path.resolve().is_relative_to(ROOT) and sha(path)==h,name
    lock=json.loads((ROOT/'wheel-lock.json').read_text());assert len(lock['packages'])==9
    for p in lock['packages']: assert sha(Path('/wheels')/p['filename'])==p['sha256'],p['name']
    envdir=Path('/runtime/venv')
    venv.EnvBuilder(with_pip=False,system_site_packages=False,symlinks=True).create(envdir)
    cmd=[sys.executable,'-I','-m','pip','--python',str(envdir/'bin/python'),'--isolated','--disable-pip-version-check',
        'install','--no-index','--no-deps','--only-binary=:all:','--require-hashes','--no-compile','--no-cache-dir',
        '--find-links','/wheels','-r',str(ROOT/'requirements.txt')]
    with (OUT/'install.log').open('w') as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=300,check=True)
    remaining=float(os.environ['CANDIDATE_DEADLINE_UNIX'])-time.time()
    assert 0<remaining<=3600
    start=time.monotonic()
    with (OUT/'candidate.log').open('w') as f:
        try:
            result=subprocess.run([str(envdir/'bin/python'),'-I',str(ROOT/'candidate_pilot.py')],stdout=f,stderr=subprocess.STDOUT,timeout=remaining)
            record={'returncode':result.returncode,'compute_wall_seconds':time.monotonic()-start,'completed_unix_s':time.time()}
        except subprocess.TimeoutExpired:
            record={'timeout':True,'compute_wall_seconds':time.monotonic()-start,'completed_unix_s':time.time()}
    dump('completion.json',record)
    assert record.get('returncode')==0,record
if __name__=='__main__':main()

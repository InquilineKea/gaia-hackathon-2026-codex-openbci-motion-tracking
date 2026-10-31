#!/bin/sh
# Run only inside a reviewed, dedicated offline GPU container with src mounted RO,
# an empty writable /out, no credentials, <=2 CPU cores and <=4 GiB host memory.
# This script cannot provision, start, stop or delete cloud instances.
set -eu
OXT_SRC=${OXT_SRC:-/src}
: "${OXT_NVRTC:?absolute path to the reviewed NVIDIA libnvrtc.so.12 required}"
: "${OXT_CPU_LIBRARY:?absolute path to the CPU library compiled from this src required}"
: "${OXT_FIXTURES:?absolute path to CPU_REFERENCE_SNAPSHOTS.json required}"
: "${OXT_OUT:?absolute writable output directory required}"
[ -d "$OXT_OUT" ]
[ ! -e "$OXT_OUT/COMPLETE.json" ]
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES=0
# Invoke this whole script through timeout --kill-after=10 600.
python3 -I -S "$OXT_SRC/validate_entry.py" --cpu-library "$OXT_CPU_LIBRARY" --nvrtc "$OXT_NVRTC" --gpu --output "$OXT_OUT/operator.json"
python3 -I -S "$OXT_SRC/snapshots_entry.py" --fixtures "$OXT_FIXTURES" --cpu-library "$OXT_CPU_LIBRARY" --ptx "$OXT_OUT/operator.ptx" --output "$OXT_OUT/snapshots.json"
python3 -I -S "$OXT_SRC/benchmark_entry.py" --cpu-library "$OXT_CPU_LIBRARY" --ptx "$OXT_OUT/operator.ptx" --output "$OXT_OUT/benchmark.json"
python3 -I -S -c 'import pathlib,json,os; p=pathlib.Path(os.environ["OXT_OUT"]); reports={n:json.loads((p/(n+".json")).read_text()) for n in ("operator","snapshots","benchmark")}; assert all(r["passed"] for r in reports.values()); (p/"COMPLETE.json").write_text(json.dumps(dict(passed=True,scope="angular operator and frozen states only; no production dynamics"))+"\n")'

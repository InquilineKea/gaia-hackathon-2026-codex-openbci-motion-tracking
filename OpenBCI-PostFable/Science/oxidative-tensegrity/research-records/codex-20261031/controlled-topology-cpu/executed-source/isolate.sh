set -eu
mount --make-rprivate /
mount -t tmpfs -o size=16m tmpfs /mnt
mkdir /mnt/work
mount --bind /tmp/codex-controlled-topology-20261031 /mnt/work
mount --bind /mnt/work/deps /mnt/work/deps
mount -o remount,bind,ro /mnt/work/deps
mount -t tmpfs -o size=16m tmpfs /home
mount -t tmpfs -o size=16m tmpfs /root
mount -t tmpfs -o size=16m tmpfs /tmp
exec env -i PATH=/usr/bin:/bin OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/timeout 1900 /usr/bin/python3 -I -S /mnt/work/sweep.py --mode "$1"

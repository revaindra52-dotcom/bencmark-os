#!/usr/bin/env python3
"""
Benchmark beban kerja terkontrol - Windows vs Linux
Skrip SAMA dijalankan di kedua OS, hasil mentah disimpan ke CSV.

Cara pakai:
    python benchmark.py          -> 10 kali pengulangan (default)
    python benchmark.py 30       -> 30 kali pengulangan

Butuh Python 3.9+ (tanpa library tambahan).
"""
import csv
import datetime
import os
import platform
import random
import socket
import statistics
import sys
import tempfile
import time
import zlib

SEED = 42  # seed tetap supaya data uji identik di kedua OS


# ---------- BEBAN KERJA ----------

def w_cpu_prime():
    """CPU: hitung bilangan prima sampai 300.000 (trial division)."""
    count = 0
    for n in range(2, 300_000):
        is_prime = True
        i = 2
        while i * i <= n:
            if n % i == 0:
                is_prime = False
                break
            i += 1
        if is_prime:
            count += 1
    return count


def _fib(n):
    return n if n < 2 else _fib(n - 1) + _fib(n - 2)


def w_cpu_fibonacci():
    """CPU: Fibonacci rekursif n=30."""
    return _fib(30)


def w_cpu_matrix():
    """CPU: perkalian matriks 120x120."""
    rnd = random.Random(SEED)
    size = 120
    a = [[rnd.random() for _ in range(size)] for _ in range(size)]
    b = [[rnd.random() for _ in range(size)] for _ in range(size)]
    result = [[0.0] * size for _ in range(size)]
    for i in range(size):
        for j in range(size):
            s = 0.0
            for k in range(size):
                s += a[i][k] * b[k][j]
            result[i][j] = s
    return result[0][0]


def w_memory_sort():
    """Memori: buat 1 juta angka acak lalu urutkan."""
    rnd = random.Random(SEED)
    data = [rnd.random() for _ in range(1_000_000)]
    data.sort()
    return sum(data)


def w_compress():
    """CPU+Memori: kompres & dekompres 10 MB data (zlib level 6)."""
    rnd = random.Random(SEED)
    raw = rnd.randbytes(10 * 1024 * 1024)
    packed = zlib.compress(raw, 6)
    return len(zlib.decompress(packed))


def w_disk_write():
    """Disk: tulis 64 MB berurutan + fsync."""
    chunk = b"x" * (1024 * 1024)
    path = os.path.join(tempfile.gettempdir(), "bench_disk.tmp")
    with open(path, "wb") as f:
        for _ in range(64):
            f.write(chunk)
        f.flush()
        os.fsync(f.fileno())
    return path


def w_disk_read():
    """Disk: baca file 64 MB (catatan: bisa kena cache OS)."""
    path = os.path.join(tempfile.gettempdir(), "bench_disk.tmp")
    total = 0
    with open(path, "rb") as f:
        while True:
            data = f.read(1024 * 1024)
            if not data:
                break
            total += len(data)
    os.remove(path)
    return total


# Urutan penting: disk_write harus sebelum disk_read
WORKLOADS = [
    ("cpu_prime", w_cpu_prime),
    ("cpu_fibonacci", w_cpu_fibonacci),
    ("cpu_matrix", w_cpu_matrix),
    ("memory_sort", w_memory_sort),
    ("compress", w_compress),
    ("disk_write", w_disk_write),
    ("disk_read", w_disk_read),
]


# ---------- PROGRAM UTAMA ----------

def main():
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 10

    os_name = platform.system()
    host = socket.gethostname()
    info = {
        "os": os_name,
        "os_version": platform.version(),
        "hostname": host,
        "cpu_count": os.cpu_count(),
        "python_version": platform.python_version(),
    }
    print("Info sistem:", info)

    out_file = f"hasil_{os_name.lower()}_{host}.csv"
    rows = []

    # Pemanasan 1x (tidak dicatat)
    print("Pemanasan...")
    for name, func in WORKLOADS:
        func()

    for run in range(1, runs + 1):
        print(f"Pengulangan {run}/{runs}")
        for name, func in WORKLOADS:
            start = time.perf_counter()
            func()
            elapsed = time.perf_counter() - start
            rows.append({
                "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
                **info,
                "run": run,
                "workload": name,
                "seconds": round(elapsed, 6),
            })

    with open(out_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nData mentah disimpan di: {out_file}\n")
    print(f"{'Beban kerja':<16}{'Rata-rata (s)':>15}{'Std dev':>12}{'Min':>10}{'Max':>10}")
    for name, _ in WORKLOADS:
        vals = [r["seconds"] for r in rows if r["workload"] == name]
        sd = statistics.stdev(vals) if len(vals) > 1 else 0.0
        print(f"{name:<16}{statistics.mean(vals):>15.4f}{sd:>12.4f}{min(vals):>10.4f}{max(vals):>10.4f}")


if __name__ == "__main__":
    main()

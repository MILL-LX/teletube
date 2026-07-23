#!/usr/bin/env python3
"""
debug_cache.py — Testa criação, leitura e validade da cache JSON por ano
"""

import sys
import os
import json
import time
import signal
import datetime
import subprocess

CACHE_DIR   = os.path.join(os.path.dirname(__file__), "..", "cache")
CHANNEL_URL = "https://www.youtube.com/@oficinasconvento"
YEAR_MIN    = 2007
YEAR_MAX    = datetime.datetime.now().year
CACHE_TTL_DAYS = 7

MENU = """
╔══════════════════════════════════════╗
║         DEBUG — Cache                ║
╠══════════════════════════════════════╣
║  1. Listar ficheiros de cache        ║
║  2. Ler cache de um ano              ║
║  3. Criar/atualizar cache de 1 ano   ║
║  4. Verificar validade da cache      ║
║  5. Apagar cache de um ano           ║
║  6. Apagar toda a cache              ║
║  0. Sair                             ║
╚══════════════════════════════════════╝
"""

# ── Cache helpers ─────────────────────────────────────────────────────────
def cache_path(year):
    return os.path.join(CACHE_DIR, f"videos_{year}.json")

def cache_exists(year):
    return os.path.exists(cache_path(year))

def cache_age_days(year):
    path = cache_path(year)
    if not os.path.exists(path):
        return None
    mtime = os.path.getmtime(path)
    return (time.time() - mtime) / 86400

def read_cache(year):
    path = cache_path(year)
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"  [ERRO] Falha ao ler cache: {e}")
        return None

def write_cache(year, videos):
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = cache_path(year)
    data = {
        "year": year,
        "channel": CHANNEL_URL,
        "generated_at": datetime.datetime.now().isoformat(),
        "count": len(videos),
        "videos": videos,
    }
    with open(path, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  [OK] Cache escrita: {path} ({len(videos)} vídeos)")

def fetch_videos_for_year(year):
    """Busca vídeos via yt-dlp (igual ao debug_youtube.py)."""
    after  = f"{year}0101"
    before = f"{year}1231"
    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--print", "%(upload_date)s\t%(id)s\t%(title)s\t%(duration)s",
        "--dateafter",  after,
        "--datebefore", before,
        "--no-warnings",
        CHANNEL_URL,
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        videos = []
        for line in r.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) >= 3:
                date, vid_id, title = parts[0], parts[1], parts[2]
                duration = parts[3] if len(parts) > 3 else "0"
                if date and date[:4] == str(year):
                    videos.append({
                        "id": vid_id,
                        "title": title,
                        "upload_date": date,
                        "duration": duration,
                        "url": f"https://www.youtube.com/watch?v={vid_id}",
                    })
        return videos
    except subprocess.TimeoutExpired:
        print("  [ERRO] Timeout ao consultar o canal.")
        return []
    except Exception as e:
        print(f"  [ERRO] {e}")
        return []

# ── Testes ────────────────────────────────────────────────────────────────
def test_list():
    os.makedirs(CACHE_DIR, exist_ok=True)
    files = sorted([f for f in os.listdir(CACHE_DIR) if f.endswith(".json")])

    if not files:
        print(f"\n  Cache vazia em: {CACHE_DIR}")
        return

    print(f"\n  {len(files)} ficheiro(s) em {CACHE_DIR}:\n")
    total_videos = 0
    for fname in files:
        path = os.path.join(CACHE_DIR, fname)
        age = (time.time() - os.path.getmtime(path)) / 86400
        stale = " [DESATUALIZADA]" if age > CACHE_TTL_DAYS else ""
        try:
            with open(path) as f:
                data = json.load(f)
            count = data.get("count", 0)
            total_videos += count
            gen = data.get("generated_at", "?")[:16]
            print(f"  {fname}  {count:3d} vídeos  gerado: {gen}  idade: {age:.1f}d{stale}")
        except Exception:
            print(f"  {fname}  [ERRO ao ler]")

    print(f"\n  Total: {total_videos} vídeos em cache.")

def test_read():
    try:
        year = int(input(f"  Ano [{YEAR_MIN}-{YEAR_MAX}]: ").strip())
    except ValueError:
        print("  Ano inválido.")
        return

    data = read_cache(year)
    if data is None:
        print(f"  Cache não existe para {year}.")
        return

    print(f"\n  Cache para {year}:")
    print(f"  Gerada em: {data.get('generated_at', '?')}")
    print(f"  Total:     {data.get('count', 0)} vídeos\n")

    for i, v in enumerate(data.get("videos", [])[:10], 1):
        print(f"  {i:2d}. [{v.get('upload_date', '?')}] {v.get('title', '?')[:55]}")

    if data.get("count", 0) > 10:
        print(f"  ... e mais {data['count'] - 10} vídeos.")

def test_build():
    try:
        year = int(input(f"  Ano para construir [{YEAR_MIN}-{YEAR_MAX}]: ").strip())
    except ValueError:
        print("  Ano inválido.")
        return

    if not (YEAR_MIN <= year <= YEAR_MAX):
        print(f"  Fora do intervalo.")
        return

    if cache_exists(year):
        age = cache_age_days(year)
        resp = input(f"  Cache já existe ({age:.1f} dias). Substituir? [s/N]: ").strip().lower()
        if resp != "s":
            print("  Cancelado.")
            return

    print(f"  A construir cache para {year}...")
    start = time.time()
    videos = fetch_videos_for_year(year)
    elapsed = time.time() - start

    if not videos:
        print(f"  Nenhum vídeo encontrado para {year} ({elapsed:.1f}s).")
        write_cache(year, [])
        return

    write_cache(year, videos)
    print(f"  Concluído em {elapsed:.1f}s.")

def test_validate():
    os.makedirs(CACHE_DIR, exist_ok=True)
    print(f"\n  Validade da cache (TTL: {CACHE_TTL_DAYS} dias):\n")
    ok = stale = missing = 0
    for year in range(YEAR_MIN, YEAR_MAX + 1):
        if not cache_exists(year):
            print(f"  {year}: AUSENTE")
            missing += 1
        else:
            age = cache_age_days(year)
            data = read_cache(year)
            count = data.get("count", 0) if data else 0
            if age > CACHE_TTL_DAYS:
                print(f"  {year}: DESATUALIZADA ({age:.1f}d)  {count} vídeos")
                stale += 1
            else:
                print(f"  {year}: OK ({age:.1f}d)  {count} vídeos")
                ok += 1

    print(f"\n  Resumo: {ok} OK  {stale} desatualizadas  {missing} ausentes")

def test_delete_one():
    try:
        year = int(input(f"  Ano a apagar [{YEAR_MIN}-{YEAR_MAX}]: ").strip())
    except ValueError:
        print("  Ano inválido.")
        return

    path = cache_path(year)
    if not os.path.exists(path):
        print(f"  Cache para {year} não existe.")
        return

    resp = input(f"  Apagar {path}? [s/N]: ").strip().lower()
    if resp == "s":
        os.remove(path)
        print(f"  [OK] Apagado.")
    else:
        print("  Cancelado.")

def test_delete_all():
    os.makedirs(CACHE_DIR, exist_ok=True)
    files = [f for f in os.listdir(CACHE_DIR) if f.endswith(".json")]
    if not files:
        print("  Cache já está vazia.")
        return

    resp = input(f"  Apagar {len(files)} ficheiros de cache? [s/N]: ").strip().lower()
    if resp == "s":
        for f in files:
            os.remove(os.path.join(CACHE_DIR, f))
        print(f"  [OK] {len(files)} ficheiros apagados.")
    else:
        print("  Cancelado.")

# ── Main ──────────────────────────────────────────────────────────────────
def main():
    print(MENU)

    def handle_exit(sig, frame):
        sys.exit(0)
    signal.signal(signal.SIGINT, handle_exit)

    while True:
        try:
            choice = input("\nEscolha [0-6]: ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if choice == "1":
            test_list()
        elif choice == "2":
            test_read()
        elif choice == "3":
            test_build()
        elif choice == "4":
            test_validate()
        elif choice == "5":
            test_delete_one()
        elif choice == "6":
            test_delete_all()
        elif choice == "0":
            break
        else:
            print("  Opção inválida.")

if __name__ == "__main__":
    main()

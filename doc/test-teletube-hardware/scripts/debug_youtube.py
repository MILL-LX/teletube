#!/usr/bin/env python3
"""
debug_youtube.py — Testa yt-dlp com o canal @oficinasconvento
Sem API Key — apenas yt-dlp
"""

import sys
import time
import signal
import subprocess
import json
import datetime

CHANNEL_URL = "https://www.youtube.com/@oficinasconvento"
YEAR_MIN    = 2007
YEAR_MAX    = datetime.datetime.now().year

MENU = """
╔══════════════════════════════════════╗
║         DEBUG — YouTube (yt-dlp)     ║
╠══════════════════════════════════════╣
║  1. Verificar yt-dlp instalado       ║
║  2. Listar vídeos de um ano          ║
║  3. Listar anos disponíveis (rápido) ║
║  4. Mostrar detalhes de 1 vídeo      ║
║  5. Obter URL de stream de 1 vídeo   ║
║  0. Sair                             ║
╚══════════════════════════════════════╝
"""

# ── yt-dlp helpers ────────────────────────────────────────────────────────
def check_ytdlp():
    try:
        r = subprocess.run(["yt-dlp", "--version"], capture_output=True, text=True)
        print(f"  [OK] yt-dlp {r.stdout.strip()}")
        return True
    except FileNotFoundError:
        print("  [ERRO] yt-dlp não instalado. Corre: uv add yt-dlp")
        return False

def fetch_videos_for_year(year, max_results=50):
    """
    Usa yt-dlp --flat-playlist para listar vídeos do canal
    e filtra pelo ano de upload.
    """
    after  = f"{year}0101"
    before = f"{year}1231"

    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--print", "%(upload_date)s\t%(id)s\t%(title)s\t%(duration)s",
        "--dateafter",  after,
        "--datebefore", before,
        "--no-warnings",
        "--playlist-end", str(max_results * 3),  # margem para filtro
        CHANNEL_URL,
    ]

    print(f"  A consultar canal para o ano {year}...")
    print(f"  Comando: {' '.join(cmd[:6])} ...")

    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        videos = []
        for line in r.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) >= 3:
                date, vid_id, title = parts[0], parts[1], parts[2]
                duration = parts[3] if len(parts) > 3 else "?"
                if date and date[:4] == str(year):
                    videos.append({
                        "id": vid_id,
                        "title": title,
                        "upload_date": date,
                        "duration": duration,
                        "url": f"https://www.youtube.com/watch?v={vid_id}",
                    })
        if r.stderr and "ERROR" in r.stderr:
            print(f"  [AVISO yt-dlp] {r.stderr[:200]}")
        return videos
    except subprocess.TimeoutExpired:
        print("  [ERRO] Timeout ao consultar o canal (>120s).")
        return []
    except Exception as e:
        print(f"  [ERRO] {e}")
        return []

def get_stream_url(video_id):
    """Obtém a URL de stream direto de um vídeo."""
    cmd = [
        "yt-dlp",
        "--get-url",
        "--format", "best[height<=480]/best",
        "--no-warnings",
        f"https://www.youtube.com/watch?v={video_id}",
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        url = r.stdout.strip().split("\n")[0]
        return url if url.startswith("http") else None
    except Exception as e:
        print(f"  [ERRO] {e}")
        return None

# ── Testes ────────────────────────────────────────────────────────────────
def test_check():
    check_ytdlp()
    print(f"\n  Canal configurado: {CHANNEL_URL}")
    print(f"  Intervalo de anos: {YEAR_MIN} — {YEAR_MAX}")

def test_list_year():
    try:
        year = int(input(f"  Ano [{YEAR_MIN}-{YEAR_MAX}]: ").strip())
    except ValueError:
        print("  Ano inválido.")
        return

    if not (YEAR_MIN <= year <= YEAR_MAX):
        print(f"  Ano fora do intervalo ({YEAR_MIN}-{YEAR_MAX}).")
        return

    start = time.time()
    videos = fetch_videos_for_year(year, max_results=20)
    elapsed = time.time() - start

    if not videos:
        print(f"\n  Nenhum vídeo encontrado para {year}.")
        return

    print(f"\n  {len(videos)} vídeo(s) encontrados para {year} ({elapsed:.1f}s):\n")
    for i, v in enumerate(videos, 1):
        dur = v["duration"]
        try:
            secs = int(dur)
            dur = f"{secs // 60}m{secs % 60:02d}s"
        except (ValueError, TypeError):
            pass
        print(f"  {i:2d}. [{v['upload_date']}] {v['title'][:50]}")
        print(f"      {v['url']}  ({dur})")

def test_list_years():
    print(f"\n  A verificar anos disponíveis ({YEAR_MIN}–{YEAR_MAX})...")
    print("  (consulta rápida: máx. 5 vídeos por ano)\n")

    years_with_videos = []
    for year in range(YEAR_MIN, YEAR_MAX + 1):
        videos = fetch_videos_for_year(year, max_results=5)
        count = len(videos)
        status = f"{count} vídeo(s)" if count > 0 else "sem vídeos"
        marker = " <--" if count > 0 else ""
        print(f"  {year}: {status}{marker}")
        if count > 0:
            years_with_videos.append(year)
        time.sleep(0.5)  # pausa para não sobrecarregar

    print(f"\n  Anos com conteúdo: {years_with_videos}")

def test_video_details():
    video_id = input("  ID do vídeo (ex: dQw4w9WgXcQ): ").strip()
    if not video_id:
        return

    cmd = [
        "yt-dlp",
        "--dump-json",
        "--no-playlist",
        "--no-warnings",
        f"https://www.youtube.com/watch?v={video_id}",
    ]
    print(f"  A obter detalhes de '{video_id}'...")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        data = json.loads(r.stdout)
        print(f"\n  Título:       {data.get('title', '?')}")
        print(f"  Canal:        {data.get('channel', '?')}")
        print(f"  Data upload:  {data.get('upload_date', '?')}")
        print(f"  Duração:      {data.get('duration', '?')}s")
        print(f"  Views:        {data.get('view_count', '?')}")
        print(f"  Formatos disp: {len(data.get('formats', []))}")
    except json.JSONDecodeError:
        print("  [ERRO] Resposta inválida do yt-dlp.")
    except Exception as e:
        print(f"  [ERRO] {e}")

def test_stream_url():
    video_id = input("  ID do vídeo: ").strip()
    if not video_id:
        return
    print(f"  A obter URL de stream para '{video_id}'...")
    url = get_stream_url(video_id)
    if url:
        print(f"\n  URL de stream:\n  {url[:100]}...")
    else:
        print("  [ERRO] Não foi possível obter URL de stream.")

# ── Main ──────────────────────────────────────────────────────────────────
def main():
    print(MENU)

    def handle_exit(sig, frame):
        sys.exit(0)
    signal.signal(signal.SIGINT, handle_exit)

    while True:
        try:
            choice = input("\nEscolha [0-5]: ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if choice == "1":
            test_check()
        elif choice == "2":
            test_list_year()
        elif choice == "3":
            test_list_years()
        elif choice == "4":
            test_video_details()
        elif choice == "5":
            test_stream_url()
        elif choice == "0":
            break
        else:
            print("  Opção inválida.")

if __name__ == "__main__":
    main()

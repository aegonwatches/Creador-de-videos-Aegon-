#!/usr/bin/env python3
"""
Aegon TikTok Batch Generator
------------------------------
El "bot": le das una carpeta con subcarpetas de fotos (una por modelo) y un
config.json con título/precio/CTA de cada uno, y te genera un vídeo TikTok
por cada carpeta automáticamente. También puede sacar varias variaciones
del mismo modelo (distinto orden/zoom) para tener contenido variado sin
repetir el mismo vídeo.

ESTRUCTURA ESPERADA:

    product_photos/
        skeleton/
            foto1.jpg
            foto2.jpg
        mesh/
            foto1.jpg
            foto2.jpg
        wood/
            foto1.jpg

    config.json
        {
          "skeleton": {"title": "SKELETON", "price": "89€", "variations": 2},
          "mesh":     {"title": "MESH",     "price": "89€"},
          "wood":     {"title": "WOOD",     "price": "119€"}
        }

USO:
    python batch_generate.py --photos ./product_photos --config ./config.json --out ./out
"""

import argparse
import glob
import json
import os
import random
from pathlib import Path

from make_tiktok import build_video

DEFAULT_CTA = "DM PARA COMPRAR"
DEFAULT_WATERMARK = "AEGON"
IMAGE_EXTS = ("*.jpg", "*.jpeg", "*.png", "*.webp")


def find_images(folder):
    files = []
    for ext in IMAGE_EXTS:
        files.extend(glob.glob(os.path.join(folder, ext)))
    return sorted(files)


def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_batch(photos_dir, config_path, out_dir, music_dir=None):
    config = load_config(config_path)
    os.makedirs(out_dir, exist_ok=True)

    results = []
    for folder_name, meta in config.items():
        folder_path = os.path.join(photos_dir, folder_name)
        if not os.path.isdir(folder_path):
            print(f"[AVISO] No existe la carpeta '{folder_path}', se salta.")
            continue

        images = find_images(folder_path)
        if not images:
            print(f"[AVISO] No hay imágenes en '{folder_path}', se salta.")
            continue

        title = meta.get("title", folder_name.upper())
        price = meta.get("price", "")
        cta = meta.get("cta", DEFAULT_CTA)
        watermark = meta.get("watermark", DEFAULT_WATERMARK)
        variations = int(meta.get("variations", 1))

        # música: usa la indicada en el config, o busca una carpeta de música por modelo
        music_path = meta.get("music")
        if not music_path and music_dir:
            for ext in ("*.mp3", "*.wav", "*.m4a"):
                found = glob.glob(os.path.join(music_dir, ext))
                if found:
                    music_path = random.choice(found)
                    break

        for v in range(1, variations + 1):
            imgs = images[:]
            if variations > 1:
                random.shuffle(imgs)  # cada variación con orden distinto de fotos

            suffix = f"_v{v}" if variations > 1 else ""
            output_path = os.path.join(out_dir, f"{folder_name}{suffix}.mp4")

            print(f"-> Generando {output_path} ({len(imgs)} fotos)")
            build_video(
                imgs, output_path, title, price, cta,
                music=music_path, watermark=watermark,
            )
            results.append(output_path)

    print(f"\nListo. {len(results)} vídeo(s) generado(s) en '{out_dir}':")
    for r in results:
        print(" -", r)
    return results


def parse_args():
    p = argparse.ArgumentParser(description="Genera en lote vídeos TikTok Aegon a partir de varias carpetas de fotos.")
    p.add_argument("--photos", required=True, help="Carpeta con subcarpetas de fotos por modelo")
    p.add_argument("--config", required=True, help="Ruta al config.json con título/precio por modelo")
    p.add_argument("--out", default="./out", help="Carpeta de salida de los vídeos")
    p.add_argument("--music-dir", default=None, help="Carpeta con pistas de música (mp3/wav) para elegir al azar")
    return p.parse_args()


def main():
    args = parse_args()
    run_batch(args.photos, args.config, args.out, args.music_dir)


if __name__ == "__main__":
    main()

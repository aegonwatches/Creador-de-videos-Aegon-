#!/usr/bin/env python3
"""
Aegon TikTok Generator
-----------------------
Convierte imágenes de producto en un vídeo vertical (1080x1920) listo para
TikTok/Reels, con efecto Ken Burns (zoom/pan suave), transiciones en
crossfade, overlay de texto en estilo Aegon (fondo oscuro, dorado, serif)
y música de fondo opcional.

USO BÁSICO:
    python make_tiktok.py \
        --images ./sample_images \
        --output ./out/skeleton.mp4 \
        --title "SKELETON" \
        --price "89€" \
        --cta "DM PARA COMPRAR"

USO CON MÚSICA:
    python make_tiktok.py --images ./sample_images --output ./out/skeleton.mp4 \
        --title "SKELETON" --price "89€" --music ./music/track.mp3

Requisitos: pip install -r requirements.txt  (y tener ffmpeg instalado)
"""

import argparse
import glob
import os
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from moviepy.editor import (
    ImageClip,
    CompositeVideoClip,
    concatenate_videoclips,
    AudioFileClip,
    CompositeAudioClip,
    vfx,
)

# ---------- CONFIG DE MARCA ----------
W, H = 1080, 1920               # formato vertical TikTok
GOLD = (198, 166, 100)          # dorado Aegon
BG_DARK = (10, 10, 10)
FONT_DIR = Path(__file__).parent / "fonts"

# Coloca aquí tus .ttf reales para que el texto salga con la tipografía de marca.
# Si no existen, se usa una fuente serif del sistema como fallback.
SERIF_FONT_CANDIDATES = [
    FONT_DIR / "CormorantGaramond-Regular.ttf",
    FONT_DIR / "CormorantGaramond-SemiBold.ttf",
]
SANS_FONT_CANDIDATES = [
    FONT_DIR / "Jost-Regular.ttf",
    FONT_DIR / "Jost-Medium.ttf",
]


def load_font(candidates, size, fallback_bold=False):
    for c in candidates:
        if c.exists():
            return ImageFont.truetype(str(c), size)
    # fallback: fuente del sistema (no es la de marca, pero no rompe el script)
    system_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf" if fallback_bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
    ]
    for p in system_paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def make_text_overlay(title, price, cta, watermark="AEGON"):
    """Genera un PNG transparente (1080x1920) con el overlay de texto estilo Aegon."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # --- gradiente oscuro inferior para que el texto siempre se lea ---
    grad_h = 700
    gradient = Image.new("L", (1, grad_h), color=0)
    for y in range(grad_h):
        gradient.putpixel((0, y), int(255 * (y / grad_h) ** 1.6))
    gradient = gradient.resize((W, grad_h))
    black = Image.new("RGBA", (W, grad_h), BG_DARK + (0,))
    black.putalpha(gradient)
    img.alpha_composite(black, (0, H - grad_h))

    # --- watermark de marca arriba ---
    f_water = load_font(SANS_FONT_CANDIDATES, 44)
    draw.text((W // 2, 100), watermark, font=f_water, fill=GOLD + (230,), anchor="mm")
    # línea fina bajo el watermark
    draw.line([(W // 2 - 60, 140), (W // 2 + 60, 140)], fill=GOLD + (200,), width=2)

    # --- título del modelo ---
    f_title = load_font(SERIF_FONT_CANDIDATES, 96)
    draw.text((W // 2, H - 430), title.upper(), font=f_title, fill=(255, 255, 255, 255), anchor="mm")

    # --- precio ---
    f_price = load_font(SANS_FONT_CANDIDATES, 58)
    draw.text((W // 2, H - 330), price, font=f_price, fill=GOLD + (255,), anchor="mm")

    # --- CTA con caja ---
    f_cta = load_font(SANS_FONT_CANDIDATES, 40)
    cta_w = draw.textlength(cta, font=f_cta)
    box_pad_x, box_pad_y = 40, 22
    box_w, box_h = cta_w + box_pad_x * 2, 40 + box_pad_y * 2
    box_x0 = (W - box_w) / 2
    box_y0 = H - 200
    draw.rounded_rectangle(
        [box_x0, box_y0, box_x0 + box_w, box_y0 + box_h],
        radius=6, outline=GOLD + (255,), width=2
    )
    draw.text((W // 2, box_y0 + box_h / 2), cta, font=f_cta, fill=(255, 255, 255, 255), anchor="mm")

    return img


def ken_burns_clip(image_path, duration, zoom_start=1.0, zoom_end=1.18, direction=None):
    """Crea un clip con efecto Ken Burns (zoom lento) ajustado a formato vertical."""
    pil_img = Image.open(image_path).convert("RGB")

    # cover del frame vertical 1080x1920 sin deformar
    img_ratio = pil_img.width / pil_img.height
    target_ratio = W / H
    if img_ratio > target_ratio:
        new_h = H
        new_w = int(H * img_ratio)
    else:
        new_w = W
        new_h = int(W / img_ratio)
    pil_img = pil_img.resize((new_w, new_h), Image.LANCZOS)

    # recorte centrado al lienzo base antes del zoom
    left = (new_w - W) // 2
    top = (new_h - H) // 2
    pil_img = pil_img.crop((left, top, left + W, top + H))

    base = np.array(pil_img)
    clip = ImageClip(base).set_duration(duration)

    if direction is None:
        direction = random.choice(["in", "out"])

    def zoom(t):
        progress = t / duration
        if direction == "in":
            return zoom_start + (zoom_end - zoom_start) * progress
        else:
            return zoom_end - (zoom_end - zoom_start) * progress

    clip = clip.fl(lambda gf, t: _zoomed_frame(gf(t), zoom(t)), apply_to=["mask"])
    return clip


def _zoomed_frame(frame, factor):
    """Aplica zoom centrado a un frame numpy sin cambiar sus dimensiones."""
    h, w = frame.shape[:2]
    new_w, new_h = int(w * factor), int(h * factor)
    img = Image.fromarray(frame).resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - w) // 2
    top = (new_h - h) // 2
    img = img.crop((left, top, left + w, top + h))
    return np.array(img)


def build_video(images, output, title, price, cta, music=None,
                 seconds_per_image=2.6, crossfade=0.5, watermark="AEGON"):
    if not images:
        raise ValueError("No se encontraron imágenes en la carpeta indicada.")

    clips = []
    for path in images:
        c = ken_burns_clip(path, seconds_per_image + crossfade)
        clips.append(c)

    # crossfade entre clips
    for i in range(1, len(clips)):
        clips[i] = clips[i].crossfadein(crossfade)

    video = concatenate_videoclips(clips, method="compose", padding=-crossfade)

    # overlay de texto (una sola vez, fijo encima de todo el vídeo)
    overlay_img = make_text_overlay(title, price, cta, watermark)
    overlay_clip = (ImageClip(np.array(overlay_img))
                     .set_duration(video.duration)
                     .set_position((0, 0)))

    final = CompositeVideoClip([video, overlay_clip], size=(W, H))

    if music and os.path.exists(music):
        audio = AudioFileClip(music).subclip(0, min(final.duration, AudioFileClip(music).duration))
        audio = audio.fx(vfx.fadeout, 1.0) if hasattr(audio, "fx") else audio
        audio = audio.audio_fadeout(1.0).audio_fadein(0.5).volumex(0.9)
        final = final.set_audio(audio)

    os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
    final.write_videofile(
        output, fps=30, codec="libx264", audio_codec="aac",
        preset="medium", threads=4, bitrate="6000k", logger=None
    )
    return output


def parse_args():
    p = argparse.ArgumentParser(description="Genera vídeos TikTok Aegon a partir de imágenes de producto.")
    p.add_argument("--images", required=True, help="Carpeta con las imágenes (jpg/png)")
    p.add_argument("--output", required=True, help="Ruta del mp4 de salida")
    p.add_argument("--title", required=True, help="Nombre del modelo, ej. SKELETON")
    p.add_argument("--price", required=True, help="Precio a mostrar, ej. 89€")
    p.add_argument("--cta", default="DM PARA COMPRAR", help="Texto del call to action")
    p.add_argument("--watermark", default="AEGON", help="Texto de marca arriba")
    p.add_argument("--music", default=None, help="Ruta a mp3/wav opcional de fondo")
    p.add_argument("--seconds-per-image", type=float, default=2.6)
    p.add_argument("--crossfade", type=float, default=0.5)
    return p.parse_args()


def main():
    args = parse_args()
    exts = ("*.jpg", "*.jpeg", "*.png", "*.webp")
    images = []
    for ext in exts:
        images.extend(sorted(glob.glob(os.path.join(args.images, ext))))
    if not images:
        raise SystemExit(f"No hay imágenes en {args.images}")

    print(f"Procesando {len(images)} imágenes -> {args.output}")
    build_video(
        images, args.output, args.title, args.price, args.cta,
        music=args.music, seconds_per_image=args.seconds_per_image,
        crossfade=args.crossfade, watermark=args.watermark,
    )
    print("Listo:", args.output)


if __name__ == "__main__":
    main()

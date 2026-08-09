"""
Aegon TikTok Generator — Web App
----------------------------------
App web con Streamlit: sube fotos, pon título/precio, genera el vídeo,
descárgalo. Sin terminal, sin instalar nada, funciona en móvil.

Para correrla en local (opcional, no necesario si la despliegas en la nube):
    streamlit run app.py
"""

import os
import tempfile
import streamlit as st

from make_tiktok import build_video

st.set_page_config(page_title="Aegon TikTok Generator", page_icon="⌚", layout="centered")

# ---------- Estilo simple, coherente con la marca ----------
st.markdown(
    """
    <style>
    .stApp { background-color: #0b0b0c; color: #f2f2f2; }
    h1, h2, h3 { color: #c9a961 !important; }
    .stButton>button {
        background-color: #c9a961; color: #0b0b0c; font-weight: 600;
        border: none; border-radius: 4px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("⌚ AEGON — Generador de vídeos TikTok")
st.caption("Sube las fotos del modelo, rellena los datos y descarga el vídeo listo para publicar.")

with st.form("video_form"):
    fotos = st.file_uploader(
        "Fotos del producto (2-6 recomendado, en orden)",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        titulo = st.text_input("Título del modelo", value="SKELETON")
    with col2:
        precio = st.text_input("Precio", value="89€")

    cta = st.text_input("Texto del botón (CTA)", value="DM PARA COMPRAR")
    musica = st.file_uploader("Música de fondo (opcional)", type=["mp3", "wav", "m4a"])

    segundos = st.slider("Segundos por foto", 1.5, 4.0, 2.6, 0.1)

    submitted = st.form_submit_button("🎬 Generar vídeo")

if submitted:
    if not fotos:
        st.error("Sube al menos una foto.")
    else:
        with st.spinner("Generando el vídeo… puede tardar 30-90 segundos."):
            with tempfile.TemporaryDirectory() as tmp:
                image_paths = []
                for i, foto in enumerate(fotos):
                    path = os.path.join(tmp, f"foto_{i}_{foto.name}")
                    with open(path, "wb") as f:
                        f.write(foto.getbuffer())
                    image_paths.append(path)

                music_path = None
                if musica:
                    music_path = os.path.join(tmp, musica.name)
                    with open(music_path, "wb") as f:
                        f.write(musica.getbuffer())

                output_path = os.path.join(tmp, "output.mp4")

                try:
                    build_video(
                        image_paths, output_path, titulo, precio, cta,
                        music=music_path, seconds_per_image=segundos,
                    )
                    with open(output_path, "rb") as f:
                        video_bytes = f.read()

                    st.success("¡Vídeo listo!")
                    st.video(video_bytes)
                    st.download_button(
                        "⬇️ Descargar MP4",
                        data=video_bytes,
                        file_name=f"aegon_{titulo.lower()}.mp4",
                        mime="video/mp4",
                    )
                except Exception as e:
                    st.error(f"Error generando el vídeo: {e}")

st.divider()
st.caption("Aegon · Herramienta interna de producción de contenido")

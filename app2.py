import streamlit as st
import rasterio
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import os

# Configuración de la página
st.set_page_config(
    page_title="Aptitud Solar - Paraguay",
    page_icon="🌞",
    layout="wide"
)

# Título principal
st.title("🌞 Predicción de Aptitud para Granjas Solares en Paraguay")
st.markdown("---")

# Cargar el raster de aptitud
@st.cache_resource
def load_raster():
    raster_path = "Mapa_Aptitud_Predicha_NN.tif"
    if not os.path.exists(raster_path):
        st.error("⚠️ Archivo de mapa no encontrado")
        return None, None
    
    with rasterio.open(raster_path) as src:
        data = src.read(1)
        # Enmascarar NaN
        data = np.ma.masked_where(np.isnan(data), data)
        return data, src

mapa, src = load_raster()

if mapa is not None:
    # Crear dos columnas
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("🗺️ Mapa de Aptitud Solar")
        
        # Crear figura con matplotlib
        fig, ax = plt.subplots(figsize=(10, 8))
        im = ax.imshow(mapa, cmap='viridis', vmin=0, vmax=1)
        plt.colorbar(im, ax=ax, label='Índice de Aptitud (0-1)', shrink=0.8)
        ax.set_title("Zonas óptimas para granjas solares")
        ax.axis('off')
        
        # Mostrar en Streamlit
        st.pyplot(fig)
    
    with col2:
        st.subheader("📊 Rendimiento de Modelos")
        
        # Métricas en tarjetas
        st.markdown("### Regresión Lineal")
        col_r1, col_r2, col_r3 = st.columns(3)
        with col_r1:
            st.metric("RMSE", "0.1243")
        with col_r2:
            st.metric("MAE", "0.0978")
        with col_r3:
            st.metric("R²", "0.7321")

        st.markdown("### Red Neuronal")
        col_n1, col_n2, col_n3 = st.columns(3)
        with col_n1:
            st.metric("RMSE", "0.0532", "▼ 57%")
        with col_n2:
            st.metric("MAE", "0.0347", "▼ 65%")
        with col_n3:
            st.metric("R²", "0.9508", "▲")

        st.caption(
            "Métricas sobre un split de test espacialmente independiente (bloques geográficos "
            "que no comparten vecinos con el set de entrenamiento), no un split aleatorio por "
            "píxel — evita la fuga espacial que infla el R² artificialmente."
        )

        # Información del modelo
        st.markdown("---")
        st.subheader("🔍 Detalles del Modelo")
        st.markdown("""
        **Arquitectura:**
        - Capa 1: 128 neuronas (ReLU, BatchNorm, Dropout 0.3)
        - Capa 2: 64 neuronas (ReLU, BatchNorm, Dropout 0.2)
        - Salida: Sigmoide

        **Features:**
        - GHI (Global Solar Atlas — independiente del GHI usado para construir el target)
        - Índice de nubosidad
        - Pendiente
        - Uso de suelo (one-hot)
        - Áreas protegidas (MADES)
        """)
    
    # Sección interactiva
    st.markdown("---")
    st.subheader("📍 Consultar punto específico")
    
    col_lat, col_lon, col_btn = st.columns([1, 1, 1])
    with col_lat:
        lat = st.number_input("Latitud", -27.0, -19.0, -25.0, step=0.1)
    with col_lon:
        lon = st.number_input("Longitud", -62.0, -54.0, -57.0, step=0.1)
    with col_btn:
        st.write("")  # Espaciador
        st.write("")  # Espaciador
        if st.button("🔍 Predecir aptitud"):
            try:
                col_pixel, row_pixel = src.index(lon, lat)
                if 0 <= row_pixel < src.height and 0 <= col_pixel < src.width:
                    aptitud = mapa[row_pixel, col_pixel]
                    if not np.ma.is_masked(aptitud) and not np.isnan(aptitud):
                        st.success(f"✨ La aptitud del mapa en ese punto es: **{aptitud:.3f}**")
                    else:
                        st.warning("Sin datos de aptitud para estas coordenadas (fuera de Paraguay, "
                                   "área protegida o uso de suelo incompatible).")
                else:
                    st.error("Coordenadas fuera del área de estudio (Paraguay).")
            except Exception as e:
                st.error(f"Error: {str(e)}")
    
    # Footer
    st.markdown("---")
    st.markdown("**Tesis de Maestría en Ciencias de la Inteligencia Artificial** | © 2024")

else:
    st.error("❌ No se pudo cargar el mapa de aptitud. Verifica que el archivo exista.")
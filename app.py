import streamlit as st
import rasterio
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from rasterio.transform import rowcol
from rasterio.mask import mask
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import shapely.geometry
import os
import tempfile
from folium.plugins import Draw

# Configuración de la página
st.set_page_config(
    page_title="Aptitud Solar - Paraguay",
    page_icon="🌞",
    layout="wide"
)

# Título principal
st.title("🌞 Análisis de Aptitud para Granjas Solares en Paraguay")
st.markdown("---")

RASTER_FILENAME = "Mapa_Aptitud_web.tif"

# El raster original (30m, ~216MB) satura la RAM del tier gratuito de Streamlit
# Cloud (~1GB) apenas se descarga y carga -> el healthcheck moría con "EOF".
# La app usa esta versión reescalada (~600m/píxel, <1MB), bundleada en el repo,
# más que suficiente para explorar el mapa a escala país/región. El raster
# original de 30m sigue disponible para descarga en el dataset de Hugging Face
# (ver README) para quien necesite la resolución completa.
HF_FULL_RES_DATASET = "mykutest/tesis-solar-aptitud-data"


# Cargar el raster de aptitud
@st.cache_resource
def load_raster():
    if not os.path.exists(RASTER_FILENAME):
        st.error(f"⚠️ No se encontró {RASTER_FILENAME} en el repositorio.")
        return None, None, None

    with rasterio.open(RASTER_FILENAME) as src:
        data = src.read(1)
        # Enmascarar NaN
        data = np.ma.masked_where(np.isnan(data), data)
        bounds = src.bounds
        return data, src, bounds

mapa, src, bounds = load_raster()

if mapa is not None and src is not None:
    # Crear dos columnas principales
    col_left, col_right = st.columns([1.5, 1])
    
    with col_left:
        st.subheader("🗺️ Mapa Interactivo")
        
        # Crear mapa base con Folium
        m = folium.Map(
            location=[-23.5, -58.0],
            zoom_start=6,
            control_scale=True
        )
        
        # Añadir tiles
        folium.TileLayer('OpenStreetMap').add_to(m)
        
        # Añadir el raster como overlay (necesitamos crear una imagen PNG temporal)
        # Normalizar datos para visualización
        mapa_normalized = mapa.copy()
        if np.ma.is_masked(mapa_normalized):
            # Para datos enmascarados, llenar NaN con 0 para visualización
            mapa_vis = mapa_normalized.filled(0)
        else:
            mapa_vis = mapa_normalized
            mapa_vis = np.nan_to_num(mapa_vis, nan=0)
        
        # Crear overlay del raster usando ImageOverlay
        from folium.raster_layers import ImageOverlay
        from branca.colormap import LinearColormap
        
        # Crear colormap
        colormap = LinearColormap(
            colors=['darkblue', 'blue', 'cyan', 'yellow', 'red'],
            vmin=0, vmax=1,
            caption='Índice de Aptitud'
        )
        
        # Añadir overlay
        ImageOverlay(
            image=mapa_vis,
            bounds=[[bounds.bottom, bounds.left], [bounds.top, bounds.right]],
            colormap=lambda x: colormap(x),
            name='Aptitud Solar',
            opacity=0.7
        ).add_to(m)
        
        # Añadir herramienta de dibujo
        draw = Draw(
            draw_options={
                'polygon': True,
                'rectangle': True,
                'circle': False,
                'marker': False,
                'polyline': False,
                'circlemarker': False
            },
            edit_options={'edit': True, 'remove': True}
        )
        draw.add_to(m)
        
        # Añadir control de capas
        folium.LayerControl().add_to(m)
        
        # Mostrar mapa en Streamlit
        output = st_folium(m, width=700, height=500)
        
        # Procesar polígono dibujado
        if output and 'all_drawings' in output and output['all_drawings']:
            drawings = output['all_drawings']
            for drawing in drawings:
                if drawing['geometry']['type'] == 'Polygon':
                    # Convertir a GeoDataFrame
                    coords = drawing['geometry']['coordinates'][0]
                    polygon = shapely.geometry.Polygon([(coord[1], coord[0]) for coord in coords])
                    gdf = gpd.GeoDataFrame([1], geometry=[polygon], crs="EPSG:4326")
                    
                    # Guardar en sesión
                    st.session_state['drawn_polygon'] = gdf
                    st.session_state['polygon_source'] = 'drawn'
                    break
    
    with col_right:
        st.subheader("📊 Resultados del Análisis")
        
        # Opciones de entrada de área
        option = st.radio(
            "Seleccionar área de interés:",
            ["Usar polígono dibujado", "Subir archivo SHP", "Coordenadas individuales"],
            key='input_option'
        )
        
        gdf_area = None
        
        if option == "Usar polígono dibujado":
            if 'drawn_polygon' in st.session_state:
                gdf_area = st.session_state['drawn_polygon']
                st.success("✅ Polígono cargado desde el mapa")
            else:
                st.info("👉 Dibuja un polígono en el mapa para comenzar")
        
        elif option == "Subir archivo SHP":
            uploaded_file = st.file_uploader("Subir archivo SHP", type=['shp', 'zip'])
            if uploaded_file:
                # Guardar archivo temporal
                with tempfile.NamedTemporaryFile(delete=False, suffix='.shp') as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name
                
                try:
                    gdf_area = gpd.read_file(tmp_path)
                    gdf_area = gdf_area.to_crs("EPSG:4326")
                    st.success(f"✅ Archivo cargado: {len(gdf_area)} polígono(s)")
                except Exception as e:
                    st.error(f"Error al leer SHP: {str(e)}")
        
        else:  # Coordenadas individuales
            st.markdown("### Ingresar punto")
            col_lat, col_lon = st.columns(2)
            with col_lat:
                lat = st.number_input("Latitud", value=-25.0, format="%.4f")
            with col_lon:
                lon = st.number_input("Longitud", value=-57.0, format="%.4f")
            
            if st.button("Consultar punto"):
                try:
                    col_pixel, row_pixel = src.index(lon, lat)
                    if 0 <= row_pixel < src.height and 0 <= col_pixel < src.width:
                        aptitud = mapa[row_pixel, col_pixel]
                        if not np.ma.is_masked(aptitud) and not np.isnan(aptitud):
                            st.metric("Aptitud", f"{aptitud:.3f}")
                            if aptitud > 0.7:
                                st.success("Excelente ubicación!")
                            elif aptitud > 0.3:
                                st.warning("Aptitud moderada")
                            else:
                                st.error("Baja aptitud")
                        else:
                            st.error("Sin datos para estas coordenadas")
                    else:
                        st.error("Coordenadas fuera del área de estudio")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
        
        # Procesar polígono si existe
        if gdf_area is not None:
            try:
                # Reprojectar a CRS del raster
                gdf_area = gdf_area.to_crs(src.crs)
                
                # Extraer valores del raster dentro del polígono
                out_image, out_transform = mask(src, gdf_area.geometry, crop=True)
                out_image = out_image[0]  # Primera banda
                
                # Enmascarar NaN
                out_image = np.ma.masked_where(np.isnan(out_image), out_image)
                
                if not np.ma.is_masked(out_image) or out_image.compressed().size > 0:
                    # Calcular estadísticas
                    valores = out_image.compressed()
                    aptitud_media = np.mean(valores)
                    aptitud_std = np.std(valores)
                    aptitud_min = np.min(valores)
                    aptitud_max = np.max(valores)
                    area_km2 = gdf_area.geometry.area[0] / 1e6  # Convertir m² a km²
                    
                    # Mostrar resultados
                    st.markdown("---")
                    st.markdown("### 📈 Estadísticas del área seleccionada")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Aptitud Media", f"{aptitud_media:.3f}")
                        st.metric("Desviación Estándar", f"{aptitud_std:.3f}")
                        st.metric("Área", f"{area_km2:.2f} km²")
                    with col2:
                        st.metric("Aptitud Mínima", f"{aptitud_min:.3f}")
                        st.metric("Aptitud Máxima", f"{aptitud_max:.3f}")
                        st.metric("Píxeles", f"{len(valores)}")
                    
                    # Histograma
                    fig, ax = plt.subplots(figsize=(8, 4))
                    ax.hist(valores, bins=30, color='green', alpha=0.7, edgecolor='black')
                    ax.axvline(aptitud_media, color='red', linestyle='--', label=f'Media: {aptitud_media:.3f}')
                    ax.set_xlabel('Aptitud')
                    ax.set_ylabel('Frecuencia')
                    ax.set_title('Distribución de Aptitud en el área')
                    ax.legend()
                    ax.grid(True, alpha=0.3)
                    st.pyplot(fig)
                    
                    # Clasificación del área
                    st.markdown("### 🏷️ Clasificación")
                    if aptitud_media > 0.7:
                        st.success("🌟 **Alta aptitud**: Área muy favorable para granjas solares")
                    elif aptitud_media > 0.4:
                        st.warning("⚠️ **Aptitud media**: Área viable con limitaciones")
                    else:
                        st.error("❌ **Baja aptitud**: Área no recomendada")
                    
                    # Recomendación
                    if aptitud_std < 0.1:
                        st.info("📊 **Homogéneo**: El área tiene condiciones uniformes")
                    else:
                        st.info("📊 **Heterogéneo**: Hay variabilidad significativa dentro del área")
                    
                else:
                    st.warning("⚠️ El área seleccionada no contiene datos de aptitud válidos")
                    
            except Exception as e:
                st.error(f"Error al procesar el polígono: {str(e)}")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    **Tesis de Maestría en Ciencias de la Inteligencia Artificial** | © 2024
    *Red neuronal (R² ≈ 0.95 en test espacialmente independiente) entrenada con GHI del Global Solar Atlas,
    nubosidad, pendiente, uso de suelo y áreas protegidas (MADES) como restricciones de exclusión.*
    """)

else:
    st.error("❌ No se pudo cargar el mapa de aptitud. Verifica que el archivo exista en el directorio.")
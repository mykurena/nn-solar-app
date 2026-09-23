# 🌞 Aptitud Solar Paraguay

Aplicación interactiva (Streamlit) para explorar el mapa de aptitud para granjas solares en Paraguay,
generado con una red neuronal entrenada sobre GHI (Global Solar Atlas), nubosidad, pendiente, uso de
suelo y áreas protegidas (MADES). 

![Mapa de aptitud solar](preview_mapa_aptitud.png)

## Modelo

| Modelo | RMSE | MAE | R² |
|---|---|---|---|
| Regresión Lineal | 0.1243 | 0.0978 | 0.7321 |
| Red Neuronal | 0.0532 | 0.0347 | 0.9508 |

Métricas sobre un split de test **espacialmente independiente** (bloques geográficos separados del
entrenamiento), no un split aleatorio por píxel. El GHI usado como input del modelo (Global Solar Atlas)
es una fuente independiente del GHI (NASA-FLDAS) con el que se construyó el índice de aptitud objetivo,
para evitar que el modelo simplemente reconstruya su propia fórmula.

## Datos

El raster `Mapa_Aptitud_Predicha_NN.tif` (~216MB) no está en este repositorio por su tamaño (supera el
límite de GitHub). Se aloja en un dataset público de Hugging Face y la app lo descarga automáticamente
la primera vez que corre:
[mykutest/tesis-solar-aptitud-data](https://huggingface.co/datasets/mykutest/tesis-solar-aptitud-data)

## Correr localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

La primera ejecución descarga el raster (~216MB) desde Hugging Face y lo cachea localmente.

## Despliegue

Pensada para **[Streamlit Community Cloud](https://streamlit.io/cloud)** (gratis): conectá este
repositorio de GitHub, elegí `app.py` como entry point, y listo — no necesita Docker ni variables de
entorno, el raster se descarga solo en el primer arranque.

También incluye un `Dockerfile` por si se prefiere desplegar en cualquier otro servicio que soporte
contenedores (Render, Railway, un Space de Hugging Face con plan PRO, etc.):

```bash
docker build -t aptitud-solar .
docker run -p 7860:7860 aptitud-solar
```

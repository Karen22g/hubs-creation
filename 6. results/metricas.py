from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
import pandas as pd
import numpy as np
import folium
import matplotlib.cm as cm
import matplotlib.colors as colors
from sklearn.neighbors import NearestNeighbors
from math import radians, sin, cos, sqrt, atan2
import matplotlib.pyplot as plt
import plotly.express as px
from sklearn.cluster import AgglomerativeClustering

def distancias_centroide_cluster(df):
        lat_cm = (df['lat'] * df['cargas']).sum() / df['cargas'].sum()
        lng_cm = (df['lng'] * df['cargas']).sum() / df['cargas'].sum()
        dists = [haversine(lat, lng, lat_cm, lng_cm) for lat, lng in zip(df["lat"], df["lng"])]
        return pd.Series({
            "c_dist_min": np.min(dists),
            "c_dist_q1": np.percentile(dists, 25),
            "c_dist_mean": np.mean(dists),
            "c_dist_q2": np.percentile(dists, 50),
            "c_dist_q3": np.percentile(dists, 75),
            "c_dist_max": np.max(dists)
        })

def generar_resultado(df, ciudades_ref, state):
    # Separar clústeres válidos
    print(df.shape)
    df_valid = df[df['cluster'] != -1]
    print(df_valid.shape)
    # Calcular resumen solo para clústeres distintos de -1
    resumen_valid = (
        df_valid.groupby('cluster')
        .apply(distancias_centroide_cluster)
        .join(df_valid.groupby('cluster')['cargas'].sum().rename('total_cargas'))
        .join(df_valid.groupby('cluster').size().rename('n_coordenadas'))
    )

    # Calcular el clúster -1 por separado (solo total de cargas y puntos)
    df_ruido = df[df['cluster'] == -1]
    if not df_ruido.empty:
        resumen_ruido = pd.DataFrame({
            'cluster': [-1],
            'dist_promedio': [np.nan],
            'dist_max': [np.nan],
            'dist_min': [np.nan],
            'total_cargas': [df_ruido['cargas'].sum()],
            'n_coordenadas': [len(df_ruido)],
        }).set_index('cluster')
        resumen = pd.concat([resumen_valid, resumen_ruido])
    else:
        resumen = resumen_valid

    resumen = resumen.reset_index()

    # Cálculo de porcentajes
    total_estado = df['cargas'].sum()
    resumen['%_estado_-1'] = resumen['total_cargas'] / total_estado * 100

    total_sin1 = df_valid['cargas'].sum()
    resumen['%_estado'] = resumen['total_cargas'] / total_sin1 * 100
    resumen.loc[resumen['cluster'] == -1, '%_estado'] = 0

    resumen['%_acumulado_-1'] = resumen['%_estado_-1'].cumsum()
    resumen['%_acumulado'] = resumen['%_estado'].cumsum()

    # --- Mapa ---
    mapa = graficar_clusters_dbscan_folium(df, ciudades_ref, state=state)

    return mapa, resumen

def distancias_intra_cluster(df):
    puntos = list(zip(df['lat'], df['lng']))
    dists = []
    
    for i in range(len(puntos)):
        for j in range(i + 1, len(puntos)):
            #print(puntos[i])
            #print(puntos[j])
            d = haversine(puntos[i][0], puntos[i][1], puntos[j][0], puntos[j][1]) # haversine(puntos[i], puntos[j], unit=Unit.MILES)
            #print(d)
            dists.append(d)
        
    return pd.Series([
            np.min(dists),
            np.percentile(dists, 25),
            np.mean(dists),
            np.percentile(dists, 50),
            np.percentile(dists, 75),
            np.max(dists)
            ], index=['dist_min', 'dist_q1', 'dist_mean', 'dist_q2', 'dist_q3', 'dist_max'])

def coordenadas(test, state):
    origins = (
        test.loc[test['StateOrigin'] == state, 
                 ['LatOrigin', 'LngOrigin', 'CityOrigin']]
        .rename(columns={'LatOrigin': 'lat', 'LngOrigin': 'lng', 'CityOrigin': 'city'})
    )
    origins['cargas_out'] = 1
    
    destinations = (
        test.loc[test['StateDestination'] == state, 
                 ['LatDestination', 'LngDestination', 'CityDestination']]
        .rename(columns={'LatDestination': 'lat', 'LngDestination': 'lng', 'CityDestination': 'city'})
    )
    destinations['cargas_in'] = 1
    
    coords = pd.concat([origins, destinations], ignore_index=True)
    coords = coords.groupby(['lat','lng'], as_index=False).sum(numeric_only=True)
    coords['cargas'] = coords['cargas_out'] + coords['cargas_in']
    return coords

cols = ['ID', 'Posted',
 'PickUp', 'CityOrigin', 'CityDestination',
 'Distance', 'Equip', 'StateOrigin', 'HubOrigin',
 'StateDestination', 'HubDestination', 'Broker_Shipper', 'RatePerMile',
 'LatOrigin', 'LngOrigin', 'LatDestination', 'LngDestination']

def cargasinout(df, state, cols=None):
    test = df.copy()
    
    # Filtrar cargas donde el estado es origen o destino
    mask = (test['StateOrigin'] == state) | (test['StateDestination'] == state)
    df = test.loc[mask].copy()
    
    # Inicializar columnas
    df['load_in'] = 0
    df['load_out'] = 0
    df['intrastate'] = 0
    
    # Clasificación
    df.loc[df['StateOrigin'] == state, 'load_out'] = 1

    #print(df.loc[df['StateOrigin'] == state].shape)
    df.loc[df['StateDestination'] == state, 'load_in'] = 1
    #print(df.loc[df['StateDestination'] == state].shape)
    
    # Intrastate: mismo origen y destino
    mask_intra = (df['StateOrigin'] == state) & (df['StateDestination'] == state)
    df.loc[mask_intra, ['load_in', 'load_out']] = 0
    df.loc[mask_intra, 'intrastate'] = 1

    #print(df.loc[mask_intra].shape)
    
    # Añadir regiones
    df = df.merge(
        states[['state', 'region']], 
        left_on='StateOrigin', 
        right_on='state', 
        how='left'
    ).drop(columns='state').rename(columns={'region': 'RegionOrigin'})
    
    df = df.merge(
        states[['state', 'region']], 
        left_on='StateDestination', 
        right_on='state', 
        how='left'
    ).drop(columns='state').rename(columns={'region': 'RegionDestination'})
    
    return df

def haversine(lat1, lon1, lat2, lon2):
    """Calculate the Haversine distance between two points on the Earth."""
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    distance = 3958.8 * c  # Radius of the Earth in miles
    return distance

def graficar_clusters_dbscan_folium(coords, ciudades_importantes, state=None):
    # Filtrar solo clusters válidos (DBSCAN asigna -1 al ruido)
    coords = coords.reset_index(drop=True)
    unique_clusters = sorted(coords['cluster'].unique())
    ncluster = len([c for c in unique_clusters if c != -1])

    # Centro del mapa
    center_lat = coords['lat'].mean()
    center_lng = coords['lng'].mean()
    m = folium.Map(location=[center_lat, center_lng], zoom_start=6, tiles="CartoDB positron")

    #for _, row in hubs.loc[hubs['state'] == state].iterrows():
     #   folium.Circle(
      #      location=[row['lat'], row['lng']],
       #     radius=50 * 1609.34,
        #    color='gray',
         #   fill=True,
          #  fill_opacity=0.3,
           # popup=f"Hub ({row['lat']:.2f}, {row['lng']:.2f})"
        #).add_to(m)
    
    norm = colors.Normalize(vmin=0, vmax=ncluster - 1)
    colormap = plt.colormaps.get_cmap('viridis')
    #cluster_color = colors.rgb2hex(colormap(norm(row['cluster'])))

    # Dibujar círculos solo para puntos que NO son ruido
    for _, row in coords.iterrows():
        if row['cluster'] == -1:
            continue  # Saltar ruido
        
        cluster_color = colors.rgb2hex(colormap(norm(row['cluster'])))
        folium.CircleMarker(
            location=[row['lat'], row['lng']],
            radius=4,
            color=cluster_color,
            fill=True,
            fill_opacity=0.8,
            popup=f"Lat: {row['lat']}, Lng: {row['lng']}, loads: {row['cargas']}, cluster: {row['cluster']}"
        ).add_to(m)

    # Ciudades importantes
    for _, row in ciudades_importantes.iterrows():
        folium.Marker(
            location=[row['lat'], row['lng']],
            popup=f"{row['city']}",
            icon=folium.Icon(color='yellow', icon='info-sign')
        ).add_to(m)

    # Puntos con muchas cargas (que no sean ruido)
    #coords_cargas_altas = coords[(coords['cargas'] > 100) & (coords['cluster'] != -1)]
    #for _, row in coords_cargas_altas.iterrows():
     #   folium.CircleMarker(
      #      location=[row['lat'], row['lng']],
       #     radius=4,
        #    color='black',
         #   fill=True,
          #  fill_color='black',
           # fill_opacity=0.7,
            #popup=f"Lat: {row['lat']}, Lng: {row['lng']}, city: {row['city']}, loads: {row['cargas']}"
        #).add_to(m)

    # Título
    title_html = f'''
        <div style="position: fixed; 
                    top: 10px; left: 10px; width: 300px; height: 40px; 
                    background-color: white;
                    z-index:9999; font-size:14px;
                    padding: 8px; border: 1px solid gray;">
            <b>Clusters con DBSCAN</b><br>
            Clusters encontrados: {ncluster} &nbsp;&nbsp;|&nbsp;&nbsp; Ruido: {(coords['cluster'] == -1).sum()}
        </div>
    '''
    m.get_root().html.add_child(folium.Element(title_html))

    return m

hubs = pd.read_excel('../utils/hubs_id.xlsx')
states = hubs.drop_duplicates(subset='state')

def sugerir_eps(X_scaled, k=5, show_plot=True):
    """
    Calcula el valor sugerido de eps para DBSCAN usando la gráfica de k-distancias.

    Args:
        X_scaled (array): Datos escalados (por ejemplo, con StandardScaler).
        k (int): Número de vecinos (usualmente min_samples).
        show_plot (bool): Si se quiere mostrar el gráfico del codo.

    Returns:
        eps_sugerido (float): Valor aproximado de eps basado en el codo.
    """
    neigh = NearestNeighbors(n_neighbors=k)
    nbrs = neigh.fit(X_scaled)
    distances, indices = nbrs.kneighbors(X_scaled)

    # Usamos la distancia al k-ésimo vecino
    k_dist = np.sort(distances[:, k - 1])

    if show_plot:
        plt.figure(figsize=(8, 4))
        plt.plot(k_dist)
        plt.xlabel("Puntos ordenados")
        plt.ylabel(f"Distancia al {k}° vecino más cercano")
        plt.title("Gráfica de k-distancias para DBSCAN")
        plt.grid()
        plt.show()

    return k_dist

def analizar_clusters(coords, loads, state=None):

    # -----------------------------
    # Preprocesamiento
    # -----------------------------
    bins = [0, 300, 600, 1000, float("inf")]
    labels = ["<300", "300-600", "600-1000", ">1000"]

    #print('asi me llamo en analizar clusters',coords['cluster'].unique())

    #loads = loads[(loads['cluster_origin'].notna()) & (loads['cluster_destination'].notna())].copy()
    loads = loads[(loads['cluster_origin'] != -1) & (loads['cluster_destination'] != -1)].copy()
    loads["DistanciaCat"] = pd.cut(loads["Distance"], bins=bins, labels=labels, right=False)
    loads["cluster_origin"] = pd.to_numeric(loads["cluster_origin"], errors="coerce").astype("Int64")
    loads["cluster_destination"] = pd.to_numeric(loads["cluster_destination"], errors="coerce").astype("Int64")

    #print('asi me llamo en analizar clusters loads',loads['cluster_origin'].unique())
    #print('asi me llamo en analizar clusters loads',loads['cluster_destination'].unique())
    
    # -----------------------------
    # Resultados comportamiento en cuanto a número de cargas
    # -----------------------------
    
    out_counts = (
        loads.groupby(["DistanciaCat", "cluster_origin"])
        .size()
        .unstack("cluster_origin")
        .fillna(0)
        .astype(int)
    )
    in_counts = (
        loads.groupby(["DistanciaCat", "cluster_destination"])
        .size()
        .unstack("cluster_destination")
        .fillna(0)
        .astype(int)
    )
    
    filas = []
    for cat in labels:
        filas.append(in_counts.loc[cat].rename(f"load_in {cat}"))
        filas.append(out_counts.loc[cat].rename(f"load_out {cat}"))

    resultado = pd.DataFrame(filas)

    resultado.loc["total_cargas"] = resultado.sum().astype(int)
    resultado.loc["total_cargas_in"] = resultado.filter(like="load_in", axis=0).sum().astype(int)
    resultado.loc["total_cargas_out"] = resultado.filter(like="load_out", axis=0).sum().astype(int)

    for cat in labels:
        filas_cat = [f"load_in {cat}", f"load_out {cat}"]
        resultado.loc[f"total_cargas {cat}"] = resultado.loc[filas_cat].sum().astype(int)

    total = resultado.loc['total_cargas'].sum()
    totales = resultado.loc['total_cargas']

    resultado.loc["% total_cargas"] = (resultado.loc["total_cargas"] / total * 100).round(2)
    resultado.loc['ratio_in_out'] = (resultado.loc["total_cargas_in"] / resultado.loc["total_cargas_out"]).round(2)
    resultado.loc["% total_cargas_in"] = (resultado.loc["total_cargas_in"] / totales * 100).round(2)
    resultado.loc["% total_cargas_out"] = (resultado.loc["total_cargas_out"] / totales * 100).round(2)

    for cat in labels:
        resultado.loc[f"% total_cargas {cat}"] = (resultado.loc[f"total_cargas {cat}"] / totales * 100).round(2)

    cargas_res = resultado.copy()

    # -----------------------------
    # Resultados comportamiento en cuanto a rpm in/out
    # -----------------------------
    rpm_in = loads.groupby("cluster_destination")["RatePerMile"].median().rename("rpm_in_q2")
    rpm_out = loads.groupby("cluster_origin")["RatePerMile"].median().rename("rpm_out_q2")

    rpm = pd.concat([rpm_in, rpm_out], axis=1)
    rpm["ratio_in_out_q2"] = rpm["rpm_in_q2"] / rpm["rpm_out_q2"]

    resultados = []
    for r in labels:
        subset = loads[loads["DistanciaCat"] == r]

        rpm_in = subset.groupby("cluster_destination")["RatePerMile"].median().rename(f"rpm_in_q2_{r}")
        rpm_out = subset.groupby("cluster_origin")["RatePerMile"].median().rename(f"rpm_out_q2_{r}")

        c_in = subset.groupby("cluster_destination")["RatePerMile"].count().rename(f"cargas_in_{r}")
        c_out = subset.groupby("cluster_origin")["RatePerMile"].count().rename(f"cargas_out_{r}")

        df = pd.concat([rpm_in, rpm_out, c_in, c_out], axis=1)
        df[f"ratio_in_out_q2_{r}"] = df[f"rpm_in_q2_{r}"] / df[f"rpm_out_q2_{r}"]

        resultados.append(df)

    rpm_res = pd.concat([rpm] + resultados, axis=1)

    # -----------------------------
    # Distancias intra-cluster
    # -----------------------------
    def distancias_intra_cluster_general(df):
        puntos = list(zip(df['lat'], df['lng']))
        dists = []
        for i in range(len(puntos)):
            for j in range(i + 1, len(puntos)):
                d = haversine(puntos[i][0], puntos[i][1], puntos[j][0], puntos[j][1])
                dists.append(d)
        return pd.Series([
            np.min(dists),
            np.percentile(dists, 25),
            np.mean(dists),
            np.percentile(dists, 50),
            np.percentile(dists, 75),
            np.max(dists)
        ], index=['dist_min', 'dist_q1', 'dist_mean', 'dist_q2', 'dist_q3', 'dist_max'])

    coords = coords[coords['cluster']!=-1].copy()
    #print('asi me llamo en analizar clusters',coords['cluster'].unique())
    #d1 = coords.groupby('cluster').apply(distancias_intra_cluster_general).reset_index(drop = True).T
    d2 = coords.groupby('cluster').apply(distancias_centroide_cluster).T
    d_res = d2 #pd.concat([d1, d2])

    # -----------------------------
    # Conectividad
    # -----------------------------
    loads['city_o'] = loads['CityOrigin'].str.lower() + ',' + loads['StateOrigin'].str.lower()
    loads['city_d'] = loads['CityDestination'].str.lower() + ',' + loads['StateDestination'].str.lower()

    # hubs_out = cuántos destinos únicos tiene cada cluster como origen
    hout = loads.groupby("cluster_origin")['city_d'].nunique().rename("hubs_out")
    # hubs_in = cuántos orígenes únicos tiene cada cluster como destino
    hin = loads.groupby("cluster_destination")['city_o'].nunique().rename("hubs_in")

    # distribuciones de distancia
    qin1 = loads.groupby("cluster_destination")['Distance'].quantile(0.25).rename("dist_in_q1")
    qin2 = loads.groupby("cluster_destination")['Distance'].quantile(0.5).rename("dist_in_q2")
    qin3 = loads.groupby("cluster_destination")['Distance'].quantile(0.75).rename("dist_in_q3")

    qout1 = loads.groupby("cluster_origin")['Distance'].quantile(0.25).rename("dist_out_q1")
    qout2 = loads.groupby("cluster_origin")['Distance'].quantile(0.5).rename("dist_out_q2")
    qout3 = loads.groupby("cluster_origin")['Distance'].quantile(0.75).rename("dist_out_q3")

    conn = pd.concat([hout, hin, qin1, qin2, qin3, qout1, qout2, qout3], axis=1).T

    # -----------------------------
    # Retornar todos los resultados
    # -----------------------------
    return {
        "cargas": cargas_res,
        "rpm": rpm_res,
        "distancia": d_res,
        "conn": conn
    }

def plot_cargas_semanales(loads, tipo="in"):
    """
    Genera visualizaciones semanales de cargas por cluster.

    Parámetros
    ----------
    loads : pd.DataFrame
        DataFrame con columnas: Posted, load_in, load_out, cluster_origin, cluster_destination.
    tipo : str
        Tipo de gráfico:
        - "in"      : línea con % inbound por cluster (cluster_destination)
        - "out"     : línea con % outbound por cluster (cluster_origin)
        - "ratio"   : línea con ratio in/out por cluster
        - "stacked" : barras apiladas con total de cargas por cluster

    Retorna
    -------
    fig : plotly.graph_objects.Figure
    """

    # ==============================
    # Preprocesamiento
    # ==============================
    loads["Posted"] = pd.to_datetime(loads["Posted"])
    df = loads[(loads["cluster_origin"] != -1) & (loads["cluster_destination"] != -1)].copy()

    # ==============================
    # Agregaciones semanales
    # ==============================
    semanal_in = (
        df.groupby([pd.Grouper(key="Posted", freq="W"), "cluster_destination"])
          .agg(cargas_in=("load_in", "sum"))
          .reset_index()
          .rename(columns={"cluster_destination": "cluster"})
    )

    semanal_out = (
        df.groupby([pd.Grouper(key="Posted", freq="W"), "cluster_origin"])
          .agg(cargas_out=("load_out", "sum"))
          .reset_index()
          .rename(columns={"cluster_origin": "cluster"})
    )

    # merge para ratio y stacked
    semanal = pd.merge(
        semanal_in, semanal_out, on=["Posted", "cluster"], how="outer"
    ).fillna(0)

    # totales semanales
    totales_in = semanal.groupby("Posted")["cargas_in"].transform("sum")
    totales_out = semanal.groupby("Posted")["cargas_out"].transform("sum")
    
    semanal["pct_in"] = (semanal["cargas_in"] / totales_in * 100).round(2)
    semanal["pct_out"] = (semanal["cargas_out"] / totales_out * 100).round(2)
    semanal["ratio_in_out"] = (
        (semanal["cargas_in"]) / (semanal["cargas_out"].replace(0, pd.NA))
    )
    semanal["total_cargas"] = semanal["cargas_in"] + semanal["cargas_out"]

    # ==============================
    # Visualizaciones
    # ==============================
    if tipo == "in":
        fig = px.line(
            semanal, x="Posted", y="pct_in", color="cluster",
            title="Inbound loads (% del total semanal) por cluster (destino)"
        )

    elif tipo == "out":
        fig = px.line(
            semanal, x="Posted", y="pct_out", color="cluster",
            title="Outbound loads (% del total semanal) por cluster (origen)"
        )

    elif tipo == "ratio":
        fig = px.line(
            semanal, x="Posted", y="ratio_in_out", color="cluster",
            title="Ratio IN/OUT semanal por cluster"
        )
        fig.update_yaxes(range=[0, 2])

    elif tipo == "stacked":
        fig = px.bar(
            semanal, x="Posted", y="total_cargas", color="cluster",
            title="Cargas semanales totales apiladas por cluster",
            barmode="stack"
        )

    else:
        raise ValueError("El parámetro 'tipo' debe ser 'in', 'out', 'ratio' o 'stacked'")

    return semanal, fig

def preparar_clusters(loads, periodo="W"):
    # asegurar fecha
    loads["Posted"] = pd.to_datetime(loads["Posted"])
    loads = loads[(loads["cluster_origin"] != -1) & (loads["cluster_destination"] != -1)].copy()

    # ============================
    # 1. Sacar centroides por cluster (coordenadas medias del origen)
    # ============================
    centroides = (
        loads.groupby("cluster_origin")[["LatOrigin", "LngOrigin"]]
        .mean()
        .reset_index()
        .rename(columns={"cluster_origin": "cluster", "LatOrigin": "Lat", "LngOrigin": "Lng"})
    )

    # ============================
    # 2. Calcular métricas por cluster y periodo
    # ============================
    loads[periodo] = loads["Posted"].dt.to_period(periodo).dt.start_time

    # inbound (por destino)
    metrics_in = (
        loads.groupby([periodo, "cluster_destination"])
        .agg(
            cargas_in=("load_in", "sum"),
            rpm_in=("RatePerMile", "median"),
        )
        .reset_index()
        .rename(columns={"cluster_destination": "cluster"})
    )

    # outbound (por origen)
    metrics_out = (
        loads.groupby([periodo, "cluster_origin"])
        .agg(
            cargas_out=("load_out", "sum"),
            rpm_out=("RatePerMile", "median"),
        )
        .reset_index()
        .rename(columns={"cluster_origin": "cluster"})
    )

    # combinar
    metrics = pd.merge(metrics_in, metrics_out, on=[periodo, "cluster"], how="outer").fillna(0)

    # cálculos adicionales
    metrics["total_cargas"] = metrics["cargas_in"] + metrics["cargas_out"]
    metrics["ratio_in_out"] = metrics["cargas_in"] / metrics["cargas_out"].replace(0, pd.NA)

    totals = metrics.groupby(periodo)["total_cargas"].transform("sum")
    metrics["pct_cargas"] = (metrics["total_cargas"] / totals * 100).round(2)

    # ============================
    # 3. Merge con centroides
    # ============================
    clusters = metrics.merge(centroides, on="cluster", how="left")

    return clusters


def plot_clusters_map(loads, periodo="W"):
    clusters = preparar_clusters(loads, periodo=periodo)

    fig = px.scatter_mapbox(
        clusters,
        lat="Lat",
        lon="Lng",
        color="pct_cargas",
        color_continuous_scale="Reds",
        hover_data={
            "cluster": True,
            "cargas_in": True,
            "cargas_out": True,
            "ratio_in_out": True,
            "rpm_in": True,
            "rpm_out": True,
            "pct_cargas": True,
        },
        animation_frame=periodo,
        zoom=4,
        mapbox_style="carto-positron",
        title=f"Mapa dinámico de clusters por {periodo}"
    )

    fig.update_traces(marker=dict(size=15))
    fig.update_layout(width=1000, height=700)

    return clusters, fig

def merge_clusters(loads,coords):
    # ================================
    # 1. Asignar coordenadas temporales para clustering
    # ================================
    loads['lat_origin'] = loads['LatOrigin']
    loads['lng_origin'] = loads['LngOrigin']
    
    loads['lat_dest'] = loads['LatDestination']
    loads['lng_dest'] = loads['LngDestination']
    
    # ================================
    # 2. Hacer el merge dos veces: origen y destino
    # ================================
    loads = loads.merge(
        coords[['lat','lng','cluster']],
        left_on=['lat_origin','lng_origin'],
        right_on=['lat','lng'],
        how='left'
    ).rename(columns={'cluster':'cluster_origin'}).drop(columns=['lat','lng'])
    
    loads = loads.merge(
        coords[['lat','lng','cluster']],
        left_on=['lat_dest','lng_dest'],
        right_on=['lat','lng'],
        how='left'
    ).rename(columns={'cluster':'cluster_destination'}).drop(columns=['lat','lng'])
    
    loads = loads.reset_index(drop = True)
    loads.shape
    
    mask = loads['Distance'].isna()
    loads.loc[mask, 'Distance'] = loads.loc[mask].apply(lambda row: haversine(row['LatOrigin'], row['LngOrigin'], row['LatDestination'], row['LngDestination']),axis=1)

    #display(coords['cluster'].unique())
    
    return loads

def aplicardbscan(ciudades, coords, state, min_samples = 20):
    x = StandardScaler().fit_transform(coords[['lat','lng','cargas']])
    
    k_dist = sugerir_eps(x, k=5, show_plot=False)
    eps_sugerido = np.percentile(k_dist, 90)  # o 95, según el comportamiento
    print(f"Eps sugerido (percentil 90): {eps_sugerido:.4f}")
    
    eps = eps_sugerido     # esto depende mucho de tus datos
    db = DBSCAN(eps=eps, min_samples=min_samples)
    coords['cluster'] = db.fit_predict(x)
    
    mapa, resumen = generar_resultado(coords, ciudades,  state = state)
    return coords, mapa

def df_prueba(df, loads, coords, ciudades, state, qt):
    loads = merge_clusters(loads, coords)
    clusters = preparar_clusters(loads, periodo='W')
    
    resultados = []
    
    for week in clusters['W'].unique():
        t = clusters.loc[clusters['W'] == week]
        t = t.sort_values('pct_cargas', ascending=False)[['cluster', 'pct_cargas']]
        t = t.head(10)
        resultados.extend(t['cluster'].tolist())
    
    conteo = pd.Series(resultados).value_counts().reset_index()
    conteo.columns = ['cluster', 'conteo']
    
    top_clusters = conteo[conteo['conteo']>conteo['conteo'].quantile(qt)]['cluster'].tolist()
    
    coords = coords[coords['cluster'].isin(top_clusters)].reset_index(drop=True).copy()
    menos1 = coords.loc[coords['cluster']==-1].reset_index(drop=True)
    resto = coords.loc[coords['cluster']!=-1].reset_index(drop=True)
    cluster_mapping = {old: i+1 for i, old in enumerate(top_clusters)}
    #print(cluster_mapping)
    
    resto['cluster'] = resto['cluster'].map(cluster_mapping)
    coords = pd.concat([resto,menos1])

    return coords

def generar_subregiones(df, loads, coords, ciudades, state, qt):
    coords = df_prueba(df, loads, coords, ciudades, state, qt)
    mapa, resumen = generar_resultado(coords, ciudades,  state = state)
    #display(resumen)
    #display(mapa)
    
    loads = cargasinout(df,state,cols)
    loads = merge_clusters(loads, coords)
    
    res = analizar_clusters(coords, loads, state="MT")
    clusters, fig = plot_clusters_map(loads, periodo = 'W')
    loads = loads[loads['Posted']>'2024-12-01'].reset_index(drop = True)
    g, fig1 = plot_cargas_semanales(loads, tipo="in")
    g, fig2 = plot_cargas_semanales(loads, tipo="out")
    g, fig3 = plot_cargas_semanales(loads, tipo="ratio")
    g, fig4 = plot_cargas_semanales(loads, tipo="stacked")

    return res, fig, fig1, fig2, fig3, fig3, coords

from sklearn.preprocessing import StandardScaler
from sklearn.cluster import AgglomerativeClustering

def aplicarjerarquico(ciudades, coords, state, distance_threshold=5.0, linkage="ward"):
    x = StandardScaler().fit_transform(coords[['lat','lng','cargas']])

    model = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=distance_threshold,
        linkage=linkage
    )
    coords['cluster'] = model.fit_predict(x)

    mapa, resumen = generar_resultado(coords, ciudades, state=state)
    return coords, mapa
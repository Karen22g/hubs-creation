import numpy as np
import pandas as pd
from math import radians, sin, cos, sqrt, atan2
import math
import os
import csv
import constants as C

def hub_assignment(df, cities_full, hubs_coords_file):
    print('Cantidad de ciudades inicial:', df.shape[0])

    cities_unr = df[['city', 'state', 'lat', 'lng']].copy()
    cities_unr = cities_unr.rename(
        {
            "state": "state_id",
        },
        axis=1,
    )

    cities_unr = cities_unr.dropna(subset=["lat"])
    print('Cantidad de ciudades a procesar:', cities_unr.shape[0])

    cities_unr = cities_unr.drop_duplicates(subset=["lat", "lng"]).reset_index(drop=True)
    print('Cantidad de ciudades a procesar borrando duplicados:', cities_unr.shape[0])

    display(cities_unr.head())

    # Step 5: Process hubs (aquí definimos el radio, ej: 50)
    dist_list = [50, 100, 150]
    cities_hubs, hubs_coords = process_hubs(
        cities_unr, cities_full, hubs_coords_file, dist_list=dist_list
    )
    cities_hubs.to_csv('hubs_assign.csv', index=False, float_format='%.10f')

    # Step 6: Add new hub names to the cities_hubs DataFrame
    cities_hubs['near_hub'] = cities_hubs['near_hub'].astype(float).astype(int)
    hubs_coords['id'] = hubs_coords['id'].astype(float).astype(int)

    cities_hubs = pd.merge(
        cities_hubs,
        hubs_coords[["id", "new_name"]],
        left_on=["near_hub"],
        right_on=["id"],
        how="left",
    )

    cities_hubs = cities_hubs.drop_duplicates(subset=["lat", "lng"]).reset_index(drop=True)

    # Step 7: Merge de resultados de vuelta al DataFrame original
    # Construimos dinámicamente la lista de columnas de radios a traer
    radio_cols = [f"hubs_{dist}m" for dist in dist_list]
    cols_to_merge = ["lat", "lng", "new_name"] + radio_cols

    df = pd.merge(
        df,
        cities_hubs[cols_to_merge],
        left_on=['lat', 'lng'],
        right_on=["lat", "lng"],
        how="left",
    )

    display(df.head())

    # Renombramos 'new_name' a 'near_hub' (el más cercano absoluto)
    df = df.rename(columns={
        "new_name": "near_hub"
    })

    # Step 8: Return final DataFrame
    return df

def process_hubs(cities_df, cities_full_df, hubs_coords_file, dist_list):
    """Process and find the nearest hubs for each city in the DataFrame."""
    cities_unr = (
        pd.concat([cities_full_df, cities_df])
        .drop_duplicates(subset=["city", "state_id", "lat", "lng"], keep="first")
        .copy()
    )

    cities_unr = cities_unr.query("near_hub.isna()")

    print('voy a procesar estas ciudades', len(cities_unr))
    print("se guardaron los cambios2")

    hubs_coords = pd.read_excel(hubs_coords_file, dtype={"id": str})

    if len(cities_unr) > 0:
        for dist in dist_list:
            cities_unr = (
                cities_unr.copy()
            )

            result = cities_unr.apply(
                    lambda x: get_array_hubs(hubs_coords, x["lat"], x["lng"], dist),
                    axis=1
                )

            cities_unr[f"hubs_{dist}m"] = result.apply(lambda x: x[0])
            cities_unr["near_hub"] = result.apply(lambda x: x[1])

    # keep="last": la versión recién calculada (cities_unr) gana sobre entradas
    # del caché (cities_full_df) que pudieran tener near_hub=NaN de corridas anteriores
    cities_hubs = (
        pd.concat([cities_full_df, cities_unr])
        .drop_duplicates(subset=["city", "state_id", "lat", "lng"], keep="last")
        .copy()
    )

    return cities_hubs, hubs_coords

def get_array_hubs(hubs_coords, lat, lng, dist):
    """Find nearby hubs within a given distance."""
    hubs_coords = hubs_coords.copy()

    hubs_coords["latc"] = lat
    hubs_coords["lngc"] = lng

    hubs_coords["distance"] = hubs_coords.apply(
        lambda x: haversine(x["lat"], x["lng"], x["latc"], x["lngc"]),
        axis=1,
    )

    # 1. El hub más cercano absoluto (independientemente de la distancia)
    nhub = hubs_coords.iloc[hubs_coords["distance"].idxmin()]["id"]

    # 2. El grupo de hubs que caen ESTRICTAMENTE dentro del radio
    list_nhub = list(hubs_coords.query("distance <= @dist")["id"])

    return list_nhub, nhub


def haversine(lat1, lon1, lat2, lon2):
    """Calculate the Haversine distance between two points on the Earth."""
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    distance = 3958.8 * c  # Radius of the Earth in miles
    return distance

def calculate_distance(origin, destination):
    # Radio de la Tierra en millas
    R = 3958.8
    # Convertir coordenadas de grados a radianes
    lat1, lon1 = math.radians(origin[0]), math.radians(origin[1])
    lat2, lon2 = math.radians(destination[0]), math.radians(destination[1])
    # Diferencias de latitud y longitud
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    # Fórmula de haversine
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    distancia = R * c * 1.17
    return distancia

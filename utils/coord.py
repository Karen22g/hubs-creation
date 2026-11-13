import numpy as np
import pandas as pd
import math
from math import radians, sin, cos, sqrt, atan2
import os
import csv
import constants as C
import swifter
import requests

_uscities_df = pd.read_csv(os.path.join(os.path.dirname(__file__), "uscities.csv"))
_uscities_df['city_key']  = _uscities_df['city'].str.lower().str.strip()
_uscities_df['state_key'] = _uscities_df['state_id'].str.lower().str.strip()
_uscities_index = _uscities_df.set_index(['city_key', 'state_key'])

def add_location_to_csv(location: dict, csv_path: str):
    if not location.get("lat") or not location.get("lng"):
        return
    new_row = pd.DataFrame([{
        "city":         location.get("city", ""),
        "city_ascii":   location.get("city_ascii", ""),
        "state_id":     location.get("state_id", ""),
        "state_name":   location.get("state_name", ""),
        "county_fips":  location.get("county_fips", ""),
        "county_name":  location.get("county_name", ""),
        "lat":          location.get("lat", 0),
        "lng":          location.get("lng", 0),
        "population":   location.get("population", ""),
        "density":      location.get("density", ""),
        "source":       location.get("source", ""),
        "military":     location.get("military", False),
        "incorporated": location.get("incorporated", False),
        "timezone":     location.get("timezone", ""),
        "ranking":      location.get("ranking", ""),
        "zips":         location.get("zips", ""),
        "id":           location.get("id", ""),
    }])
    new_row.to_csv(csv_path, mode='a', header=False, index=False)
    # actualizar el df en memoria para que búsquedas siguientes lo encuentren
    new_row['city_key']  = new_row['city'].str.lower().str.strip()
    new_row['state_key'] = new_row['state_id'].str.lower().str.strip()
    global _uscities_df, _uscities_index
    _uscities_df = pd.concat([_uscities_df, new_row], ignore_index=True)
    _uscities_index = _uscities_df.set_index(['city_key', 'state_key'])


def get_coordinates_from_csv(city_name: str, state_id: str):
    try:
        city_key  = city_name.lower().split(",")[0].strip()
        state_key = str(state_id).lower().strip() if pd.notna(state_id) and state_id != '' else None

        if state_key and (city_key, state_key) in _uscities_index.index:
            row = _uscities_index.loc[(city_key, state_key)]
            # puede haber más de una fila con mismo city+state
            if isinstance(row, pd.DataFrame):
                row = row.iloc[0]
            return float(row['lat']), float(row['lng'])

        # sin estado: buscar solo por ciudad
        matches = _uscities_df[_uscities_df['city_key'] == city_key]
        if not matches.empty:
            return float(matches.iloc[0]['lat']), float(matches.iloc[0]['lng'])

        # fallback geoapify (sin credenciales nunca llega aquí)
        location = get_coordinates(city_name, state_id)
        add_location_to_csv(location, os.path.join(os.path.dirname(__file__), "uscities.csv"))
        return float(location["lat"]), float(location["lng"])

    except FileNotFoundError:
        print("Error: El archivo no se encontró.")
        return None, None
    except Exception as e:
        print(f"Error: {e}")
        return None, None

def process_row(row):

    lat, lng = get_coordinates_from_csv(
        row.get('city', ''),
        row.get('state', '')
    )

    row['lat'] = lat
    row['lng'] = lng

    return row

def get_coordinates(city_name: str, state_name: str) -> dict:
    try:
        # Cargar la API Key desde las variables de entorno
        API_KEY = os.getenv("GEOAPIFY_API_KEY")
        if not API_KEY:
            raise ValueError(
                "La API Key no está configurada en las variables de entorno."
            )

        # Concatenar ciudad y estado
        location = f"{city_name}, {state_name}"

        url = (
            f"https://api.geoapify.com/v1/geocode/autocomplete?"
            f"text={requests.utils.quote(location)}&"
            f"limit=5&"
            f"lang=en&"
            f"filter=countrycode:us&"
            f"apiKey={API_KEY}&"
            f"type=city"
        )
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        if data.get("features") and len(data["features"]) > 0:
            properties = data["features"][0].get("properties", {})
            return {
                "city": properties.get("city", ""),
                "city_ascii": properties.get("city", ""),
                "city_name_original": city_name,
                "state_id": properties.get("state_code", ""),
                "state_name": properties.get("state", ""),
                "county_fips": "",
                "county_name": properties.get("city", ""),
                "lat": properties.get("lat", 0),
                "lng": properties.get("lon", 0),
                "population": "",
                "density": "",
                "source": "geoapify",
                "hamlet": properties.get("hamlet", ""),
                "military": False,
                "incorporated": True,
                "timezone": properties.get("timezone", ""),
                "ranking": "1",
                "zips": "",
                "id": properties.get("place_id", ""),
            }
        else :
            return {
                "city": "",
                "city_ascii": "",
                "city_name_original": "",
                "state_id": "",
                "state_name": "",
                "county_fips": "",
                "county_name": "",
                "lat": 0,
                "lng": 0,
                "population": "",
                "density": "",
                "source": "",
                "hamlet": "",
                "military": False,
                "incorporated": False,
                "timezone": "",
                "ranking": "",
                "zips": "",
                "id": "",
            }

            
    except Exception as e:
        print(f"Error: {e}")
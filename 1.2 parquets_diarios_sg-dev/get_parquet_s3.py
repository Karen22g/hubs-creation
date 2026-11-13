from dotenv import load_dotenv
import os
import boto3
import constants as C
from utils import initialize_boto3
from datetime import datetime, timezone, timedelta
import re

load_dotenv()

def ensure_folder_exists(folder):
    try:
        if not os.path.exists(folder):
            os.makedirs(folder)
            print(f"Directorio '{folder}' creado exitosamente.")
        else:
            print(f"El directorio '{folder}' ya existe.")
    except Exception as e:
        print(f"Error al crear el directorio '{folder}': {e}")

def download_parquets_s3():

    s3_resource, s3, s3_bucket_name = initialize_boto3(0)
    s3_bucket_name = "efrouting-dev-scraping"
    scrap = "GENERAL" # if enviroment == 0 else "ONDEMAND"
    temp_dir = f'loads_history/{scrap}'
   
    ensure_folder_exists(temp_dir)
    ldbds = ['TQL']

    for ldbd in ldbds:
    
        prefix = f"generalScrap/{ldbd}/processing/output/tql/processed/"
        
        objs = list(s3_resource.Bucket(s3_bucket_name).objects.filter(Prefix=prefix))
        if not objs:
            print(f"No se encontraron objetos en el prefijo: {prefix}")
            continue

        parquet_objs = [obj for obj in objs if obj.key.endswith(f".parquet")]

        if not parquet_objs:
            print(f"No se encontraron archivos .parquet para {ldbd}")
            continue

        #la fecha mínima de info es el 27 enero
        utc_minus_5 = timezone(timedelta(hours=-5))
        target_date = datetime(2025, 1, 28).astimezone(utc_minus_5).date()
        parquet_objs_filtered = [obj for obj in parquet_objs if obj.last_modified.date() <= target_date]

        # Expresión regular para extraer la fecha del nombre del archivo
        pattern = re.compile(r"tql_(\d{2})-(\d{2})-(\d{4})")

        # Filtrar archivos según la fecha en el nombre
        parquet_objs_filtered = []
        for obj in parquet_objs:
            match = pattern.search(obj.key)
            if match:
                day, month, year = map(int, match.groups())
                file_date = datetime(year, month, day).date()
                if file_date < target_date:
                    parquet_objs_filtered.append(obj)

        if not parquet_objs_filtered:
            print(f"No se encontraron archivos .parquet de {target_date} para {ldbd}")
            continue

        local_dir = f"{temp_dir}/{ldbd}"
        os.makedirs(local_dir, exist_ok=True)

        for obj in parquet_objs_filtered:
            filename = os.path.basename(obj.key)  # Extrae solo el nombre del archivo
            local_filename = os.path.join(local_dir, filename)  # Construye la ruta local
            os.makedirs(os.path.dirname(local_filename), exist_ok=True)  # Asegura que la carpeta exista
            s3.download_file(s3_bucket_name, obj.key, local_filename)
        
#def download_parquets():
 #   ldbds = C.loadboards_gs_aws
  #  download_parquets_s3(0, ldbds)
   # return True

download_parquets_s3()
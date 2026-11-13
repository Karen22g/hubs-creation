from dotenv import load_dotenv
import os
import boto3
import constants as C
from utils import initialize_boto3
from datetime import datetime, timezone, timedelta

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

def download_parquets_s3(enviroment, ldbds):
    s3_resource, s3, s3_bucket_name = initialize_boto3(0)
    s3_bucket_name = "efrouting-indicators"
    scrap = "GENERAL" if enviroment == 0 else "ONDEMAND"
    temp_dir = f'loads_history/{scrap}'
   
    ensure_folder_exists(temp_dir)

    # Rango de fechas en que se realizó el análisis de los hubs, se puede dejar todo 2026
    #la fecha mínima de info es el 27 enero
    start_date = datetime(2025, 1, 27).date()
    end_date = datetime(2025, 8, 31).date()
    
    for ldbd in ldbds:
        
        print(f"\nProcesando loadboard: {ldbd}")
        
        prefix = f"processing/{ldbd}/output/{scrap}/"
        
        objs = list(s3_resource.Bucket(s3_bucket_name).objects.filter(Prefix=prefix))
        
        if not objs:
            print(f"No se encontraron objetos en el prefijo: {prefix}")
            continue

        parquet_objs = [obj for obj in objs if obj.key.endswith(f".parquet")]

        if not parquet_objs:
            print(f"No se encontraron archivos .parquet para {ldbd}")
            continue

        local_dir = os.path.join(temp_dir, ldbd)
        os.makedirs(local_dir, exist_ok=True)

        # Revisar los archivos que ya existen localmente
        existing_files = set(os.listdir(local_dir))

        downloaded = 0
        skipped = 0

        for obj in parquet_objs:

            # Convertir la fecha de S3 a la zona horaria UTC-5
            local_date = (
                obj.last_modified
                .astimezone(timezone(timedelta(hours=-5)))
                .date()
            )

            # Filtrar fechas entre el 29 de enero y el 31 de agosto
            if not (start_date <= local_date <= end_date):
                continue

            # Mantener el formato de nombre de archivo original
            filename = (
                f"{obj.last_modified.strftime('%Y-%m-%d_%H-%M-%S')}.parquet"
            )

            # No descargar si el archivo ya existe
            if filename in existing_files:
                skipped += 1
                continue

            local_filename = os.path.join(local_dir, filename)

            print(f"Descargando: {filename}")

            s3.download_file(
                s3_bucket_name,
                obj.key,
                local_filename
            )

            existing_files.add(filename)
            downloaded += 1

        print(
            f"{ldbd}: {downloaded} descargados, "
            f"{skipped} omitidos porque ya existían."
        )
        
def download_parquets():
    ldbds = C.loadboards_gs_aws
    print(ldbds)
    download_parquets_s3(1, ldbds)
    return True

#se debe correr con 0 y 1 para llenar los datos de cada tipo de scrap (general 0, ondemand 1)

download_parquets()
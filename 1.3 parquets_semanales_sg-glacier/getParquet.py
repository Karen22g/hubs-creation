from dotenv import load_dotenv
import os
import boto3
import constants as gc
from helpers import get_week_dates

# Configuración
temp_dir = './loads_history'

load_dotenv()

# Obtener las credenciales de AWS y el nombre del bucket desde el .env
bucket_name = "efrouting-dev-scraping"
bucket_name_glacier = "efrouting-archival-glacier"
session = boto3.Session(
    aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID", ""),
    aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY", "")
)

s3_resource = session.resource('s3')
s3 = session.client('s3')

def download_week():
    try:
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
            print(f"Directorio '{temp_dir}' creado exitosamente.")
        else:
            print(f"El directorio '{temp_dir}' ya existe.")
    except Exception as e:
        print(f"Error al crear el directorio '{temp_dir}': {e}")

    #prefixes = ["generalScrap/TSMARTER/processing/output","generalScrap/CHR/processing/output",
     #           "generalScrap/DAT/processing/output","generalScrap/DOFT/processing/output"]

    prefixes = ["generalScrap/CHR/processing/output"]
    
    wanted_files =  ['chr.parquet','tsmart.parquet', 'dat.parquet', 'doft.parquet']
    
    for prefix in prefixes:
    
        for obj in s3_resource.Bucket(bucket_name).objects.filter(Prefix=prefix):            
            local_filename = os.path.join(temp_dir, obj.key.split('/')[-1])
            
            file = obj.key.split('/')[-1]

            if file in wanted_files:
                    
                # Descarga el archivo .rar del bucket de S3
                s3.download_file(bucket_name, obj.key, local_filename)
                
def ensure_folder_exists(folder):
    try:
        if not os.path.exists(folder):
            os.makedirs(folder)
            print(f"Directorio '{folder}' creado exitosamente.")
        else:
            print(f"El directorio '{folder}' ya existe.")
    except Exception as e:
        print(f"Error al crear el directorio '{folder}': {e}")

def download_parquets():
        
    ensure_folder_exists(temp_dir)

    for ldbd in gc.loadboards:
        
        ## Download from glacier s3
        prefix = f"generalScrap/{ldbd.upper()}/historical"
    
        for obj in s3_resource.Bucket(bucket_name_glacier).objects.filter(Prefix=prefix):     
            file_name = obj.key.split('/')[-1]
            ensure_folder_exists(f"{temp_dir}/{ldbd}")
            local_filename = f"{temp_dir}/{ldbd}/{file_name}"
            s3.download_file(bucket_name_glacier, obj.key, local_filename)
            
        ## Download from regular s3
        prefix = f"generalScrap/{ldbd.upper()}/processing/output"
        week_start, week_end = get_week_dates(0) 
        
        for obj in s3_resource.Bucket(bucket_name).objects.filter(Prefix=prefix):
            file_name = obj.key.split('/')[-1]
            lbdb_name = 'tsmart' if ldbd == 'tsmarter' else ldbd
            if file_name == f"{lbdb_name}.parquet":
                local_filename = f"{temp_dir}/{ldbd}/{lbdb_name}_{week_start.strftime('%Y-%m-%d')}_{week_end.strftime('%Y-%m-%d')}.parquet"
                s3.download_file(bucket_name, obj.key, local_filename)

download_parquets()
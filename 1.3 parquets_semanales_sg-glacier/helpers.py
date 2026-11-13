import requests
import time
import datetime as dt
import pandas as pd
import numpy as np
import ast
import json
import os
import re
import boto3
from botocore.exceptions import NoCredentialsError
from dotenv import load_dotenv
#import processing.paths as P
#import processing.utils.constants as gc
#from processing.utils.lib import read_csv
#from processing.utils.lib_test import read_csv as read_csv_test
#from processing.utils.upload_s3 import S3FileManager
import warnings
warnings.filterwarnings("ignore")

load_dotenv()

def get_week_dates(less_weeks=0):
    
    today = dt.date.today()
    
    target_date = today - dt.timedelta(weeks=less_weeks)
    year, week, _ = target_date.isocalendar()

    first_day = dt.date.fromisocalendar(year, week, 1) 
    
    last_day = first_day + dt.timedelta(days=6)
    
    return first_day, last_day

def get_weeks_ago(first_day, last_day):
    """
    Calcula cuántas semanas atrás está una fecha dada en comparación con la semana actual.
    La semana actual es la semana 0.
    """
    first_day = dt.datetime.strptime(first_day, '%Y-%m-%d').date()
    last_day = dt.datetime.strptime(last_day, '%Y-%m-%d').date()
    # Verificar que la diferencia de días sea de 6
    if (last_day - first_day).days != 6:
        raise ValueError("Las fechas no corresponden a una semana válida (7 días).")
    
    # Obtener la fecha actual
    today = dt.date.today()
    current_year, current_week, _ = today.isocalendar()
    
    # Calcular el número de semana y año para la fecha proporcionada
    year, week, _ = first_day.isocalendar()
    
    # Calcular semanas de diferencia (teniendo en cuenta el año)
    weeks_difference = (current_year - year) * 52 + (current_week - week)
    
    return weeks_difference

def get_data_range_pd(min_date, max_date, frq):
    return pd.DataFrame(pd.date_range(min_date, max_date, freq=frq), columns=['start_date'])
import re
from datetime import datetime, timedelta
import os
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Callable
import requests
import constants as C
import pandas as pd
import math
import csv
import boto3
from dotenv import load_dotenv
load_dotenv()


def initialize_boto3(environment):

    #bucket_suffix = "_PROD" if environment != 0 else ""
    s3_bucket_name = "efrouting-dev-scraping"
    aws_access_key_id = os.environ.get("AWS_ACCESS_KEY_ID", "")
    aws_secret_access_key = os.environ.get("AWS_SECRET_ACCESS_KEY", "")

    session = boto3.Session(
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
    )
    s3_resource = session.resource("s3")
    s3 = session.client("s3")
    return s3_resource, s3, s3_bucket_name


## Reader utils

def extract_date_from_filename(filename: str) -> int:
    """Extracts the timestamp from the filename using a regex and converts it to an integer timestamp."""
    try:
        date_str = re.search(r"\d{2}-\d{2}-\d{4}_\d{2}h\d{2}m\d{2}s", filename).group()
        date_format = "%d-%m-%Y_%Hh%Mm%Ss"
        return int(datetime.strptime(date_str, date_format).timestamp())
    except AttributeError:
        raise ValueError(
            f"No se pudo extraer la fecha del nombre del archivo: {filename}"
        )


def append_timestamp_to_loads(loads: list, timestamp: int) -> list:
    """Appends the timestamp to each load in the list."""
    return [{**item, "removedef": timestamp} for item in loads]

## formatter utils

def process_loads_in_parallel(loads: List[Any], transform_function):
    """Processes all loads in parallel using the given transform function."""
    with ThreadPoolExecutor() as executor:
        transformed_loads = list(executor.map(transform_function, loads))
    return transformed_loads


def convert_timestamp(data, value, divisor) -> str:
    try:
        value_row = data.get(value)
        if value:
            value_seconds = (
                int(value_row) // divisor
            )  # Convertir milisegundos a segundos
            return datetime.fromtimestamp(int(value_seconds)).strftime(
                '%Y-%m-%dT%H:%M:%SZ'
            )
        else:
            return None
    except (ValueError, TypeError):
        return None


def convert_date(data, value) -> str:
    try:
        date_str = data.get(value)
        if value:
            timestamp_date = datetime.strptime(date_str, "%m/%d/%Y")
            return timestamp_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        else:
            return None
    except (ValueError, TypeError):
        return None


def extract_numeric_value(value_str: str) -> float:
    """Extracts numeric value from a string."""
    try:
        if value_str:
            return float(value_str)
        return 0  # Cambiar '' a None para mantener consistencia con el tipo de dato esperado
    except ValueError:
        return 0

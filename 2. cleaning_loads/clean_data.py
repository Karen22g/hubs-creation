import polars as pl
import pandas as pd
import numpy as np

def filter_states(df: pl.DataFrame) -> pl.DataFrame:
    """Excluye AK, HI y PR de StateOrigin y StateDestination."""
    return df.filter(
        ~pl.col('StateOrigin').is_in(['AK', 'HI', 'PR']) &
        ~pl.col('StateDestination').is_in(['AK', 'HI', 'PR'])
    )


def remove_duplicates(df: pl.DataFrame) -> pl.DataFrame:
    """Elimina duplicados por ID, o por columnas específicas si es jbhunt."""
    is_jbhunt = df.filter(pl.col('Source') == 'jbhunt').height > 0
    if is_jbhunt:
        return df.unique(
            subset=["CityOrigin", "StateOrigin", "CityDestination", "PickUp",
                    "StateDestination", "Weight", "Equip"],
            keep="first"
        )
    else:
        df_dedup = df.unique(subset=["ID"], keep="last")
        print(df_dedup['ID'].unique().to_list()[:5], '...')
        print(df_dedup['ID'].n_unique())
        return df_dedup


def remove_empty_values(df: pl.DataFrame) -> pl.DataFrame:
    """Elimina filas con estados o ciudades vacíos o nulos."""
    return df.filter(
        pl.col('StateOrigin').is_not_null()      & (pl.col('StateOrigin') != '')      &
        pl.col('StateDestination').is_not_null() & (pl.col('StateDestination') != '') &
        pl.col('CityOrigin').is_not_null()       & (pl.col('CityOrigin') != '')       &
        pl.col('CityDestination').is_not_null()  & (pl.col('CityDestination') != '')
    )

def remove_duplicates_general(data: pd.DataFrame) -> pd.DataFrame:

    print(data.columns.tolist())

    """
    This function removes duplicate rows from the provided DataFrame
    based on specific columns.
    Args:
    data (pd.DataFrame): The dataset to be processed.
    Returns:
    pd.DataFrame: A DataFrame with duplicates removed.
    """
    # Ensure the input is a DataFrame
    if not isinstance(data, pd.DataFrame):
        raise ValueError("Input data must be a pandas DataFrame.")
    # List of columns to check for duplicates

    cols_duplicates = [
        "Posted",
        "CityOrigin",
        "StateOrigin",
        "CityDestination",
        "StateDestination",
        "PickUp",
        "Equip",
        "Broker_Shipper",
        "Weight",
        "Size",
    ]

    # Ensure all specified columns exist in the DataFrame
    #if not isinstance(data.columns, list):  # Convertir a lista si es necesario
     #   data.columns = data.columns.tolist()

    if isinstance(cols_duplicates, (pd.Index, np.ndarray)):  
        cols_duplicates = cols_duplicates.tolist()  # Convertir a lista de strings si es necesario

    # Ensure all specified columns exist in the DataFrame
    missing_cols = [col for col in cols_duplicates if col not in data.columns]
    
    if missing_cols:
        raise ValueError(
            f"The following columns are missing from the DataFrame: {', '.join(missing_cols)}"
        )
    # Remove duplicates based on the specified columns
    df = data.drop_duplicates(
        subset=cols_duplicates, keep="first"
    )  # Keep the first occurrence
    return df
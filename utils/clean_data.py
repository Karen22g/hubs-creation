import pandas as pd
import numpy as np
#borrar estados random

def filter_states(data: pd.DataFrame) -> pd.DataFrame:
    """
    Excludes rows from the DataFrame where 'StateOrigin' or 'StateDestination'
    are non-contiguous U.S. states or territories (AK, HI, PR).

    Args:
        data (pd.DataFrame): DataFrame with 'StateOrigin' and 'StateDestination' columns.

    Returns:
        pd.DataFrame: DataFrame with rows excluded based on the 'StateOrigin'
                      and 'StateDestination' values.
    """
    filtered_df = data.query(
        "not(StateOrigin.isin(['AK', 'HI', 'PR'])) & "
        "not(StateDestination.isin(['AK', 'HI', 'PR']))"
    )

    return filtered_df

#borrar por ID cargas iguales
#borrar las de jbhunt por sus columnas que hacen match

def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Sort and remove duplicates based on ID and specific columns for JBHUNT."""
    #df = df.sort_values(by="Removed", ascending=False).copy()

    df['Source'].unique()

    if df['Source'] != 'jbhunt':
        df = df.drop_duplicates(subset=["ID"], keep="last")
        print(df['ID'].unique())
        print(df['ID'].nunique())
    else:
        df = df.drop_duplicates(subset=["CityOrigin", "StateOrigin", "CityDestination","PickUp", 
                                        "StateDestination", "Weight", "Equip"], keep="first")
    
    return df

#df_duplicates.reset_index(drop=True, inplace=True)

#borrar duplicados entre loadboards

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

#ver si esto realmente ocurre
#ciudades origen/destino desconocidas

def remove_empty_values(df: pd.DataFrame) -> pd.DataFrame:
    """
    Removes rows from the DataFrame where any of the following columns contain empty or missing
    values: 'StateOrigin','StateDestination', 'CityOrigin', 'CityDestination'

    This function filters out rows with NaN or empty strings ('') in the specified columns to
    ensure that the data is complete for further processing.

    Args:
        df (pd.DataFrame): The input DataFrame containing the columns to be checked for missing
        or empty values.

    Returns:
        pd.DataFrame: The filtered DataFrame with rows removed where any of the specified columns
        have missing or empty values.
    """

    query_condition = (
        "StateOrigin.notna() & StateDestination.notna() & "
        "CityOrigin.notna() & CityDestination.notna()"
    )

    second_condition = (
        "StateOrigin != '' & StateDestination != '' & "
        "CityOrigin != '' & CityDestination != ''"
    )

    filtered_df = df.query(query_condition).query(second_condition)

    return filtered_df
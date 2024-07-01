import lightcast_api.coreLmi as corelmi
import pandas as pd

conn = corelmi.CoreLMIConnection()

def build_query_corelmi(cols: list, constraints: list[dict] = []) -> dict:
    query: dict = {"metrics": [], "constraints": constraints}

    # take as list of column names just to make the syntax easier
    # convert it to expected syntax for the API
    for c in cols:
        query["metrics"].append({"name": c})

    return query


def query_corelmi(dataset: str, query: dict, datarun: str = "2024.2") -> pd.DataFrame:
    return conn.post_retrieve_df(dataset, query, datarun)



from . import coreLmi
import pandas as pd

class Lightcast:
    conn = coreLmi.CoreLMIConnection()
    def __init__(self):
        pass

    def build_query_corelmi(self, cols: list, constraints: list[dict] = []) -> dict:
        query: dict = {"metrics": [], "constraints": constraints}

        # take as list of column names just to make the syntax easier
        # convert it to expected syntax for the API
        for c in cols:
            query["metrics"].append({"name": c})

        return query

    def query_corelmi(self, dataset: str, query: dict, datarun: str = "2024.2") -> pd.DataFrame:
        return self.conn.post_retrieve_df(dataset, query, datarun)

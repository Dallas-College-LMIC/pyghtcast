import pandas as pd

from . import base, coreLmi, openSkills


class Lightcast:
    conn: coreLmi.CoreLMIConnection | None = None

    def __init__(self, username: str, password: str):
        self.conn = coreLmi.CoreLMIConnection(username, password)

    def build_query_corelmi(self, cols: list, constraints: list[dict] | None = None) -> dict:
        if constraints is None:
            constraints = []
        query: dict = {"metrics": [], "constraints": constraints}

        # take as list of column names just to make the syntax easier
        # convert it to expected syntax for the API
        for c in cols:
            query["metrics"].append({"name": c})

        return query

    def query_corelmi(self, dataset: str, query: dict, datarun: str = "2025.3") -> pd.DataFrame:
        return self.conn.post_retrieve_df(dataset, query, datarun)


class JobPostings:
    conn: base.JobPostingsConnection | None = None

    def __init__(self):
        self.conn = base.JobPostingsConnection()

    def totals(self, payload: dict) -> dict:
        return self.conn.post_totals(payload)

    def rankings(self, facet: str, payload: dict) -> pd.DataFrame:
        return self.conn.post_rankings_df(facet, payload)

    def timeseries(self, payload: dict) -> dict:
        return self.conn.post_timeseries(payload)


class Skills:
    conn: openSkills.SkillsClassificationConnection | None = None

    def __init__(self, username: str, password: str):
        self.conn = openSkills.SkillsClassificationConnection(username, password)

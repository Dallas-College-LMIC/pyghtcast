#!/usr/bin/env python3
"""Example pulls against the Lightcast Core LMI API for the DFW 13-county area."""

from __future__ import annotations

import os

import pandas as pd

from .lightcast import Lightcast

DFW_13_FIPS = {
    "collin": 48085,
    "dallas": 48113,
    "denton": 48121,
    "ellis": 48139,
    "hunt": 48231,
    "kaufman": 48257,
    "rockwall": 48397,
    "hood": 48221,
    "johnson": 48251,
    "parker": 48367,
    "somervell": 48425,
    "tarrant": 48439,
    "wise": 48497,
}


def industry_pull(lc: Lightcast) -> pd.DataFrame:
    cols = [
        "Jobs.2013",
        "Jobs.2018",
        "Jobs.2023",
        "Jobs.2033",
    ]

    constraints = [
        {
            "dimensionName": "Area",
            "mapLevel": {
                "level": 4,
                "predicate": [str(fips) for fips in DFW_13_FIPS.values()],
            },
        },
        {
            "dimensionName": "Industry",
            "mapLevel": {"level": 2, "predicate": ["10"]},
        },
    ]

    query = lc.build_query_corelmi(cols=cols, constraints=constraints)

    df = lc.query_corelmi(dataset="emsi.us.industry", query=query)

    df = df[df["Area"].str.contains("ZIP")]
    df["Area"] = df["Area"].str.removeprefix("ZIP")
    return df


def occupation_pull(lc: Lightcast) -> pd.DataFrame:
    cols = [
        "Jobs.2022",
        "ResidenceJobs.2022",
    ]

    constraints = [
        {
            "dimensionName": "Area",
            "mapLevel": {
                "level": 4,
                "predicate": [str(fips) for fips in DFW_13_FIPS.values()],
            },
        },
        {
            "dimensionName": "Occupation",
            "mapLevel": {"level": 5, "predicate": ["00-0000"]},
        },
    ]

    query = lc.build_query_corelmi(cols=cols, constraints=constraints)
    df = lc.query_corelmi(dataset="emsi.us.occupation", query=query)

    df = df[df["Area"].str.contains("ZIP")]
    df["Area"] = df["Area"].str.removeprefix("ZIP")
    return df


if __name__ == "__main__":
    lc = Lightcast(os.environ["LCAPI_USER"], os.environ["LCAPI_PASS"])
    print(industry_pull(lc))
    print(occupation_pull(lc))

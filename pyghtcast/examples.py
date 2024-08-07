#!/usr/bin/env python3
from lightcast import build_query_corelmi, query_corelmi

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

def industry_pull():
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

    query = build_query_corelmi(cols=cols, constraints=constraints)

    df = query_corelmi(dataset="emsi.us.industry", query=query)

    df = df[df["Area"].str.contains("ZIP")]
    df["Area"] = df["Area"].str.removeprefix("ZIP")
    return df


def occupation_pull():
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

    query = build_query_corelmi(cols=cols, constraints=constraints)
    df = query_corelmi(dataset="emsi.us.occupation", query=query)

    df = df[df["Area"].str.contains("ZIP")]
    df["Area"] = df["Area"].str.removeprefix("ZIP")
    return df

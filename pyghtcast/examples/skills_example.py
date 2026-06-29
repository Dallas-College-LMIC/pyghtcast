"""Smoke test the Skills API connection using LCAPI_USER / LCAPI_PASS."""

import os

from pyghtcast import lightcast

skills = lightcast.Skills(os.environ["LCAPI_USER"], os.environ["LCAPI_PASS"])

# Confirm the connection works by listing available Skills API versions.
versions = skills.conn.get_versions()
print(f"Skills API connected; {len(versions)} version(s) available.")

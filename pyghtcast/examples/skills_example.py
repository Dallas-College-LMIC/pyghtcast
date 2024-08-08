from pyghtcast import lightcast
import os

user = os.environ.get("LCAPI_USER", "")
pwd = os.environ.get("LCAPI_PASS", "")

skills = lightcast.Skills(user, pwd)

print(user)
print(pwd)

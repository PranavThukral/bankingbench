import os
from hypothesis import settings

settings.register_profile("ci", derandomize=True, database=None, max_examples=200, deadline=None)
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "ci"))

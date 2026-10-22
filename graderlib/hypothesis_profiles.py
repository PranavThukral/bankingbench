import os
from hypothesis import Phase, settings

# No shrinking phase: a failing property already rejects the solution, and shrinking a failure
# could add minutes without changing the verdict. Explicit examples still run first.
settings.register_profile("ci", derandomize=True, database=None, max_examples=200, deadline=None,
                          phases=[Phase.explicit, Phase.reuse, Phase.generate])
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "ci"))

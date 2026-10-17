# 90-second walkthrough (script)

**0–15 s — the problem.**
"An eval is only as good as its grader. If a grader passes plausible-but-wrong code, models get
rewarded for bugs. I built ten banking tasks to measure how often that happens, and how to fix it."

**15–40 s — task 01.** *Show `tasks/01_idempotent_payments/PROBLEM.md`, then the
`wrong_retry_race` overlay.*
"The ticket: payment retries must be idempotent; concurrent duplicates charge once. This wrong
solution checks for the key, calls the card network, then inserts. It's what most people write
first. It passes every sequential test, but two simultaneous retries both get charged."

**40–65 s — naive vs final.** *Open `results/final/report.html`, scroll from the naive grid to
the final grid.*
"Each row is a task; each column a solution. Under the naive graders, 29 of 30 wrong solutions
pass, which is red. The hardened graders reject all 30, and still accept both the reference and a
structurally different correct solution for every task. Zero flips across repeated runs."

**65–80 s — one finding.** *Open `analysis/findings.md`, the task 10 finding.*
"The hardening process has its own failure mode. My first hardened grader for the batch-file
parser dropped an earlier regression test, so the unmodified starter passed. Running the starter
through every grader version caught it. That's the kind of check that scales to a task factory."

**80–90 s — Harbor export.** *Show `dist/harbor/01_idempotent_payments/`.*
"Every task exports to the Harbor format with an oracle check: the reference solution scores 1,
the starter scores 0. Repo link in the description."

# Landing page audit — visual and copy pass (2026-10-18)

Baseline: commit `390bf14`, `site/index.html`.
Measured full-page height: **7,363 px at 1440 wide** (about 8 screens) and **16,707 px at 390 wide** (about 20 phone screens).

**Targets:** ≤ **4,200 px at 1440** and ≤ **9,000 px at 390**. Cut words before cutting design. Every number stays computed from the embedded data.

## Visual findings

| # | Where | Problem | Change |
|---|---|---|---|
| V1 | Hero card + stat band | The hero card already shows 20/30 → 0/30 and 20/20 correct accepted. The stat band directly below repeats it (20→0, 0/20, 60/60). | **Delete the stat band.** The hero card is the summary. If "10 tasks" is needed, it goes in the hero sentence. |
| V2 | Hero | Three layers of metadata sit before any content: the disclaimer under the CTAs, the proofline (commit / runs / Python), then the stats. | **Delete the hero disclaimer and the proofline.** Both move to the footer. |
| V3 | Hero card | The card is rotated a few degrees. The text sits off-axis and the tilt reads as a gimmick. | Remove the rotation and keep the shadow. |
| V4 | Hero ribbon | Only a small wedge shows in the top-right corner. It looks cropped rather than intentional. | Let it sweep behind the card, larger and lower-opacity, so it frames the card. Keep reduced-motion handling. |
| V5 | "How it works" | Four tall cards with chip mockups (~700 px) explain what the worked example below shows anyway. | **Merge it into the example section** as one compact numbered strip (≤ 120 px): `1 Ticket · 2 Five solutions · 3 Naive grader · 4 Hardened grader`, one short line each. Delete the cards. |
| V6 | Worked example | The left list's blurbs are 2–3 lines each, and the open step pushes the layout. | One line per step. Keep the code window as the visual anchor. |
| V7 | Results matrix | ~1,600 px at 1440. Each cell stacks a name, two text rows and a tag. | Make it a **compact heatmap**: per cell, the short variant name plus two small squares (naive, hardened), with a dashed outline when caught by hardening. Target row height ≤ 64 px. Verdict text and test counts live in the drawer. On mobile, keep per-task cards with the same compact cells. |
| V8 | Results toolbar | Five filter chips plus a legend sentence plus a footnote paragraph. | Three chips: **All**, **Caught by hardening**, **Naive grader caught it**. One-line legend. Delete the footnote paragraph. |
| V9 | Patterns bento | Five large cards (~900 px) with chip rows. | **One row of four short items** (title + one sentence, no chips) on desktop, stacked on mobile. Drop "Hardening regresses too" or fold it into the footer fine print. |
| V10 | "Reproducible and portable", closing CTA, footer | Three sections (~1,100 px) all saying "here are links". | **Merge into one footer**: link row (Full report, Findings, Summary, matrix.json, Repository if set), the rerun command as one line of code, the run line (commit, runs, wall time, Python, PostgreSQL), and **one** fine-print paragraph. |
| V11 | Section spacing | `section{padding:120px 0}` everywhere. | 72–88 px on desktop, 56 px on mobile. |

## Copy findings (AI-speak and inferable fluff)

Rules for every string on the page:
- No aphorisms or slogans. No staccato fragment triads ("A retry works. A race double-charges. The quick grader never sees it.").
- No two-tone headlines whose grey half restates the dark half. Keep the two-tone treatment only where the second half adds a fact.
- No "not X, but Y" constructions, and no "genuinely", "actually", "every … is written down" or "Here is what changed".
- No instructions the UI already makes obvious ("Select any cell…", "Follow each verdict…").
- No claims the data doesn't support ("It's what most people write first").
- State limitations **once**, in the footer.

| Location | Current | Replace with |
|---|---|---|
| Eyebrow | A portfolio experiment in AI evaluation | Coding tasks and graders · synthetic data |
| H1 | Good code deserves a better grader. | How often does a first-draft grader pass wrong code? |
| Hero sentence | 10 finance coding tasks for evaluating AI coding models. Build the hidden tests, try plausible wrong solutions, then harden the grader. Here is what changed. | `${n}` synthetic finance coding tasks, each with three plausible wrong solutions. The first-draft graders accepted `${naivePass}` of `${wrongTotal}`. The hardened graders accept none and still pass every correct solution. *(computed)* |
| CTAs | Explore the evidence / See one bug | See the results / Read one example |
| Hero card title | Same code. Better tests. | Wrong solutions accepted |
| How-it-works heading | A grader is only as good as the wrong answers it rejects. So every task ships with some. | *(delete; the section is merged)* |
| Example heading | A retry works. A race double-charges. The quick grader never sees it. | Example: duplicate payment retries |
| Example step 1 | The ticket says concurrent duplicates must charge exactly once. It says nothing about how. | The ticket: concurrent duplicates must charge once. |
| Example step 2 | Look up the key, charge the card, then save the key. It's what most people write first, and every sequential retry works. | The bug: check for the key, charge, then save the key. |
| Example step 3 | It retries one request after another. The first response is already saved… | Naive grader: retries are sequential, so the race never happens. |
| Example step 4 | Callers wait at a barrier and fire together… repeated rounds must each produce exactly one charge. | Hardened grader: ten simultaneous callers, one charge allowed. |
| Ticket pane note | The ticket states the observable behaviour only. Any design that meets it is accepted: … | Two valid designs pass: a reserved key row (409 while in flight) or an advisory lock (duplicates wait). |
| Results heading | Every solution, both graders. Follow each verdict to the tests behind it. | Results |
| Patterns heading | Bugs that pass ordinary tests cluster into a few shapes. | What the first-draft graders missed |
| Pattern 1 | State over time is invisible to one-shot tests — The bug only appears on a second request… The fix: sequences, restarts, a fake clock and a barrier. | **Bugs that need two events.** Restarts, retries, clock changes and concurrent calls. |
| Pattern 2 | Numeric bugs live on rare inputs — Half-up vs banker's rounding… The fix: searched ties and boundaries, checked with exact fractions. | **Rounding ties and boundaries.** Wrong code agrees with right code almost everywhere else. |
| Pattern 3 | Totals hide identity bugs — … The fix: assert the exact pairs and per-scope results. | **Right totals, wrong pairing.** Count checks miss reused entries and unscoped keys. |
| Pattern 4 | Rejections need state checks, not just error checks — … | **Half-applied rejections.** The right error, with state left behind. |
| Reproducible heading | One command to rerun it. One export to use it elsewhere. | *(delete; footer)* |
| Closing | Read the hardening log. Every miss is written down. | *(delete; footer link "Hardening log")* |
| Hero + footer disclaimers | Two separate limitation passages | One footer paragraph: "Synthetic tasks and author-written solutions; results describe this sample, not model performance. Verified natively on Windows; the Docker path is untimed. Blind reviews are self-reviews so far." |
| Matrix footnote | `N of M solutions match. Green: expected verdict. Red: …` | *(delete; the one-line legend covers it)* |

# Portfolio notes

A creator-vetting tool that is explicit about what it cannot know: relative scores, heuristic flags, and a refusal rule for small cohorts.

## Bullets you can defend today (each is backed by the test suite or a screenshot in this repo)
- Built an explainable creator-scoring engine: cohort-relative percentiles, weighted heuristic authenticity signals, CPM/CPE, and a rule that withholds the score when fewer than 5 comparable creators exist.
- Fixed a false-positive design flaw (the lowest creator in any small cohort was flagged) by requiring both bottom-decile rank and under one third of the cohort median; covered by a regression test on the demo cohort.
- Shipped an interactive dashboard (filters, scatter, per-signal explanations) and a privacy-preserving importer that stores only a duplicate-comment ratio; 7 automated tests including real-browser checks.

## Add these only after you have measured them yourself (do not publish a number you have not measured)
- Scored [N] real creators across [M] platforms; [K] flagged high risk, of which I verified [J] manually.
- Agreement between my manual vetting and the score ranking: [measure it].

## Interview questions this project prepares you for
**How do you score without industry benchmarks?**  
Percentiles within the imported cohort. It's relative by design, and the tool refuses to score a creator whose cohort has fewer than 5 members.

**Can this detect fake followers?**  
No. It surfaces heuristic signals from public numbers (follower jumps, weak reach, duplicate comments) and says they are not proof; a human decides.

**What was a bug you found in your own scoring?**  
The first risk rule flagged the lowest creator in every small cohort. Requiring both bottom decile and under a third of the median fixed it.

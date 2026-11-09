# Method: CreatorScore

## Scoring
Score = `(0.4*engagement_pct + 0.3*reach_pct + 0.3*consistency) * (1 - 0.5*risk)`, 0-100.
- Percentiles are within the creator's platform+tier cohort (falls back to the platform; **score withheld below 5 comparable creators**). No invented industry benchmarks.
- consistency = share of posts with views within 0.5x-2x of the median.
- Risk signals (weights): follower spike 0.35 (robust z >= 4 and >= 5% jump), low reach 0.20, low engagement 0.15 (both: bottom decile **and** under a third of cohort median), duplicate/wordless comments 0.30 (>= 30%). Only evaluable signals count; < 0.5 evaluable weight => "insufficient data". Risk is `triggered weight / evaluable weight`. **Heuristic, not proof of fraud.**
- CPM = rate / (median views / 1000); CPE = rate / median engagements. Tiers: nano < 10k, micro < 100k, mid < 500k, macro < 1M, mega.

## Limits you should state in any write-up
- Risk is a set of **heuristic signals from public numbers, not proof of fraud**. The API and UI say so on every record.
- Percentiles are relative to *your imported cohort*. No industry benchmark is invented; with fewer than 5 comparable creators the score is withheld.
- Scores are comparable only within one cohort and one point in time. Small post counts lower the stated confidence.
- Only a duplicate/wordless-comment *ratio* is stored; comment text and author identities are never stored.

<!--
Background knowledge template.

Copy this file to the project root as `background_knowledge.md` (git-ignored),
fill it in for one decision, and point to it from decision.yaml:

    background_knowledge_path: "background_knowledge.md"

The whole file is appended to 00_context.md under "## Background Knowledge",
so every perspective agent sees it before allocating points.

Guidelines:
- State facts, constraints and evidence. Do NOT write a recommendation —
  the perspective agents and the decision-maker do the weighing.
- Use the same candidate IDs as decision.yaml (A, B, C, ...).
- Say how each fact was verified, so agents can tell evidence from assumption.
- Leave out anything you would not want an LLM provider to process
  (personal data, confidential contract terms, credentials).
- Delete this comment and any section that does not apply.
-->

# <Decision name> — background knowledge

**Decision ID:** <AD-xxx, matches decision.yaml>  
**Prepared:** <YYYY-MM-DD>  
**Status:** Background for trade-off analysis. No recommendation.

## 1. Decision to make

<One or two sentences: the question being decided, and who decides.>

| ID | Option | Description |
|---|---|---|
| A | <name> | <what it is, how it would be delivered> |
| B | <name> | <...> |

<Options considered and excluded, with the reason:>

## 2. Fixed constraints

Constraints that are already agreed and are not up for trade-off.

| Ref | Constraint | Applies to / from |
|---|---|---|
| <REQ/AD/principle ID> | <constraint> | <scope or date> |

## 3. Established facts

| # | Fact | How verified |
|---|---|---|
| F1 | <fact relevant to the choice> | <source read, test run, vendor confirmation, ...> |

## 4. Criteria and evidence per option

Criteria derive from §2 and §3. Weighting is left to the perspectives.

| Criterion (source) | A — <name> | B — <name> |
|---|---|---|
| <criterion> (<REQ/F ref>) | <evidence for A> | <evidence for B> |

## 5. Costs and effort

| Item | A | B |
|---|---|---|
| One-off (build, migration, licences) | | |
| Recurring (run, support, licences) | | |
| Exit cost | | |

## 6. Risks and assumptions

| # | Risk or assumption | Affects | Mitigation / how to resolve |
|---|---|---|---|
| R1 | | <A/B/all> | |

## 7. Open questions

Questions the decision-maker still needs answered. Agents should flag where
their scoring depends on one of these.

1. <question> — owner: <role>, needed by: <date>

## 8. Sources

| Source | Version / date | What was used |
|---|---|---|
| <document, call notes, repository, register> | | |

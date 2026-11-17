# User Testing: Plan & Report

> **Status: not yet conducted.** This page holds the session plan and a report
> template. Fill in the [Results](#results) section after the sessions.
> Until then, nothing here is a user finding.

## Goals

Answer the FP10 success criteria "Users find tool intuitive and useful" and
"Feedback collected for v2 planning":

1. Can a developer who has never seen the tool load a repository and answer a
   dependency question **without help**?
2. Which page do people actually use to answer dependency questions: Search,
   Dependencies or Graph?
3. Is the graph understandable on a real repository (hundreds to thousands of nodes)?
4. Which missing feature would people want first: GitLab, private repos,
   impact analysis, or something else?

## Participants

- **5 developers** (5 sessions find most usability problems). Aim for a mix of:
  - 2 who use Python day to day, 2 who use JS/TS, and 1 other
  - at least 1 who has joined an unfamiliar codebase in the past 6 months
- Not on the project team.
- Record: role, years of experience, main language, and whether they've used
  Sourcegraph, GitHub code navigation or IDE call hierarchies.

## Setup

- App running locally or on a staging deployment, with Neo4j **empty**.
- Test repository: `https://github.com/psf/requests` (about 37 Python files,
  imports in a few seconds, and familiar to many developers).
- Screen and audio recording with consent. A moderator and a note-taker.
- 30 minutes per session: 2 min intro, 20 min tasks, 8 min debrief.

## Tasks

Read each task aloud and don't hint at which page to use. Record time on task,
success (yes / with help / no), the path taken, and quotes.

| # | Task | Success when | Target time |
|---|---|---|---|
| T1 | "Load the `requests` repository from GitHub into the tool." | Import completes | 2 min |
| T2 | "Find where the class `Session` is defined." | Names `sessions.py` | 1 min |
| T3 | "Which files import `models.py`?" | Lists the imported-by files | 2 min |
| T4 | "If you changed `utils.py`, which files might be affected?" | Names direct importers, using any page | 3 min |
| T5 | "Show the graph around `api.py` and find a file two import hops away." | Identifies a 2-hop file | 3 min |
| T6 | "Find a function whose name you only roughly remember: something like `get_enviroment_proxies`." | Finds `get_environ_proxies` via typo match | 1 min |
| T7 | "Upload these 3 files (provided) and look at how they connect." | Notices whether import links appear (probes known issue K1) | 3 min |

## Debrief questions

1. On a scale of 1–5, how easy was the tool to use? Why?
2. What did you expect to happen that didn't?
3. Which page would you use most? Which would you never use?
4. Would you use this when joining a new codebase? What would make you use it?
5. Pick one: GitLab support, private repos, "what breaks if I change this", or
   something else. Which do you want first?
6. **SUS questionnaire** (System Usability Scale, 10 standard items) at the end.

## Results

*Fill in after the sessions.*

### Participants

| P | Role | Experience | Main language | Similar tools used |
|---|---|---|---|---|
| P1 | | | | |
| P2 | | | | |
| P3 | | | | |
| P4 | | | | |
| P5 | | | | |

### Task outcomes

✅ = unaided, 🟡 = with help, ❌ = failed. Put time in the cell.

| Task | P1 | P2 | P3 | P4 | P5 | Success rate | Median time |
|---|---|---|---|---|---|---|---|
| T1 | | | | | | | |
| T2 | | | | | | | |
| T3 | | | | | | | |
| T4 | | | | | | | |
| T5 | | | | | | | |
| T6 | | | | | | | |
| T7 | | | | | | | |

**SUS score:** mean ___ (range ___–___). Above 68 is above average.

### Findings

| # | Finding | Seen in | Severity (1–4) | Evidence (quote or observation) | Proposed change |
|---|---|---|---|---|---|
| F1 | | | | | |

Severity: 4 = blocks the task, 3 = major delay, 2 = minor friction, 1 = cosmetic.

### Feature demand

| Feature | Votes |
|---|---|
| GitLab | |
| Private repos | |
| Change impact | |
| Other: | |

### Changes made in response

| Finding | Change | Commit |
|---|---|---|
| | | |

### Impact on the roadmap

*Describe how the results change the order in [roadmap.md](roadmap.md).*

# Wajha — Verification Record

This record lists the acceptance scenarios for Wajha, what was expected, what actually happened, and the result. It also summarises the automated tests and lists known limitations.

## How these checks were run

- **Date:** 9 October 2026
- **Version:** the `main` branch at the time of writing (Python 3.14.7, Django 6.1.2, SQLite)
- **Data:** a fresh database loaded with `python manage.py load_demo_data` (fictitious accounts and trips; see the README)
- **Method:** each scenario was executed through the application's real URLs, forms and views with Django's test client, using the demo accounts. Every run happened inside a database transaction that was rolled back afterwards, so the demo data stayed unchanged.
- **Manual re-check:** the last column is for a person to repeat the scenario in a browser before submission and initial it.

## Acceptance scenarios

| ID | Scenario | Expected result | Actual result | Status | Manual re-check |
|---|---|---|---|---|---|
| V01 | **Main workflow:** register two new users, create a trip, the second user joins with the code typed in lower case, both add preferences, the organizer generates recommendations, opens the explanation and finalizes | Trip saved as Decided with the top recommendation; Trip Room shows the boarding-pass decision card | 7 recommendations saved; explanation page loaded (200); trip status DECIDED with the rank-1 destination (Cairo); Trip Room shows "Final destination" | Pass | |
| V02 | Create a trip with every field empty | "This field is required." on all 4 fields; nothing saved | 4 required-field messages; no trip saved | Pass | |
| V03 | Create a trip whose end date is before its start date | "The end date must be after the start date."; nothing saved | Error shown; no trip saved | Pass | |
| V04 | Save preferences with a budget of 0 | "Budget must be at least 500 SAR."; nothing saved | Error shown; no preference saved | Pass | |
| V05 | Save preferences with a maximum flight of 4.3 hours | "Use whole or half hours"; nothing saved | Error shown; no preference saved | Pass | |
| V06 | Save preferences with no interest selected | "Choose at least one interest."; nothing saved | Error shown; no preference saved | Pass | |
| V07 | Join with a code no trip uses (WJ-ZZZZZ) | "No trip uses that code." | Error shown | Pass | |
| V08 | Sara joins Spring Break, which she is already in | Redirected to the trip with "already a member"; no duplicate membership | Message shown; members stayed at 3 | Pass | |
| V09 | Khalid joins the cancelled Eid Trip | Refused: the trip is cancelled and no longer accepts members | Error shown; not joined | Pass | |
| V10 | A ninth person joins a trip that already has 8 members | "This trip is full."; still 8 members | Error shown; 8 members | Pass | |
| V11 | Ammar filters My Trips by each status | All 5 · Planning 3 · Decided 1 · Cancelled 1, newest first | All 5 · Planning 3 · Decided 1 · Cancelled 1 | Pass | |
| V12 | Sara filters My Trips by Cancelled (she has none) | Empty state "No trips here" with "Show all trips" | Empty state shown | Pass | |
| V13 | Organizer generates for Spring Break while Khalid hasn't submitted | Refused with an explanation; no recommendations saved | Message shown; 0 saved | Pass | |
| V14 | Open recommendations for Weekend on a Budget (budgets 1,500 and 1,800 SAR) | "No destination fits everyone", with reasons per destination and no member names | Empty state shown; e.g. "Cairo ≈ 2,150 SAR — Over budget for 2 members"; no names in the reasons | Pass | |
| V15 | Winter Getaway group summary (**aggregation**) | Average budget (4500 + 4000 + 5000 + 3800) / 4 = **4,325 SAR** · lowest **3,800** · shortest max flight **5 h** · Food 3, Nature 2 | 4,325 · 3,800 · 5 h · Food 3, Nature 2 | Pass | |
| V16 | My Trips counts per trip (**annotation**) | Winter Getaway "4 of 4 ready" · Spring Break "2 of 3 ready" | Both shown correctly | Pass | |
| V17 | Winter Getaway: Tbilisi's saved score (hand calculation below) | Rank 1 · Group Match **87.7** · lowest member **79.9** · **3,200 SAR** per person | Rank 1 · 87.7 · 79.9 · 3,200 | Pass | |
| V18 | Faisal (a member) tries to generate, finalize and remove a member on Winter Getaway; Sara (not a member) opens it | 403 for each organizer action, 404 for the non-member; trip unchanged | 403 · 403 · 403 · 404; trip still Planning | Pass | |
| V19 | Organizer removes the waiting member Khalid from Spring Break (deletion with dependent records) | Membership deleted; group becomes 2 of 2 ready and can generate; Khalid gets 404 | Membership gone; can generate; Khalid sees 404 | Pass | |
| V20 | Cancelled Eid Trip keeps its records | Trip and both memberships still exist; status Cancelled | Cancelled; 2 members kept | Pass | |
| V21 | Sara edits her preferences on the decided Summer Escape | Refused; budget unchanged | Budget stayed 6,000 | Pass | |
| V22 | Organizer adds a night to Winter Getaway | Recommendations cleared because costs changed | 0 recommendations left | Pass | |
| V23 | Spring Break summary with only 2 submissions (privacy) | Budget figures hidden, with an explanation | Explanation shown; "5,500" not visible | Pass | |
| V24 | Open a trip that doesn't exist, with `DEBUG=False` | Custom 404 page | 404 with the Wajha "We couldn't find that page" page | Pass | |
| V25 | **Mobile and desktop layout** | Every page usable at phone width with no horizontal scrolling; navigation folds into a menu | Checked with headless Chrome at 390 px and 1280 px: landing, register/login, My Trips, create/join, Trip Room (planning, ready, decided), preferences, recommendations, explanation, confirmation pages, 404 | Pass | |
| V26 | **Fresh checkout** | Clone → virtual environment → `pip install -r requirements.txt` → copy `.env.example` → `migrate` → `load_demo_data` → all tests pass | Done from a clean clone after each development phase; latest run passed | Pass | |

**Result: 26 of 26 scenarios passed.**

## Hand calculation for V17 (Tbilisi, Winter Getaway)

The trip departs from Riyadh, 14–18 January 2027 (4 nights). January is in the Jan–Mar period, when Tbilisi is **Cold**.

**Estimated cost per person:** return flight 1,600 + daily cost 400 × 4 nights = **3,200 SAR**. That's within every member's budget, and the 3.5-hour direct flight is within every member's maximum, so Tbilisi passes all hard constraints.

| Member | Interests (35) | Budget comfort (25) | Weather (20) | Flight comfort (15) | Direct (5) | Score |
|---|---|---|---|---|---|---|
| Ammar: 4,500 SAR, 6 h, Cold, Nature + Food | 2 of 2 → 35 | 3,200 ≤ 80% of 4,500 → 25 | Cold = Cold → 20 | 3.5 h vs half of 6 h: 1 − 0.5 × (0.5 / 3) → 13.75 | 5 | **98.75** |
| Faisal: 4,000 SAR, 5 h, Mild, direct only, Food + Culture | 2 of 2 → 35 | 3,200 = 80% of 4,000 → 25 | Mild vs Cold (neighbours) → 10 | 1 − 0.5 × (1 / 2.5) = 0.8 → 12 | 5 | **87.00** |
| Mohammed: 5,000 SAR, 6 h, any weather, Nature + Adventure | 2 of 2 → 35 | → 25 | No preference → 20 | → 13.75 | 5 | **98.75** |
| Khalid: 3,800 SAR, 7 h, Cold, Shopping + Food | 1 of 2 → 17.5 | 1 − 0.5 × (160 / 760) → 22.37 | → 20 | 3.5 h ≤ half of 7 h → 15 | 5 | **79.87** |

- Average = (98.75 + 87.00 + 98.75 + 79.87) / 4 = **91.09**
- Group Match = 0.7 × 91.09 + 0.3 × 79.87 = 63.76 + 23.96 = **87.72**, saved as **87.7** (lowest member 79.9)

## Automated tests

`python manage.py test` runs **206 tests**; all passed on the latest run.

| File | Tests | What they protect |
|---|---|---|
| `trips/tests/test_matching.py` | 32 | Cost, each hard constraint (including limits exactly at the edge), each factor score, group formula, tie-breaks, ranking, all with hand-calculated values |
| `trips/tests/test_trip_management.py` | 35 | Finalize, cancel, edit and remove member: rules, permissions, locking after a decision, deletion with dependent records |
| `trips/tests/test_recommendations.py` | 30 | Generation, saved scores matching the engine, invalidation when the group changes, page states, privacy of exclusions |
| `trips/tests/test_preferences.py` | 23 | Preference validation, own-record only, different preferences per trip, readiness rules |
| `trips/tests/test_views.py` | 17 | Create trip validation, access (404/403), My Trips relationship query and member count |
| `trips/tests/test_join.py` | 15 | Invite code normalisation and every join rule |
| `trips/tests/test_reporting.py` | 14 | Group summary aggregation, interest vote annotation, status filter and per-trip counts |
| `trips/tests/test_models.py` | 11 | Database constraints: dates, status vs destination, unique membership, invite codes |
| `destinations/tests.py` | 11 | Catalog loader, catalog constraints, climate periods, bundled photos |
| `trips/tests/test_pages.py` | 5 | Landing, credits, custom 404 and 403 pages |
| `trips/tests/test_demo.py` | 5 | Demo data states, repeat runs, protection of real accounts |
| `accounts/tests.py` | 8 | Registration (hashed password, duplicates, required email), login, logout by POST |

## Known limitations

1. **Prices, flight times and weather are illustrative estimates**, not live data. Weather is the destination's typical weather for the three-month period containing the trip's start date; a trip crossing two periods uses the first.
2. **Per-member breakdowns are recalculated** from the current catalog. If an administrator edits a destination after a trip is decided, its breakdown could change; the saved Group Match and the decision do not.
3. **No notifications.** Members aren't told when they are removed, when recommendations are ready or when a decision is made; they see changes the next time they open the trip.
4. **Members can't leave a trip themselves.** Only the organizer can remove a member (agreed scope).
5. **Budget privacy is partial in small groups.** Budget figures are hidden until 3 members have submitted, but with 3 members the lowest and average budgets still narrow down the others' budgets. No budget is ever shown next to a name.
6. **Custom error pages only appear with `DEBUG=False`.** In development (`DEBUG=True`) Django shows its technical pages instead.
7. **The 8-member limit relies on a row lock** (`select_for_update`). SQLite ignores row locks, but it only allows one write at a time, so the limit still holds for this local setup.
8. **User-entered text isn't translated.** The interface and catalog are available in English and Arabic, but trip names and usernames appear exactly as typed in both versions.

# Wajha — Demo Script

This script follows the presentation order in the capstone guide. It uses the fictitious demo data, so the scores below are fixed and match `docs/verification.md`.

## Before the demo (2 minutes)

```bash
python manage.py load_demo_data     # resets the demo trips to their starting state
python manage.py runserver
```

- Open two browser windows: a normal window logged in as **ammar** (the organizer) and a private window logged in as **faisal** (a member).
- The password for every demo account is `wajha-demo-2026`.
- Optional, to show the custom error pages: run with `DJANGO_DEBUG=False` in `.env` and start the server with `python manage.py runserver --insecure`, so Django still serves static files.
- After rehearsing, run `load_demo_data` again to restore the starting state.

## 1. Users, problem and evidence (about 1 minute)

- **Users:** groups of 2–8 friends in Saudi Arabia planning an international leisure trip.
- **Problem:** everyone has a different budget, maximum flight time, weather preference and interests, so "where should we go?" becomes a long WhatsApp thread that often ends without a decision.
- **Evidence (survey of 58 people, `docs/market.md`):**
  - Of the 38 who travelled abroad with friends, **45% took a week or more** to agree and **37% had someone drop out or end up unhappy**.
  - **Budget is the #1 reason** to rule out a destination (83%). 29% would rather not share their exact budget.
  - Likelihood of using Wajha: **4.32 / 5 among 18–35 year olds** (3.71 overall).
  - Respondents asked for **a vote** and **"a time that suits everyone"**, and both are now in the product.
  - **Say honestly:** the sample is mostly over 35 and from Jeddah/Makkah, flight length mattered less than expected (12%), no interviews yet, and booking intent (47% yes) is still an assumption.

## 2. Value and the main workflow (about 4 minutes)

Logged in as **ammar**:

1. **My Trips.** Five trips in different states. Click the **Planning / Decided / Cancelled** tabs (filtering; the counts come from one aggregate query).
2. Open **Winter Getaway** (Riyadh, 14–18 Jan 2027, 4 nights).
   - The **readiness bar** shows 4 of 4 ready. Each friend submitted their preferences privately.
   - Point out the **invite code**: this is how friends joined.
3. Click **Generate recommendations** (if they are already generated, click **View recommendations**).
   - **Tbilisi, 88% Group Match**, is the top pick. Then Sarajevo, Cairo, Trabzon and Baku.
   - Open **"Didn't fit everyone (7)"**: Dubai is "Over budget for 2 members", with no names, so nobody is embarrassed.
4. Click **See why it fits**:
   - The checklist: fits everyone's budget (≈ 3,200 SAR), direct 3.5 h flight, interests match 4 of 4 members, typically cold in January.
   - **Member compatibility:** Khalid is lowest at 80%. Explain the fairness rule: *Group Match = 70% of the average + 30% of the lowest member, so one unhappy friend pulls the score down instead of being averaged away.*
   - Back on the recommendations page, scroll to **Group vote**: 3 of 4 members voted and Tbilisi is leading. Vote as ammar to show the counts change. Only totals are shown, never who voted for what; the organizer still decides.
5. Click **Choose Tbilisi** → read the confirmation → confirm.
   - The **boarding pass** shows RUH → Tbilisi, dates, 4 travelers, 88% Group Match. The trip is now **Decided** and locked.
6. In **faisal's** window, refresh the trip. He sees the same decision but has no organizer actions.

**Optional: shared dates (Spring Break).** Open **Share your dates** from the Trip Room. Everyone has added their free dates; the current dates (25–30 Mar) suit 2 of 3, and the best suggestion is **27 Mar – 1 Apr, everyone free**. As organizer, click **Use these dates** → confirm. The trip keeps its 5 nights. The suggestion comes from a pure function (`suggest_windows()` in `trips/services/dates.py`) that can be checked by hand.

## 3. One validation or failure case (about 1 minute)

Pick one or two:
- **Weekend on a Budget → View recommendations:** "No destination fits everyone". The reasons show which limits block each destination, e.g. "Cairo ≈ 2,150 SAR — Over budget for 2 members".
- **Join trip** with `WJ-ZZZZZ`: "No trip uses that code."
- **Spring Break → Add your preferences** (as khalid) with a budget of `0`: "Budget must be at least 500 SAR."
- As **faisal**, open `/trips/<winter id>/edit/`: the 403 page "Only the organizer can do that". Permissions are checked on the server, not just by hiding buttons.

## 4. The report: aggregation and annotation (about 1 minute)

- **Trip Room → Group summary** (Winter Getaway):
  - **Group budget limit 3,800 SAR** (`Min`): no destination can cost more for everyone to go.
  - **Average budget 4,325 SAR** (`Avg`).
  - **Shortest max flight 5 h** (`Min`): the longest flight everyone accepts.
  - **Top interests** (annotation): Food 3, Nature 2.
- **The decision it supports:** the organizer sees the group's real limits and priorities before choosing, instead of guessing from chat messages.
- **My Trips cards:** "4 of 4 ready" / "2 of 3 ready" are annotated per trip with `Count(..., distinct=True)`.
- **Privacy:** in Spring Break only 2 members have submitted, so the budget figures are hidden.

## 5. Key relationships and one technical decision (about 2 minutes)

Show `docs/erd.md`.
- **Preference belongs to TripMember, not User:** the same person can have different budgets for different trips.
- **RouteProfile holds flight data per origin-destination pair:** Riyadh → Baku is direct, Jeddah → Baku is not.
- **DestinationClimate holds weather per three-month period**, because weather depends on the trip's dates.

**Technical decision to explain (choose one):**
- The matching engine is **deterministic, pure Python with no database access** (`trips/services/matching.py`), so every score can be calculated by hand and unit-tested. It isn't AI. See the hand calculation in `docs/verification.md`.
- **Hard constraints plus the fairness formula** instead of a plain average.
- `distinct=True` on counts across two one-to-many joins. Without it, 4 members × 5 recommendations would be counted as 20 and 20.

## 6. Market potential, limitations and next step (about 1 minute)

- **Adoption:** free for groups. The organizer shares one code in the group chat.
- **Revenue (assumption to validate):** affiliate links for flights, hotels and activities once a destination is decided; a premium tier for larger groups or detailed planning.
- **Limitations:** illustrative prices and weather, no notifications, members can't leave on their own. See `docs/verification.md`.
- **Next practical improvement:** after "Decide" comes "Plan". Link the decided trip to live flight and hotel searches (affiliate), and notify members when a decision is made.

---

## Individual technical discussion: quick reference

**Trace a request: My Trips**
1. URL `/trips/` → `trips/urls.py` (`name="my_trips"`, namespace `trips`)
2. View `trips/views.py` → `my_trips()` (line 65)
3. ORM, in this order:
   - a subquery of the user's memberships (relationship query)
   - `aggregate()` per-status counts
   - `filter(status=...)`
   - `annotate(member_count, ready_count)` with `distinct=True`
   - `order_by("-created_at")`
4. Template `templates/trips/my_trips.html`, which uses the shared partials (`_status_badge.html`, `_empty_state.html`)

**Explain a constraint**
- `trip_status_matches_selected_destination` in `trips/models.py` (line 91): PLANNING → no destination, DECIDED → destination required, CANCELLED → either. Finalizing sets both together in `finalize_trip()` (`trips/services/trip_actions.py`, line 110).

**Show a calculation**
- `calculate_member_match()` and `combine_member_scores()` in `trips/services/matching.py` (lines 166 and 184), with the worked Tbilisi example in `docs/verification.md`.

**Show a validation rule**
- `TripForm.clean()` (end date after start) and `PreferenceForm.clean_max_flight_hours()` (half hours) in `trips/forms.py`.
- Server-side permission checks: `get_organizer_trip_or_403()` in `trips/permissions.py`.

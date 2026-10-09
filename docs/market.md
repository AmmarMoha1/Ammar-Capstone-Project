# Wajha — Market Validation

The capstone guide asks us to **separate evidence from assumptions**. This document lists the assumptions, the survey evidence collected to test them, what the evidence supports or contradicts, and what remains an assumption.

## Problem statement

Groups of friends in Saudi Arabia planning an international leisure trip struggle to agree on a destination. Each person has a different budget, maximum flight time, weather preference and set of interests, and the discussion usually happens in a long, unstructured group chat.

## Assumptions (tested below)

| # | Assumption | How we tested it |
|---|---|---|
| A1 | Groups of friends often take a long time, or fail, to agree on a destination | Survey Q4–Q6 |
| A2 | Budget and flight duration are the most common reasons a destination is rejected | Survey Q7 |
| A3 | People don't always share their real budget openly in the group chat | Survey Q8 |
| A4 | People would use a tool that collects everyone's constraints and ranks destinations | Survey Q9, Q10, Q12 |
| A5 | Users would click through to book flights or hotels from a decided trip (affiliate revenue) | Survey Q11 |

## Evidence: survey

**Method.** An anonymous online form in Arabic ("وجهة | Wajha - استبيان اختيار وجهة السفر"), shared in personal networks on 9 October 2026. **58 responses.** No names, emails or contact details were collected. The raw responses are in [survey/wajha-survey-responses.csv](survey/wajha-survey-responses.csv).

Questions (translated from Arabic):
1. Age range
2. City you usually travel from
3. International trips with friends in the last 3 years
4. How was the destination of your last trip with friends chosen? (group chat discussion / agreed straight away / vote / one person decided / other)
5. How long did it take to agree? (same day / a few days / a week or more / never agreed)
6. Has a friend ever dropped out or been unhappy with the chosen destination? If yes, why?
7. What could make you rule out a destination? (several answers allowed)
8. Are you comfortable sharing your exact budget with friends in the group?
9. How likely are you to use an app with this idea? (1–5)
10. What would make you trust the app's recommendations? (several answers allowed)
11. After agreeing on a destination, would you use links in the app to book flights or hotels?
12. What would you most like to have to make agreeing with friends easier? (open answer)

### Who answered

| | Result (58 responses) |
|---|---|
| Age | Over 35: 33 (57%) · 25–30: 11 (19%) · 22–24: 6 (10%) · 18–21: 6 (10%) · 31–35: 2 (3%) |
| Travels from | Jeddah 35 (60%) · Makkah 18 (31%) · Makkah or Jeddah 3 · Riyadh 1 · outside Saudi Arabia 1 |
| Trips with friends in 3 years | None: 20 (34%) · one: 14 (24%) · 2–3: 14 (24%) · 4–5: 7 (12%) · 6+: 3 (5%) |

**38 respondents** had travelled abroad with friends in the last three years. Q4–Q6 describe a real past trip only for them, so those questions are reported for these 38.

### Results

| Question | Result | Base |
|---|---|---|
| Q4 How the last destination was chosen | Group chat discussion 16 (42%) · agreed straight away 11 (29%) · vote 8 (21%) · one person decided 2 (5%) · other 1 (3%) | 38 who travelled |
| Q5 Time to agree | A week or more 17 (45%) · a few days 13 (34%) · same day 6 (16%) · never agreed 2 (5%) | 38 who travelled |
| Q6 Someone dropped out or was unhappy | Yes 14 (37%) · no 22 (58%) · not sure 2 (5%) | 38 who travelled |
| Q6 Reasons given (open answers, all respondents) | Different interests 5 · budget or money 4 · emergencies 2 · visa 1 · no leave left 1 · other or unclear 3 | 16 answers |
| Q7 Reasons to rule out a destination | Budget and cost **48 (83%)** · safety 26 (45%) · weather 20 (34%) · activities and interests 17 (29%) · visa requirements 14 (24%) · flight duration **7 (12%)** · no direct flight 6 (10%) · other 4 (7%) | 58 (multiple answers) |
| Q8 Comfortable sharing exact budget | Yes 41 (71%) · prefer not to share my exact budget 15 (26%) · no 2 (3%) | 58 |
| Q9 Likelihood of using the app (1–5) | **Average 3.71**; 4 or 5: 33 (57%) · 3: 17 (29%) · 1 or 2: 8 (14%) | 58 |
| Q9 Ages 18–35 only (the target age) | **Average 4.32**; 4 or 5: 19 of 25 (76%) | 25 |
| Q10 What builds trust | Clear prices and costs 41 (71%) · up-to-date information 31 (53%) · traveller reviews 31 (53%) · comparing destinations 26 (45%) · considering everyone's budget and preferences 24 (41%) · showing why each destination is recommended 17 (29%) | 58 (multiple answers) |
| Q11 Would book through links in the app | Yes 27 (47%) · maybe 29 (50%) · no 2 (3%) | 58 |

### What people asked for (Q12, open answers)

46 respondents wrote an answer. The most common themes, with representative quotes (translated). One answer can fall under more than one theme:

| Theme | Count | Example answers | Wajha today |
|---|---|---|---|
| Budget, cost or money | 16 | "Budget", "Money", "Competitive prices" | Budget is a hard limit for every member; per-person cost shown on every destination |
| A vote between friends | 3 | "A vote on the possible destinations", "A voting box" | **Group vote** on the top 3 recommendations |
| A list that fits everyone's budget and preferences | 2 | "A list of suitable destinations based on each person's budget and preference", "Fits our interests" | The core feature: private preferences and a fairness-ranked list |
| Agreeing on dates | 1 | "Choosing a travel time that suits everyone" | **Shared dates** with suggested windows |
| Activities, places and reviews | 4 | "Show all activities and their ratings", "Previous travellers' experience" | Not yet: interests are matched, but activities and reviews aren't shown |
| Clear plan and details | 6 | "A clear, well-studied plan", "Clear accommodation", "A very detailed explanation of the destination" | Partly: an explanation page per destination; no itinerary or accommodation |
| Travelling with family, not only friends | 2 | "Open it to travelling with family or brothers" | Works for any group, but the wording targets friends |
| Payment and packages | 3 | "Tabby and Tamara", "Link the budget to direct bank debit", "Ready packages for friends within the budget" | Not in scope (future affiliate or package model) |

### Interviews

**Not conducted.** The plan was 3–5 short interviews with organizers of a recent group trip. The open answers above are the only qualitative evidence, so statements about *why* people behave this way remain partly assumptions.

## What the evidence shows

| # | Assumption | Verdict | Evidence |
|---|---|---|---|
| A1 | Agreeing takes long or fails | **Supported** | Of 38 who travelled with friends, 45% needed a week or more and 5% never agreed; 79% needed several days or more. 37% had a friend drop out or end up unhappy, most often because of different interests or budget. |
| A2 | Budget and flight duration are the main reasons for rejection | **Partly supported** | Budget is by far the first reason (83%). **Flight duration (12%) and direct flights (10%) are not**: safety (45%), weather (34%), interests (29%) and visa requirements (24%) matter more. |
| A3 | People don't always share their real budget | **Partly supported** | Most (71%) say they're comfortable sharing, but 29% (17 of 58) prefer not to share their exact budget or aren't comfortable. Private budgets matter for a significant minority rather than for everyone. |
| A4 | People would use such a tool | **Supported, strongest in the target age** | Average 3.71 overall, 57% rated 4–5. Among 18–35 year olds the average is 4.32 and 76% rated 4–5. Voting and date-agreement requests in Q12 match features now built. |
| A5 | Users would book through the app | **Promising, unproven** | 47% yes and 50% maybe; only 3% no. Intent in a survey isn't behaviour; affiliate revenue stays an assumption until real click-throughs are measured. |

**Limitations of this evidence.**
- **The sample doesn't match the target audience.** 57% are over 35, and almost everyone travels from Jeddah or Makkah, while the target is 18–35 year olds and the demo data focuses on Riyadh.
- **It's a convenience sample** from personal networks, so it may be more positive than the general public.
- **A third had not travelled with friends recently**, so their answers describe expectations rather than experience.
- **No interviews were done.**

## What changed in the product because of the evidence

- **Group vote added.** Respondents asked for a voting box. Members now vote on the top 3, while the fairness ranking still protects everyone's limits.
- **Shared dates added.** Agreeing on *when* is part of agreeing on *where*. Members share free dates and Wajha suggests windows that suit the most people.
- **Clear costs and reasons are kept front and centre.** The top trust factors were clear prices (71%) and up-to-date information (53%). Every destination shows its per-person cost and the reasons it fits. The illustrative prices are labelled clearly, and live prices are the next improvement.
- **Next improvements the evidence points to:**
  - **Visa requirements for Saudi passport holders and a safety indicator.** These were the 2nd and 5th most common reasons to rule out a destination (safety 45%, visa 24%).
  - **Activities with traveller reviews per destination.** This was asked for in the open answers, and reviews were a top-3 trust factor (53%).
  - **Wording that welcomes family groups as well as friends.**
- **Flight duration stays in the model, but it has a small weight.** It counts for 15 of 100 points, and direct flights for 5. The survey shows these are secondary reasons for most people but still hard limits for some.

## Existing tools and manual processes

This is a general comparison of what each tool is designed for. Check current features before presenting.

| Option | What it does well | Why it doesn't solve this problem |
|---|---|---|
| Group chat discussion (e.g. WhatsApp) | Everyone is already there; free. **42% of respondents decided this way** | Unstructured; budgets stay unspoken; no way to weigh everyone's constraints |
| Group chat polls | Quick vote between a few options (21% decided by vote) | Someone must choose the options first; a majority vote can ignore one member's hard limits |
| Flight "explore anywhere" searches (e.g. Skyscanner) | Find cheap destinations from one origin | Designed around one traveller's budget, not several people's constraints and interests |
| Itinerary planners (e.g. Wanderlog) | Plan a trip once the destination is known | Start after the decision Wajha helps make |
| Expense-splitting apps (e.g. Splitwise) | Share costs during and after a trip | Solve a later stage of the trip |

**Why choose Wajha:** each member's constraints are collected privately, destinations that break anyone's limit are excluded, and the remaining options are ranked with a fairness rule. Then the group votes and agrees on dates in the same place. Existing tools leave this whole step to a group chat.

## Adoption and revenue model

- **Adoption (assumption):** free for groups. One organizer creates a trip and shares a code in the existing group chat; friends join in under a minute. Each trip brings in new users.
- **Revenue (assumption, with early evidence):** affiliate commissions on flight, hotel and activity bookings made after a destination is decided. 47% said they would book through links in the app and 50% maybe (Q11). Later, a premium tier or ready-made packages within the group's budget (requested in Q12).
- **Scope today:** the capstone delivers the decision step: preferences, ranking, vote, dates and the final choice. Booking and payments are future work.

## Conclusion

- **Supported.** The problem is real for people who travel with friends: agreeing usually takes days or weeks, and a third have had someone drop out or end up unhappy. Budget is the dominant constraint. Interest in the idea is high in the target age group (4.32 / 5).
- **Contradicted.** Flight length isn't a main reason to reject a destination. Safety, weather and visa requirements matter more, so they are the next factors to add.
- **Still assumptions.** That people would pay through or book through Wajha, and that the results hold for a younger, Riyadh-based audience. The next step is 3–5 interviews with 18–30 year old organizers in Riyadh, plus measuring real booking-link clicks.

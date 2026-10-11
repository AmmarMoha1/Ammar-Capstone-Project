# Wajha — Market Validation

The capstone guide asks us to **separate evidence from assumptions**. This document lists the assumptions, the survey and interview evidence collected to test them, what the evidence supports or contradicts, and what remains an assumption.

## Problem statement

Groups of friends in Saudi Arabia planning an international leisure trip struggle to agree on a destination. Each person has a different budget, maximum flight time, weather preference and set of interests, and the discussion usually happens in a long, unstructured group chat.

## Assumptions (tested below)

| # | Assumption | How we tested it |
|---|---|---|
| A1 | Groups of friends often take a long time, or fail, to agree on a destination | Survey Q4–Q6, interviews |
| A2 | Budget and flight duration are the most common reasons a destination is rejected | Survey Q7 |
| A3 | People don't always share their real budget openly in the group chat | Survey Q8 |
| A4 | People would use a tool that collects everyone's constraints and ranks destinations | Survey Q9, Q10, Q12, interviews |
| A5 | Users would click through to book flights or hotels from a decided trip (affiliate revenue) | Survey Q11 |

## Evidence: survey

**Method.** An anonymous online form in Arabic ("وجهة | Wajha - استبيان اختيار وجهة السفر"), shared in personal networks from 9 to 11 October 2026. **108 responses.** No names, emails or contact details were collected. The raw responses are in [survey/wajha-survey-responses.csv](survey/wajha-survey-responses.csv).

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

| | Result (108 responses) |
|---|---|
| Age | Over 35: 73 (68%) · 25–30: 15 (14%) · 18–21: 9 (8%) · 22–24: 8 (7%) · 31–35: 3 (3%) |
| Travels from | Jeddah 61 (56%) · Makkah 36 (33%) · Makkah or Jeddah 5 · Riyadh 2 · Taif 1 · outside Saudi Arabia 3 |
| Trips with friends in 3 years | None: 40 (37%) · one: 20 (19%) · 2–3: 28 (26%) · 4–5: 10 (9%) · 6+: 10 (9%) |

**68 respondents** had travelled abroad with friends in the last three years. Q4–Q6 describe a real past trip only for them, so those questions are reported for these 68.

### Results

| Question | Result | Base |
|---|---|---|
| Q4 How the last destination was chosen | Group chat discussion 22 (32%) · agreed straight away 20 (29%) · vote 15 (22%) · other 6 (9%) · one person decided 5 (7%) | 68 who travelled |
| Q5 Time to agree | A week or more 27 (40%) · a few days 26 (38%) · same day 12 (18%) · never agreed 3 (4%) | 68 who travelled |
| Q6 Someone dropped out or was unhappy | Yes 22 (32%) · no 39 (57%) · not sure 7 (10%) | 68 who travelled |
| Q6 Reasons given (open answers, all respondents) | Different interests 10 · budget or money 6 · emergencies 3 · different opinions 2 · visa 1 · no leave left 1 · family commitments 1 · other or unclear 3 | 27 answers |
| Q7 Reasons to rule out a destination | Budget and cost **76 (70%)** · safety 41 (38%) · weather 32 (30%) · visa requirements 25 (23%) · activities and interests 22 (20%) · flight duration **14 (13%)** · other 12 (11%) · no direct flight 11 (10%) | 108 (multiple answers) |
| Q8 Comfortable sharing exact budget | Yes 75 (69%) · prefer not to share my exact budget 29 (27%) · no 4 (4%) | 108 |
| Q9 Likelihood of using the app (1–5) | **Average 3.54**; 4 or 5: 54 (50%) · 3: 32 (30%) · 1 or 2: 22 (20%) | 108 |
| Q9 Ages 18–35 only (the target age) | **Average 4.03**; 4 or 5: 23 of 35 (66%) | 35 |
| Q10 What builds trust | Clear prices and costs 72 (67%) · traveller reviews 48 (44%) · up-to-date information 45 (42%) · comparing destinations 45 (42%) · considering everyone's budget and preferences 41 (38%) · showing why each destination is recommended 26 (24%) | 108 (multiple answers) |
| Q11 Would book through links in the app | Yes 57 (53%) · maybe 44 (41%) · no 7 (6%) | 108 |

### What people asked for (Q12, open answers)

79 respondents wrote an answer. The most common themes, with representative quotes (translated). One answer can fall under more than one theme:

| Theme | Count | Example answers | Wajha today |
|---|---|---|---|
| Budget, cost or money | 28 | "Budget", "Competitive prices", "A clear budget" | Budget is a hard limit for every member; per-person cost shown on every destination |
| A clear plan and full information | 8 | "A well-studied plan", "Clear accommodation", "Complete information about where we travel" | Partly: an explanation page per destination; no itinerary or accommodation |
| Activities, places and reviews | 6 | "Show all activities and their ratings", "A schedule per city of activities, landmarks and restaurants" | Not yet: interests are matched, but activities and reviews aren't shown |
| Transparency and honesty | 6 | "Clarity and transparency", "Credibility at every stage of the app" | Every ranking explains itself; illustrative prices are labelled |
| A vote between friends | 3 | "A vote on the possible destinations", "A voting box" | **Group vote** on the top 3 recommendations |
| Travelling with family, not only friends | 3 | "Open it to travelling with family or brothers" | Works for any group, but the wording targets friends |
| Payment and packages | 3 | "Tabby and Tamara", "Ready packages for friends within the budget" | Not in scope (future affiliate or package model) |
| A list that fits everyone's budget and preferences | 2 | "A list of suitable destinations based on each person's budget and preference" | The core feature: private preferences and a fairness-ranked list |
| Agreeing on dates | 1 | "Choosing a travel time that suits everyone" | **Shared dates** with suggested windows |

## Evidence: interviews

**Method.** Three short interviews in October 2026 with people who had planned a trip with friends, using the prompts below. The third prompt was asked after showing them Wajha. The interviewer combined the three conversations into one summary, so the points below aren't attributed to individual interviewees.

Prompts:
1. "Walk me through how your last group trip destination was chosen."
2. "What was the hardest part?"
3. After seeing Wajha: "Would this have helped? What's missing?"

| Prompt | What they said (summarised and translated) | What it supports or contradicts |
|---|---|---|
| How the destination was chosen | Not quick: "after a long discussion and checking". Each person proposed a country with its pros, cons, risks and opportunities. After **about a week** of discussion they chose a country that suited everyone. | **Supports A1**: about a week to agree. It also shows groups already weigh every member's constraints by hand, which is what Wajha automates. |
| Hardest part | Choosing **when** to travel: "which month? how many days? from when to when?" It had to fit ticket prices, when salaries are paid, everyone's leave and the airline. "Not impossible, but tiring to arrange." | **Supports the shared-dates feature.** It also shows that dates and prices interact (salary timing, ticket price by date), which Wajha doesn't model yet. |
| Would it help, what's missing | "Yes, it would have helped a lot": it saves time and effort. Wanted: finding **activities that fit the budget**, the distance between accommodation and each activity, a **schedule** of activities that everyone can refer to, several schedule options to choose from, and **saving it to use offline**. | **Supports A4.** It points to the next stage after the decision (activities and itinerary), which is outside the current scope. |

## What the evidence shows

| # | Assumption | Verdict | Evidence |
|---|---|---|---|
| A1 | Agreeing takes long or fails | **Supported** | Of 68 who travelled with friends, 40% needed a week or more and 4% never agreed; 82% needed several days or more or never agreed. 32% had a friend drop out or end up unhappy, most often because of different interests or budget. The interviews describe about a week of discussion. |
| A2 | Budget and flight duration are the main reasons for rejection | **Partly supported** | Budget is by far the first reason (70%). **Flight duration (13%) and direct flights (10%) are not**: safety (38%), weather (30%) and visa requirements (23%) matter more. |
| A3 | People don't always share their real budget | **Partly supported** | Most (69%) say they're comfortable sharing, but 31% (33 of 108) prefer not to share their exact budget or aren't comfortable. Private budgets matter for a significant minority rather than for everyone. |
| A4 | People would use such a tool | **Supported, strongest in the target age** | Average 3.54 overall and 50% rated 4–5. Among 18–35 year olds the average is 4.03 and 66% rated 4–5. All interviewees said it would have helped. Voting and date-agreement requests match features now built. |
| A5 | Users would book through the app | **Promising, unproven** | 53% yes and 41% maybe; only 6% no. Intent in a survey isn't behaviour; affiliate revenue stays an assumption until real click-throughs are measured. |

**Limitations of this evidence.**
- **The sample doesn't match the target audience.** 68% are over 35, and almost everyone travels from Jeddah or Makkah, while the target is 18–35 year olds and the demo data focuses on Riyadh.
- **It's a convenience sample** from personal networks, so it may be more positive than the general public.
- **37% had not travelled with friends recently**, so their answers describe expectations rather than experience.
- **Only three interviews**, recorded as one combined summary.

## What changed in the product because of the evidence

- **Group vote added.** Respondents asked for a voting box. Members now vote on the top 3, while the fairness ranking still protects everyone's limits.
- **Shared dates added.** Agreeing on *when* is part of agreeing on *where*. The interviews named timing as the hardest part, so members now share free dates and Wajha suggests windows that suit the most people.
- **Clear costs and reasons are kept front and centre.** The top trust factor was clear prices (67%), and 6 open answers asked for transparency. Every destination shows its per-person cost and the reasons it fits, and the illustrative prices are labelled clearly. Live prices are the next improvement.
- **Next improvements the evidence points to:**
  - **Visa requirements for Saudi passport holders and a safety indicator.** These were the 4th and 2nd most common reasons to rule out a destination (visa 23%, safety 38%).
  - **Activities with traveller reviews, then a shared itinerary that can be saved offline.** These were asked for in the open answers and the interviews, and reviews were the 2nd trust factor (44%).
  - **Dates that take ticket prices into account,** following the interviews.
  - **Wording that welcomes family groups as well as friends.**
- **Flight duration stays in the model, but it has a small weight.** It counts for 15 of 100 points, and direct flights for 5. The survey shows these are secondary reasons for most people but still hard limits for some.

## Existing tools and manual processes

This is a general comparison of what each tool is designed for. Check current features before presenting.

| Option | What it does well | Why it doesn't solve this problem |
|---|---|---|
| Group chat discussion (e.g. WhatsApp) | Everyone is already there; free. **The most common way respondents decided (32%)** | Unstructured; budgets stay unspoken; no way to weigh everyone's constraints |
| Group chat polls | Quick vote between a few options (22% decided by vote) | Someone must choose the options first; a majority vote can ignore one member's hard limits |
| Flight "explore anywhere" searches (e.g. Skyscanner) | Find cheap destinations from one origin | Designed around one traveller's budget, not several people's constraints and interests |
| Itinerary planners (e.g. Wanderlog) | Plan a trip once the destination is known | Start after the decision Wajha helps make |
| Expense-splitting apps (e.g. Splitwise) | Share costs during and after a trip | Solve a later stage of the trip |

**Why choose Wajha:** each member's constraints are collected privately, destinations that break anyone's limit are excluded, and the remaining options are ranked with a fairness rule. Then the group votes and agrees on dates in the same place. Existing tools leave this whole step to a group chat.

## Adoption and revenue model

- **Adoption (assumption):** free for groups. One organizer creates a trip and shares a code in the existing group chat; friends join in under a minute. Each trip brings in new users.
- **Revenue (assumption, with early evidence):** affiliate commissions on flight, hotel and activity bookings made after a destination is decided. 53% said they would book through links in the app and 41% maybe (Q11). Later, a premium tier or ready-made packages within the group's budget (requested in Q12).
- **Scope today:** the capstone delivers the decision step: preferences, ranking, vote, dates and the final choice. Booking, payments and itineraries are future work.

## Conclusion

- **Supported.** The problem is real for people who travel with friends:
  - agreeing usually takes days or weeks, and a third have had someone drop out or end up unhappy;
  - budget is the dominant constraint;
  - interest in the idea is high in the target age group (4.03 / 5);
  - the interviewees said it would have helped a lot.
- **Contradicted.** Flight length isn't a main reason to reject a destination. Safety, weather and visa requirements matter more, so they are the next factors to add.
- **Still assumptions.** That people would book through Wajha, and that the results hold for a younger, Riyadh-based audience. The next steps are more interviews with 18–30 year old organizers in Riyadh, and measuring real booking-link clicks.

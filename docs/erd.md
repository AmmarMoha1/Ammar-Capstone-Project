# Wajha — Entity Relationship Diagram

This diagram matches the implemented models and migrations. The entity blocks were generated from the Django models, not drawn by hand.

GitHub and VS Code render the diagram below. Elsewhere, paste the code block into <https://mermaid.live>.

```mermaid
erDiagram
    USER ||--o{ TRIP : "organizes"
    USER ||--o{ TRIPMEMBER : "is"
    TRIP ||--|{ TRIPMEMBER : "has (organizer always included)"
    TRIPMEMBER ||--o| PREFERENCE : "submits"
    PREFERENCE ||--|{ PREFERENCE_INTERESTS : "chooses"
    INTEREST ||--o{ PREFERENCE_INTERESTS : "chosen in"
    ORIGINCITY ||--o{ TRIP : "departure city of"
    DESTINATION |o--o{ TRIP : "selected for"
    ORIGINCITY ||--o{ ROUTEPROFILE : "route from"
    DESTINATION ||--o{ ROUTEPROFILE : "route to"
    DESTINATION ||--|{ DESTINATIONCLIMATE : "weather per period"
    DESTINATION ||--o{ DESTINATION_INTERESTS : "offers"
    INTEREST ||--o{ DESTINATION_INTERESTS : "offered by"
    TRIP ||--o{ RECOMMENDATION : "ranked results"
    DESTINATION ||--o{ RECOMMENDATION : "recommended as"

    USER {
        int id PK
        varchar(150) username UK
        varchar(254) email
        varchar(128) password "hashed by Django"
    }
    ORIGINCITY {
        bigint id PK
        varchar(100) name UK
        varchar(3) airport_code UK
        bool is_active
    }
    DESTINATION {
        bigint id PK
        varchar(100) city "UK with country"
        varchar(100) country "UK with city"
        varchar(2) country_code
        int estimated_daily_cost "SAR per person per day"
        text description
        bool is_active
    }
    DESTINATIONCLIMATE {
        bigint id PK
        bigint destination_id FK "UK with period"
        smallint period "1 Jan-Mar ... 4 Oct-Dec"
        varchar(4) weather_type "COLD MILD WARM HOT"
    }
    INTEREST {
        bigint id PK
        varchar(50) name UK
    }
    DESTINATION_INTERESTS {
        bigint id PK
        bigint destination_id FK
        bigint interest_id FK
    }
    ROUTEPROFILE {
        bigint id PK
        bigint origin_city_id FK "UK with destination"
        bigint destination_id FK "UK with origin"
        decimal(4,1) flight_duration_hours
        bool direct_available
        int estimated_flight_cost "return, SAR"
    }
    TRIP {
        bigint id PK
        bigint owner_id FK
        bigint departure_city_id FK
        bigint selected_destination_id FK "nullable"
        varchar(100) name
        date start_date
        date end_date
        varchar(8) invite_code UK
        varchar(10) status "PLANNING DECIDED CANCELLED"
        datetime created_at
        datetime updated_at
    }
    TRIPMEMBER {
        bigint id PK
        bigint trip_id FK "UK with user"
        bigint user_id FK "UK with trip"
        datetime joined_at
    }
    PREFERENCE {
        bigint id PK
        bigint trip_member_id FK,UK
        int max_budget "SAR, whole trip"
        decimal(3,1) max_flight_hours
        varchar(4) weather_preference "or ANY"
        bool direct_only
        datetime created_at
        datetime updated_at
    }
    PREFERENCE_INTERESTS {
        bigint id PK
        bigint preference_id FK
        bigint interest_id FK
    }
    RECOMMENDATION {
        bigint id PK
        bigint trip_id FK "UK with destination, UK with rank"
        bigint destination_id FK
        smallint rank
        decimal(4,1) score
        decimal(4,1) lowest_member_score
        int estimated_total_cost "SAR per person"
        datetime generated_at
    }
```

`DESTINATION_INTERESTS` (`destinations_destination_interests`) and `PREFERENCE_INTERESTS` (`trips_preference_interests`) are the link tables Django creates for the two many-to-many fields. Each has a unique pair constraint.

## Relationships, cardinality and deletion behaviour

| Relationship | Cardinality and optionality | On delete | Why |
|---|---|---|---|
| User → Trip (owner) | One user organizes zero or more trips; every trip has exactly one organizer | PROTECT | A user who organizes trips can't be deleted by accident and take everyone's trips with them |
| Trip → TripMember | One trip has one or more members (the organizer is always one) | CASCADE | Memberships have no meaning without their trip |
| User → TripMember | One user has zero or more memberships | CASCADE | If an account is deleted, its memberships go with it |
| TripMember → Preference | One membership has zero or one preference | CASCADE | Removing a member removes their preferences for that trip |
| Preference ↔ Interest | Each preference has one or more interests (form rule); an interest can appear in many preferences | CASCADE on the link rows | |
| OriginCity → Trip | One city is the departure city of zero or more trips | PROTECT | Cities in use can't be deleted; retire them with `is_active` |
| Destination → Trip (selected) | A trip has zero or one selected destination | PROTECT | A decision can't silently lose its destination |
| OriginCity, Destination → RouteProfile | Each origin-destination pair has at most one route | CASCADE | Catalog data that belongs to the pair |
| Destination → DestinationClimate | Each destination has one row per period (four in the catalog) | CASCADE | Catalog data that belongs to the destination |
| Destination ↔ Interest | A destination offers zero or more interests | CASCADE on the link rows | |
| Trip → Recommendation | A trip has zero or more saved recommendations | CASCADE | Results belong to the trip |
| Destination → Recommendation | A destination appears in zero or more recommendations | PROTECT | Saved results can't lose their destination; retire destinations with `is_active` instead |

## Constraints protecting business rules

| Model | Constraint | Rule |
|---|---|---|
| Trip | `trip_end_after_start` | `end_date > start_date` |
| Trip | `trip_status_matches_selected_destination` | PLANNING → no destination; DECIDED → destination required; CANCELLED → either (a decided trip keeps its destination when cancelled) |
| Trip | unique `invite_code` | Every invite code identifies one trip |
| TripMember | `unique_trip_member` (trip, user) | A user can't join the same trip twice |
| Preference | one-to-one `trip_member` | One preference per member per trip |
| Preference | `preference_budget_positive`, `preference_flight_hours_positive` | Budget and flight hours greater than 0 (the form also enforces 500–100,000 SAR and 1–24 hours) |
| Recommendation | `unique_recommendation_destination`, `unique_recommendation_rank` | A destination appears once per trip, and each rank is used once |
| Recommendation | `recommendation_rank_positive`, `recommendation_score_range`, `recommendation_lowest_score_range` | Rank ≥ 1; scores between 0 and 100 |
| Destination | `unique_destination_city_country`, `destination_daily_cost_positive` | No duplicate cities; daily cost greater than 0 |
| DestinationClimate | `unique_climate_destination_period` | One weather value per destination per period |
| RouteProfile | `unique_route_origin_destination`, `route_flight_duration_positive`, `route_flight_cost_positive` | One route per pair; positive duration and fare |
| OriginCity, Interest | unique `airport_code`, `name` | No duplicates |

Rules that span several tables are enforced in the application and covered by tests:
- The organizer always has a TripMember row, because the trip and the membership are created in one transaction and the organizer can't be removed.
- At most 8 members per trip.
- Recommendations can only be generated when every member has submitted preferences.

## Where information belongs, and why

- **Preferences belong to TripMember, not User.** The same person can have a 4,000 SAR budget for one trip and 2,500 SAR for another.
- **TripMember is a model of its own rather than a plain many-to-many field.** A membership carries its own data (when the person joined, and their preference for that trip).
- **Flight data belongs to RouteProfile, not Destination.** Riyadh → Baku and Jeddah → Baku have different durations, fares and direct-flight availability.
- **Weather belongs to DestinationClimate, not Destination.** It depends on the time of year, and periods (not "winter/summer") work for both hemispheres. Four columns on Destination would be a repeating group.
- **Organizer role isn't stored on TripMember.** It's `Trip.owner`, so the two can never disagree.
- **Recommendation stores group-level results only.** Each member's breakdown is recalculated with the same deterministic function, which avoids duplicating data that can be derived.

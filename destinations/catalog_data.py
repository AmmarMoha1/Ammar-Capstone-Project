"""Illustrative demo catalog for Wajha.

All prices and durations are rough illustrative estimates for demonstration,
not live prices or schedules.

- daily_cost: SAR per person per day (accommodation, food, local transport)
- climate: weather for (Jan–Mar, Apr–Jun, Jul–Sep, Oct–Dec)
- routes: origin airport code -> (flight hours, direct available, return fare SAR)
"""

ORIGIN_CITIES = [
    ("Riyadh", "RUH"),
    ("Jeddah", "JED"),
    ("Dammam", "DMM"),
]

INTERESTS = ["Nature", "Food", "Culture", "Shopping", "Nightlife", "Beaches", "Adventure"]

DESTINATIONS = [
    {
        "city": "Cairo",
        "country": "Egypt",
        "country_code": "EG",
        "daily_cost": 350,
        "description": "Ancient wonders, lively markets and a famous food scene along the Nile.",
        "interests": ["Culture", "Food", "Shopping"],
        "climate": ("MILD", "HOT", "HOT", "WARM"),
        "routes": {"RUH": (2.5, True, 1100), "JED": (2.0, True, 900), "DMM": (3.0, True, 1300)},
    },
    {
        "city": "Baku",
        "country": "Azerbaijan",
        "country_code": "AZ",
        "daily_cost": 450,
        "description": "A Caspian capital mixing a medieval old city with modern skyline and great food.",
        "interests": ["Culture", "Food", "Nightlife"],
        "climate": ("COLD", "WARM", "HOT", "MILD"),
        "routes": {"RUH": (3.5, True, 1500), "JED": (6.0, False, 1900), "DMM": (3.0, True, 1400)},
    },
    {
        "city": "Tbilisi",
        "country": "Georgia",
        "country_code": "GE",
        "daily_cost": 400,
        "description": "Hillside old town, sulphur baths and easy day trips into the Caucasus mountains.",
        "interests": ["Nature", "Food", "Culture", "Adventure", "Nightlife"],
        "climate": ("COLD", "WARM", "HOT", "MILD"),
        "routes": {"RUH": (3.5, True, 1600), "JED": (4.5, True, 1800), "DMM": (5.5, False, 1900)},
    },
    {
        "city": "Dubai",
        "country": "United Arab Emirates",
        "country_code": "AE",
        "daily_cost": 900,
        "description": "Short-hop city break with malls, beaches, desert trips and dining.",
        "interests": ["Shopping", "Beaches", "Nightlife", "Food", "Adventure"],
        "climate": ("WARM", "HOT", "HOT", "WARM"),
        "routes": {"RUH": (2.0, True, 800), "JED": (2.5, True, 900), "DMM": (1.0, True, 600)},
    },
    {
        "city": "Istanbul",
        "country": "Türkiye",
        "country_code": "TR",
        "daily_cost": 650,
        "description": "Two continents, grand mosques, bazaars and one of the world's great food cities.",
        "interests": ["Culture", "Food", "Shopping", "Nightlife"],
        "climate": ("COLD", "WARM", "HOT", "MILD"),
        "routes": {"RUH": (5.0, True, 2000), "JED": (4.0, True, 1800), "DMM": (5.0, True, 2100)},
    },
    {
        "city": "Trabzon",
        "country": "Türkiye",
        "country_code": "TR",
        "daily_cost": 450,
        "description": "Green Black Sea highlands, mountain lakes and misty plateau villages.",
        "interests": ["Nature", "Adventure", "Food"],
        "climate": ("COLD", "MILD", "WARM", "MILD"),
        "routes": {"RUH": (4.5, True, 1900), "JED": (4.5, True, 1900), "DMM": (7.0, False, 2300)},
    },
    {
        "city": "Sarajevo",
        "country": "Bosnia and Herzegovina",
        "country_code": "BA",
        "daily_cost": 400,
        "description": "Ottoman and European heritage surrounded by forested mountains and rivers.",
        "interests": ["Nature", "Culture", "Food", "Adventure"],
        "climate": ("COLD", "MILD", "WARM", "COLD"),
        "routes": {"RUH": (5.0, True, 2200), "JED": (5.0, True, 2200), "DMM": (8.0, False, 2600)},
    },
    {
        "city": "Vienna",
        "country": "Austria",
        "country_code": "AT",
        "daily_cost": 1100,
        "description": "Imperial palaces, coffee houses and classical culture in a very walkable city.",
        "interests": ["Culture", "Food", "Shopping"],
        "climate": ("COLD", "MILD", "WARM", "COLD"),
        "routes": {"RUH": (6.0, True, 2800), "JED": (8.0, False, 3000), "DMM": (8.5, False, 3200)},
    },
    {
        "city": "Prague",
        "country": "Czechia",
        "country_code": "CZ",
        "daily_cost": 850,
        "description": "Fairytale old town, castle views and a lively evening atmosphere.",
        "interests": ["Culture", "Food", "Nightlife"],
        "climate": ("COLD", "MILD", "WARM", "COLD"),
        "routes": {"RUH": (6.0, True, 2700), "JED": (8.5, False, 3000), "DMM": (8.5, False, 3100)},
    },
    {
        "city": "Kuala Lumpur",
        "country": "Malaysia",
        "country_code": "MY",
        "daily_cost": 550,
        "description": "Street food, huge malls and rainforest escapes close to the city.",
        "interests": ["Food", "Shopping", "Nature", "Culture"],
        "climate": ("HOT", "HOT", "HOT", "HOT"),
        "routes": {"RUH": (8.0, True, 3000), "JED": (8.5, True, 2900), "DMM": (9.5, False, 3200)},
    },
    {
        "city": "Bali",
        "country": "Indonesia",
        "country_code": "ID",
        "daily_cost": 600,
        "description": "Rice terraces, temples, surf beaches and volcano sunrise hikes.",
        "interests": ["Beaches", "Nature", "Culture", "Adventure"],
        "climate": ("HOT", "WARM", "WARM", "HOT"),
        "routes": {"RUH": (13.0, False, 4200), "JED": (13.5, False, 4300), "DMM": (14.0, False, 4400)},
    },
    {
        "city": "Malé",
        "country": "Maldives",
        "country_code": "MV",
        "daily_cost": 1500,
        "description": "Island resorts, clear lagoons and some of the world's best snorkelling.",
        "interests": ["Beaches", "Nature", "Adventure"],
        "climate": ("HOT", "HOT", "HOT", "HOT"),
        "routes": {"RUH": (5.0, True, 2800), "JED": (8.0, False, 3200), "DMM": (6.5, False, 3100)},
    },
]

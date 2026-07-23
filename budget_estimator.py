import logging
import re
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

CURRENCY = "CNY"

DESTINATION_COST_MULTIPLIERS = {
    "东京": 1.35,
    "京都": 1.25,
    "上海": 1.15,
    "杭州": 1.0,
    "成都": 0.9,
    "tokyo": 1.35,
    "kyoto": 1.25,
    "osaka": 1.2,
    "shanghai": 1.15,
    "beijing": 1.1,
    "hangzhou": 1.0,
    "chengdu": 0.9,
    "xi'an": 0.9,
    "xian": 0.9,
    "guangzhou": 1.05,
    "shenzhen": 1.15,
}

TRAVELER_PROFILES = {
    "solo": {"people": 1, "rooms": 1, "transport_factor": 1.0, "label": "solo"},
    "couple": {"people": 2, "rooms": 1, "transport_factor": 1.8, "label": "couple"},
    "friends": {"people": 3, "rooms": 2, "transport_factor": 2.6, "label": "friends"},
    "family": {"people": 3, "rooms": 1, "transport_factor": 2.3, "label": "family"},
    "business": {"people": 1, "rooms": 1, "transport_factor": 1.1, "label": "business"},
    "senior": {"people": 2, "rooms": 1, "transport_factor": 1.7, "label": "senior"},
}

TRAVELER_ALIASES = {
    "solo": "solo",
    "single": "solo",
    "个人": "solo",
    "独自": "solo",
    "couple": "couple",
    "情侣": "couple",
    "夫妻": "couple",
    "friends": "friends",
    "friend": "friends",
    "朋友": "friends",
    "family": "family",
    "亲子": "family",
    "家庭": "family",
    "business": "business",
    "商务": "business",
    "senior": "senior",
    "老人": "senior",
    "长辈": "senior",
}

COST_PROFILES = {
    "economy": {
        "hotel_per_room_night": 280,
        "food_per_person_day": 95,
        "transport_per_person_day": 45,
        "poi_cost_factor": 0.75,
        "contingency_rate": 0.05,
    },
    "comfort": {
        "hotel_per_room_night": 520,
        "food_per_person_day": 180,
        "transport_per_person_day": 90,
        "poi_cost_factor": 1.0,
        "contingency_rate": 0.08,
    },
    "experience_first": {
        "hotel_per_room_night": 780,
        "food_per_person_day": 280,
        "transport_per_person_day": 140,
        "poi_cost_factor": 1.25,
        "contingency_rate": 0.1,
    },
}

CATEGORY_BASE_COSTS = {
    "landmark": 20,
    "city_walk": 0,
    "museum": 60,
    "history": 80,
    "culture": 80,
    "nature": 60,
    "food": 120,
    "shopping": 100,
    "nightlife": 180,
    "theme_park": 260,
    "experience": 220,
    "viewpoint": 120,
    "local_life": 40,
}

BUDGET_LEVEL_PER_PERSON_DAY = {
    "budget": 420,
    "economy": 420,
    "经济": 420,
    "mid-range": 760,
    "midrange": 760,
    "comfort": 760,
    "comfortable": 760,
    "舒适": 760,
    "premium": 1150,
    "luxury": 1500,
    "体验": 1150,
    "高端": 1500,
}


def normalize_traveler_type(traveler_type: Optional[str]) -> str:
    if not traveler_type:
        return "solo"

    value = str(traveler_type).strip().lower()
    for alias, normalized in TRAVELER_ALIASES.items():
        if alias in value:
            return normalized
    return "solo"


def get_traveler_profile(traveler_type: Optional[str]) -> Dict[str, Any]:
    normalized = normalize_traveler_type(traveler_type)
    return TRAVELER_PROFILES[normalized]


def get_destination_multiplier(destination: str) -> float:
    destination_key = (destination or "").lower()
    for keyword, multiplier in DESTINATION_COST_MULTIPLIERS.items():
        if keyword in destination_key:
            return multiplier
    return 1.0


def normalize_budget_constraint(
    budget: Optional[Any],
    days: int,
    traveler_type: Optional[str] = None,
) -> Optional[float]:
    """
    Converts either a numeric budget or a coarse budget label into a total
    trip budget. All values are local estimates in CNY and do not use APIs.
    """
    if budget is None or budget == "":
        return None

    if isinstance(budget, (int, float)):
        return round(float(budget), 2)

    budget_text = str(budget).strip()
    number_match = re.search(r"\d+(?:\.\d+)?", budget_text.replace(",", ""))
    if number_match:
        return round(float(number_match.group(0)), 2)

    lower_budget = budget_text.lower()
    traveler = get_traveler_profile(traveler_type)
    people = traveler["people"]
    for keyword, per_person_day in BUDGET_LEVEL_PER_PERSON_DAY.items():
        if keyword in lower_budget or keyword in budget_text:
            return round(per_person_day * max(days, 1) * people, 2)

    logger.info("Unknown budget label '%s'; no budget constraint applied.", budget)
    return None


def estimate_poi_cost(
    category: str,
    candidate_type: str,
    destination: str,
    base_cost: Optional[float] = None,
) -> float:
    cost_profile = COST_PROFILES.get(candidate_type, COST_PROFILES["comfort"])
    raw_cost = base_cost if base_cost is not None else CATEGORY_BASE_COSTS.get(category, 80)
    estimated = raw_cost * cost_profile["poi_cost_factor"] * get_destination_multiplier(destination)
    return round(max(0, estimated), 2)


def estimate_candidate_budget(
    candidate: Dict[str, Any],
    destination: str,
    days: int,
    traveler_type: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Estimates POI, hotel, local transport, food, and contingency costs.
    The estimator is deterministic and intentionally avoids third-party APIs.
    """
    candidate_type = candidate.get("id", "comfort")
    cost_profile = COST_PROFILES.get(candidate_type, COST_PROFILES["comfort"])
    traveler = get_traveler_profile(traveler_type)
    multiplier = get_destination_multiplier(destination)
    people = traveler["people"]
    rooms = traveler["rooms"]
    nights = max(int(days) - 1, 0)

    poi_total = 0.0
    for day in candidate.get("daily_plan", []):
        day_poi_total = 0.0
        for poi in day.get("pois", []):
            poi_cost = float(poi.get("estimated_cost", 0))
            day_poi_total += poi_cost * people
        day["estimated_poi_cost"] = round(day_poi_total, 2)
        poi_total += day_poi_total

    hotel_total = (
        cost_profile["hotel_per_room_night"] * rooms * nights * multiplier
    )
    food_total = cost_profile["food_per_person_day"] * people * max(days, 1) * multiplier
    baseline_transport_total = (
        cost_profile["transport_per_person_day"]
        * traveler["transport_factor"]
        * max(days, 1)
        * multiplier
    )
    route_transport_total = sum(
        float(day.get("estimated_transport_cost", 0) or 0)
        for day in candidate.get("daily_plan", [])
    )
    transport_total = route_transport_total if route_transport_total > 0 else baseline_transport_total
    subtotal = poi_total + hotel_total + food_total + transport_total
    contingency = subtotal * cost_profile["contingency_rate"]
    total = subtotal + contingency

    breakdown = {
        "currency": CURRENCY,
        "people": people,
        "rooms": rooms,
        "nights": nights,
        "poi_total": round(poi_total, 2),
        "hotel_total": round(hotel_total, 2),
        "transport_total": round(transport_total, 2),
        "transport_estimate_method": "route_based" if route_transport_total > 0 else "daily_baseline",
        "food_total": round(food_total, 2),
        "contingency": round(contingency, 2),
        "total": round(total, 2),
    }

    for day in candidate.get("daily_plan", []):
        day["estimated_day_cost"] = round(
            day.get("estimated_poi_cost", 0)
            + (food_total / max(days, 1))
            + (
                day.get("estimated_transport_cost", 0)
                if route_transport_total > 0
                else transport_total / max(days, 1)
            ),
            2,
        )

    return breakdown

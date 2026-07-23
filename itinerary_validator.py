from typing import Any, Dict, Iterable, List, Optional

from budget_estimator import normalize_budget_constraint, normalize_traveler_type

REQUIRED_CANDIDATE_FIELDS = [
    "total_budget",
    "daily_plan",
    "hotel_option",
    "transport_summary",
    "score",
    "warnings",
]

REQUIRED_POI_FIELDS = ["name", "category", "estimated_cost", "reason", "outfit_advice"]

MAX_POIS_PER_DAY = {
    "solo": 5,
    "couple": 4,
    "friends": 5,
    "family": 3,
    "business": 3,
    "senior": 3,
}


def validate_candidate(
    candidate: Dict[str, Any],
    budget: Optional[Any],
    days: int,
    traveler_type: Optional[str] = None,
) -> Dict[str, Any]:
    warnings: List[str] = []

    for field in REQUIRED_CANDIDATE_FIELDS:
        if field not in candidate:
            warnings.append(f"缺少必要字段: {field}")

    budget_limit = normalize_budget_constraint(budget, days, traveler_type)
    total_budget = candidate.get("total_budget")
    if budget_limit is not None and isinstance(total_budget, (int, float)):
        if total_budget > budget_limit:
            warnings.append(
                f"预计费用 {total_budget:.0f} CNY 超出预算 {budget_limit:.0f} CNY"
            )

    daily_plan = candidate.get("daily_plan", [])
    if not isinstance(daily_plan, list) or not daily_plan:
        warnings.append("daily_plan 为空或格式不正确")
    elif len(daily_plan) != days:
        warnings.append(f"行程天数为 {len(daily_plan)} 天，与请求的 {days} 天不一致")

    traveler = normalize_traveler_type(traveler_type)
    max_pois = MAX_POIS_PER_DAY.get(traveler, 4)
    for day_index, day in enumerate(daily_plan, start=1):
        pois = day.get("pois", [])
        if "day" not in day:
            warnings.append(f"第 {day_index} 天缺少 day 字段")
        if not isinstance(pois, list) or not pois:
            warnings.append(f"第 {day_index} 天缺少 POI")
            continue
        if len(pois) > max_pois:
            warnings.append(f"第 {day.get('day', day_index)} 天 POI 过多: {len(pois)} 个")

        for poi_index, poi in enumerate(pois, start=1):
            for field in REQUIRED_POI_FIELDS:
                if field not in poi:
                    warnings.append(
                        f"第 {day.get('day', day_index)} 天第 {poi_index} 个 POI 缺少字段: {field}"
                    )

    hotel_option = candidate.get("hotel_option", {})
    if not isinstance(hotel_option, dict):
        warnings.append("hotel_option 格式不正确")
    else:
        for field in ["name", "tier", "estimated_total"]:
            if field not in hotel_option:
                warnings.append(f"hotel_option 缺少字段: {field}")

    transport_summary = candidate.get("transport_summary", {})
    if not isinstance(transport_summary, dict):
        warnings.append("transport_summary 格式不正确")
    else:
        for field in ["mode", "estimated_total"]:
            if field not in transport_summary:
                warnings.append(f"transport_summary 缺少字段: {field}")

    candidate["warnings"] = warnings
    candidate["is_valid"] = not warnings
    return candidate


def validate_itineraries(
    candidates: Iterable[Dict[str, Any]],
    budget: Optional[Any],
    days: int,
    traveler_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    return [
        validate_candidate(candidate, budget=budget, days=days, traveler_type=traveler_type)
        for candidate in candidates
    ]

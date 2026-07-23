import logging
import re
from typing import Any, Dict, Iterable, List, Optional

from budget_estimator import normalize_budget_constraint, normalize_traveler_type

logger = logging.getLogger(__name__)

SCORE_WEIGHTS = {
    "budget_match": 0.35,
    "preference_match": 0.25,
    "intensity": 0.2,
    "diversity": 0.2,
}

PREFERENCE_ALIASES = {
    "history": {"history", "historic", "temple", "heritage", "历史", "古迹", "寺", "文化"},
    "culture": {"culture", "museum", "art", "gallery", "文化", "博物馆", "艺术"},
    "nature": {"nature", "park", "lake", "mountain", "garden", "自然", "公园", "湖", "山"},
    "food": {"food", "restaurant", "snack", "market", "美食", "餐", "小吃", "咖啡"},
    "shopping": {"shopping", "mall", "boutique", "购物", "商场", "街区"},
    "nightlife": {"nightlife", "bar", "night", "夜生活", "酒吧"},
    "family": {"family", "kid", "children", "亲子", "家庭", "孩子"},
    "local_life": {"local", "walk", "neighborhood", "city_walk", "本地", "街区", "漫步"},
    "experience": {"experience", "workshop", "show", "体验", "手作", "演出"},
}

TARGET_POIS_PER_DAY = {
    "solo": 3.5,
    "couple": 3.2,
    "friends": 3.8,
    "family": 2.6,
    "business": 2.4,
    "senior": 2.3,
}


def _tokenize_preferences(preferences: Optional[Any]) -> List[str]:
    if not preferences:
        return []
    if isinstance(preferences, (list, tuple, set)):
        raw = " ".join(str(item) for item in preferences)
    else:
        raw = str(preferences)
    return [token for token in re.split(r"[\s,;，；、/]+", raw.lower()) if token]


def _canonical_preferences(preferences: Optional[Any]) -> List[str]:
    tokens = _tokenize_preferences(preferences)
    canonical = []
    for token in tokens:
        matched = False
        for category, aliases in PREFERENCE_ALIASES.items():
            if token in aliases or any(alias in token for alias in aliases):
                canonical.append(category)
                matched = True
                break
        if not matched:
            canonical.append(token)
    return list(dict.fromkeys(canonical))


def _candidate_terms(candidate: Dict[str, Any]) -> List[str]:
    terms = []
    terms.extend(candidate.get("tags", []))
    terms.append(candidate.get("strategy", ""))
    for day in candidate.get("daily_plan", []):
        terms.append(day.get("theme", ""))
        for poi in day.get("pois", []):
            terms.extend(
                [
                    poi.get("name", ""),
                    poi.get("category", ""),
                    " ".join(poi.get("tags", [])),
                ]
            )
    return [str(term).lower() for term in terms if term]


def score_budget_match(candidate: Dict[str, Any], budget_limit: Optional[float]) -> float:
    total_budget = float(candidate.get("total_budget", 0) or 0)
    if not budget_limit or budget_limit <= 0 or total_budget <= 0:
        return 82.0

    ratio = total_budget / budget_limit
    if ratio <= 1:
        return round(max(70.0, 100.0 - abs(0.9 - ratio) * 35.0), 2)
    return round(max(0.0, 100.0 - (ratio - 1.0) * 180.0), 2)


def score_preference_match(candidate: Dict[str, Any], preferences: Optional[Any]) -> float:
    canonical_preferences = _canonical_preferences(preferences)
    if not canonical_preferences:
        return 82.0

    terms = _candidate_terms(candidate)
    matches = 0
    for preference in canonical_preferences:
        if any(preference in term for term in terms):
            matches += 1
    return round(55.0 + (matches / len(canonical_preferences)) * 45.0, 2)


def score_intensity(candidate: Dict[str, Any], traveler_type: Optional[str]) -> float:
    days = candidate.get("daily_plan", [])
    if not days:
        return 0.0

    traveler = normalize_traveler_type(traveler_type)
    target = TARGET_POIS_PER_DAY.get(traveler, 3.0)
    counts = [len(day.get("pois", [])) for day in days]
    average_count = sum(counts) / len(counts)
    distance = abs(average_count - target)
    score = max(45.0, 100.0 - distance * 22.0)
    return round(score, 2)


def score_diversity(candidate: Dict[str, Any]) -> float:
    categories = []
    names = []
    for day in candidate.get("daily_plan", []):
        for poi in day.get("pois", []):
            categories.append(poi.get("category", ""))
            names.append(poi.get("name", ""))

    if not categories:
        return 0.0

    category_ratio = len(set(categories)) / len(categories)
    repeat_penalty = max(0, len(names) - len(set(names))) * 4
    score = 68.0 + category_ratio * 32.0 - repeat_penalty
    return round(max(0.0, min(100.0, score)), 2)


def score_candidate(
    candidate: Dict[str, Any],
    budget_limit: Optional[float],
    preferences: Optional[Any],
    traveler_type: Optional[str],
) -> Dict[str, float]:
    components = {
        "budget_match": score_budget_match(candidate, budget_limit),
        "preference_match": score_preference_match(candidate, preferences),
        "intensity": score_intensity(candidate, traveler_type),
        "diversity": score_diversity(candidate),
    }
    total = sum(components[key] * weight for key, weight in SCORE_WEIGHTS.items())
    return {
        "total": round(total, 2),
        **components,
    }


def rank_itineraries(
    candidates: Iterable[Dict[str, Any]],
    budget: Optional[Any],
    days: int,
    preferences: Optional[Any] = None,
    traveler_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    budget_limit = normalize_budget_constraint(budget, days, traveler_type)
    ranked = []
    for candidate in candidates:
        candidate["score"] = score_candidate(
            candidate,
            budget_limit=budget_limit,
            preferences=preferences,
            traveler_type=traveler_type,
        )
        ranked.append(candidate)

    ranked.sort(key=lambda item: item.get("score", {}).get("total", 0), reverse=True)
    for index, candidate in enumerate(ranked, start=1):
        candidate["rank"] = index
    logger.info("Ranked %s itinerary candidates.", len(ranked))
    return ranked

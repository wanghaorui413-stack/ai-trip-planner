"""Offline evaluator for the AI Trip Planner MVP.

The evaluator works with synthetic test cases and mock-data planner outputs.
It does not call live booking, ticketing, payment, map, or inventory services.

Examples:
    python evals/evaluate_plans.py
    python evals/evaluate_plans.py --predictions evals/predictions.json
    python evals/evaluate_plans.py --output evals/latest_report.json --no-fail
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from budget_estimator import normalize_budget_constraint, normalize_traveler_type
    from itinerary_validator import MAX_POIS_PER_DAY
except Exception:  # pragma: no cover - keeps evaluator usable against raw JSON.
    normalize_budget_constraint = None
    normalize_traveler_type = None
    MAX_POIS_PER_DAY = {
        "solo": 5,
        "couple": 4,
        "friends": 5,
        "family": 3,
        "business": 3,
        "senior": 3,
    }


PREFERENCE_ALIASES: Dict[str, set[str]] = {
    "history": {"history", "historic", "heritage", "temple", "历史", "古迹", "寺", "寺社"},
    "culture": {"culture", "museum", "art", "gallery", "文化", "艺术", "展览"},
    "museum": {"museum", "gallery", "博物馆", "美术馆", "展馆"},
    "nature": {"nature", "park", "lake", "mountain", "garden", "自然", "公园", "湖", "山"},
    "food": {"food", "restaurant", "snack", "market", "美食", "餐", "小吃", "火锅", "咖啡"},
    "shopping": {"shopping", "mall", "market", "boutique", "购物", "商场", "市场", "街"},
    "nightlife": {"nightlife", "bar", "night", "夜生活", "酒吧", "夜间"},
    "family": {"family", "kid", "children", "亲子", "家庭", "孩子", "熊猫"},
    "local_life": {"local_life", "local", "neighborhood", "本地", "街区", "社区", "生活"},
    "city_walk": {"city_walk", "walk", "walking", "漫步", "步行", "街区"},
    "experience": {"experience", "workshop", "show", "体验", "手作", "演出", "茶道"},
    "viewpoint": {"viewpoint", "view", "tower", "landmark", "观景", "地标", "塔"},
    "landmark": {"landmark", "iconic", "地标", "经典"},
    "tea": {"tea", "tea_culture", "茶", "茶馆", "茶文化", "茶道"},
    "relaxed": {"relaxed", "slow", "light", "轻松", "慢游", "舒缓", "休息"},
}

DEFAULT_MIN_PREFERENCE_MATCH = 0.66
DEFAULT_MIN_COMPLETENESS = 0.95
DEFAULT_MIN_DAILY_LOAD = 0.85


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
        file.write("\n")


def load_cases(path: Path) -> List[Dict[str, Any]]:
    payload = load_json(path)
    if isinstance(payload, dict):
        cases = payload.get("test_cases", [])
    else:
        cases = payload

    if not isinstance(cases, list) or not cases:
        raise ValueError(f"No test cases found in {path}")
    return cases


def normalize_traveler(value: Optional[str]) -> str:
    if normalize_traveler_type:
        return normalize_traveler_type(value)
    if not value:
        return "solo"
    lowered = str(value).strip().lower()
    aliases = {
        "couple": "couple",
        "情侣": "couple",
        "friends": "friends",
        "朋友": "friends",
        "family": "family",
        "亲子": "family",
        "家庭": "family",
        "business": "business",
        "商务": "business",
        "senior": "senior",
        "长辈": "senior",
        "老人": "senior",
    }
    for alias, normalized in aliases.items():
        if alias in lowered:
            return normalized
    return "solo"


def budget_limit_for(case_input: Dict[str, Any]) -> Optional[float]:
    budget = case_input.get("budget")
    days = int(case_input.get("days", 1) or 1)
    traveler_type = case_input.get("traveler_type")
    if normalize_budget_constraint:
        return normalize_budget_constraint(budget, days, traveler_type)

    if budget in (None, ""):
        return None
    if isinstance(budget, (int, float)):
        return float(budget)
    digits = "".join(char for char in str(budget) if char.isdigit() or char == ".")
    return float(digits) if digits else None


def unwrap_payload(payload: Any) -> Any:
    current = payload
    for key in ("data", "result", "plan", "output"):
        if isinstance(current, dict) and key in current and len(current) <= 3:
            current = current[key]
    return current


def prediction_for_case(predictions: Any, case: Dict[str, Any], index: int) -> Any:
    case_id = case.get("id")
    if predictions is None:
        return generate_prediction(case)

    payload = unwrap_payload(predictions)
    if isinstance(payload, dict):
        if case_id and case_id in payload:
            return unwrap_payload(payload[case_id])
        for key in ("results", "predictions", "cases"):
            values = payload.get(key)
            if isinstance(values, list) and index < len(values):
                item = values[index]
                if isinstance(item, dict) and "prediction" in item:
                    return unwrap_payload(item["prediction"])
                return unwrap_payload(item)
        if "candidates" in payload or "daily_plan" in payload:
            return payload

    if isinstance(payload, list) and index < len(payload):
        item = payload[index]
        if isinstance(item, dict) and "prediction" in item:
            return unwrap_payload(item["prediction"])
        return unwrap_payload(item)

    raise ValueError(f"Prediction not found for case {case_id or index}")


def generate_prediction(case: Dict[str, Any]) -> Dict[str, Any]:
    from planner import plan_trip

    case_input = case.get("input", {})
    return plan_trip(
        destination=case_input.get("destination"),
        days=case_input.get("days"),
        budget=case_input.get("budget"),
        preferences=case_input.get("preferences"),
        traveler_type=case_input.get("traveler_type", "solo"),
        rag_context="",
        rag_sources=[],
    )


def select_candidate(plan: Any, policy: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    plan = unwrap_payload(plan)
    if isinstance(plan, list):
        candidates = [item for item in plan if isinstance(item, dict)]
        full_plan: Dict[str, Any] = {"candidates": candidates}
    elif isinstance(plan, dict):
        full_plan = plan
        candidates = plan.get("candidates") if isinstance(plan.get("candidates"), list) else None
        if candidates is None and "daily_plan" in plan:
            candidates = [plan]
    else:
        raise ValueError("Prediction payload must be a dict or list")

    if not candidates:
        raise ValueError("No itinerary candidate found in prediction payload")

    if policy == "top_score":
        candidate = max(
            candidates,
            key=lambda item: float(item.get("score", {}).get("total", 0) or 0),
        )
    else:
        candidate = min(
            candidates,
            key=lambda item: int(item.get("rank", 10_000) or 10_000),
        )
    return full_plan, candidate


def as_number(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace(",", "").strip())
        except ValueError:
            return None
    return None


def is_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict, tuple, set)):
        return bool(value)
    return True


def collect_terms(candidate: Dict[str, Any]) -> List[str]:
    terms: List[str] = []
    for key in ("id", "title", "strategy", "tags"):
        value = candidate.get(key)
        if isinstance(value, list):
            terms.extend(str(item) for item in value)
        elif value:
            terms.append(str(value))

    for day in candidate.get("daily_plan", []) or []:
        if isinstance(day, dict):
            terms.append(str(day.get("theme", "")))
            terms.append(str(day.get("meal_suggestion", "")))
            terms.append(str(day.get("daily_transport", "")))
            for poi in day.get("pois", []) or []:
                if not isinstance(poi, dict):
                    continue
                terms.extend(
                    [
                        str(poi.get("name", "")),
                        str(poi.get("category", "")),
                        " ".join(str(tag) for tag in poi.get("tags", []) or []),
                    ]
                )
    return [term.lower() for term in terms if term and term != "None"]


def expand_preference(value: str) -> set[str]:
    token = str(value).strip().lower()
    expanded = {token}
    if token in PREFERENCE_ALIASES:
        expanded.update(PREFERENCE_ALIASES[token])
    for canonical, aliases in PREFERENCE_ALIASES.items():
        if token in aliases:
            expanded.add(canonical)
            expanded.update(aliases)
    return {item.lower() for item in expanded if item}


def score_preference_match(
    candidate: Dict[str, Any],
    case: Dict[str, Any],
) -> Tuple[float, List[str], List[str]]:
    expectations = case.get("expectations", {})
    expected = expectations.get("expected_preferences")
    if not expected:
        raw = str(case.get("input", {}).get("preferences", "") or "")
        expected = [token for token in raw.replace(",", " ").replace("，", " ").split() if token]

    if not expected:
        return 1.0, [], []

    terms = collect_terms(candidate)
    matched: List[str] = []
    missing: List[str] = []
    for preference in expected:
        aliases = expand_preference(str(preference))
        if any(alias in term for alias in aliases for term in terms):
            matched.append(str(preference))
        else:
            missing.append(str(preference))
    return round(len(matched) / len(expected), 4), matched, missing


def score_budget_fit(
    candidate: Dict[str, Any],
    case: Dict[str, Any],
) -> Tuple[float, Optional[float], Optional[float], bool]:
    case_input = case.get("input", {})
    expectations = case.get("expectations", {})
    budget_limit = budget_limit_for(case_input)
    total_budget = as_number(candidate.get("total_budget"))
    if budget_limit is None:
        return 1.0, None, total_budget, True
    if total_budget is None:
        return 0.0, budget_limit, None, False

    allowed_overrun = float(expectations.get("max_budget_overrun_pct", 0) or 0)
    allowed_total = budget_limit * (1 + allowed_overrun)
    passed = total_budget <= allowed_total
    if passed:
        return 1.0, budget_limit, total_budget, True

    overrun_ratio = (total_budget - allowed_total) / max(budget_limit, 1)
    return round(max(0.0, 1.0 - overrun_ratio), 4), budget_limit, total_budget, False


def score_plan_completeness(
    full_plan: Dict[str, Any],
    candidate: Dict[str, Any],
    case: Dict[str, Any],
) -> Tuple[float, List[str]]:
    case_input = case.get("input", {})
    requested_days = int(case_input.get("days", 0) or 0)
    missing: List[str] = []
    checks: List[Tuple[str, bool]] = []

    for field in ("destination", "days", "currency"):
        if field in full_plan:
            checks.append((f"plan.{field}", is_present(full_plan.get(field))))

    candidate_fields_allowing_empty = {"warnings"}
    for field in (
        "id",
        "title",
        "daily_plan",
        "hotel_option",
        "transport_summary",
        "budget_breakdown",
        "total_budget",
        "score",
        "warnings",
    ):
        present = field in candidate and (
            field in candidate_fields_allowing_empty or is_present(candidate.get(field))
        )
        checks.append((f"candidate.{field}", present))

    daily_plan = candidate.get("daily_plan")
    checks.append(("candidate.daily_plan_length", isinstance(daily_plan, list) and len(daily_plan) == requested_days))

    if isinstance(daily_plan, list):
        for index, day in enumerate(daily_plan, start=1):
            if not isinstance(day, dict):
                checks.append((f"day_{index}.object", False))
                continue
            for field in ("day", "theme", "pois", "meal_suggestion", "daily_transport", "estimated_day_cost"):
                checks.append((f"day_{index}.{field}", field in day and is_present(day.get(field))))
            pois = day.get("pois")
            if isinstance(pois, list):
                for poi_index, poi in enumerate(pois, start=1):
                    if not isinstance(poi, dict):
                        checks.append((f"day_{index}.poi_{poi_index}.object", False))
                        continue
                    for field in ("name", "category", "duration_hours", "estimated_cost", "reason", "tags"):
                        checks.append(
                            (
                                f"day_{index}.poi_{poi_index}.{field}",
                                field in poi and is_present(poi.get(field)),
                            )
                        )

    hotel = candidate.get("hotel_option")
    if isinstance(hotel, dict):
        for field in ("name", "tier", "nights", "estimated_total", "reason"):
            checks.append((f"hotel_option.{field}", field in hotel and is_present(hotel.get(field))))
    else:
        checks.append(("hotel_option.object", False))

    transport = candidate.get("transport_summary")
    if isinstance(transport, dict):
        for field in ("mode", "estimated_total", "notes"):
            checks.append((f"transport_summary.{field}", field in transport and is_present(transport.get(field))))
    else:
        checks.append(("transport_summary.object", False))

    breakdown = candidate.get("budget_breakdown")
    if isinstance(breakdown, dict):
        for field in (
            "currency",
            "people",
            "rooms",
            "nights",
            "poi_total",
            "hotel_total",
            "transport_total",
            "food_total",
            "contingency",
            "total",
        ):
            checks.append((f"budget_breakdown.{field}", field in breakdown and is_present(breakdown.get(field))))
    else:
        checks.append(("budget_breakdown.object", False))

    for name, passed in checks:
        if not passed:
            missing.append(name)
    score = sum(1 for _, passed in checks if passed) / max(len(checks), 1)
    return round(score, 4), missing


def score_daily_load(candidate: Dict[str, Any], case: Dict[str, Any]) -> Tuple[float, List[str]]:
    case_input = case.get("input", {})
    expectations = case.get("expectations", {})
    requested_days = int(case_input.get("days", 0) or 0)
    traveler = normalize_traveler(case_input.get("traveler_type"))
    default_max = int(MAX_POIS_PER_DAY.get(traveler, 4))
    min_pois, max_pois = expectations.get("daily_poi_range", [1, default_max])
    max_hours = float(expectations.get("max_daily_hours", 8) or 8)
    daily_plan = candidate.get("daily_plan")
    notes: List[str] = []

    if not isinstance(daily_plan, list) or not daily_plan:
        return 0.0, ["daily_plan is empty or not a list"]

    day_scores: List[float] = []
    for index, day in enumerate(daily_plan, start=1):
        pois = day.get("pois", []) if isinstance(day, dict) else []
        if not isinstance(pois, list):
            notes.append(f"day {index}: pois is not a list")
            day_scores.append(0.0)
            continue

        count = len(pois)
        durations = [as_number(poi.get("duration_hours")) or 0 for poi in pois if isinstance(poi, dict)]
        hours = sum(durations)

        if count < min_pois:
            count_score = count / max(float(min_pois), 1.0)
            notes.append(f"day {index}: POI count {count} below expected minimum {min_pois}")
        elif count > max_pois:
            count_score = max(0.0, 1.0 - ((count - max_pois) / max(float(max_pois), 1.0)))
            notes.append(f"day {index}: POI count {count} above expected maximum {max_pois}")
        else:
            count_score = 1.0

        if hours > max_hours:
            hours_score = max(0.0, 1.0 - ((hours - max_hours) / max(max_hours, 1.0)))
            notes.append(f"day {index}: planned POI duration {hours:.1f}h exceeds {max_hours:.1f}h")
        else:
            hours_score = 1.0

        day_scores.append((count_score + hours_score) / 2)

    score = statistics.mean(day_scores)
    if len(daily_plan) != requested_days:
        score *= 0.5
        notes.append(f"plan has {len(daily_plan)} days, expected {requested_days}")
    return round(score, 4), notes


def warning_count(candidate: Dict[str, Any]) -> int:
    warnings = candidate.get("warnings", [])
    if isinstance(warnings, list):
        return len(warnings)
    if isinstance(warnings, str):
        return 1 if warnings.strip() else 0
    return 0


def evaluate_case(case: Dict[str, Any], prediction: Any, policy: str) -> Dict[str, Any]:
    case_id = case.get("id", "unknown")
    try:
        full_plan, candidate = select_candidate(prediction, policy=policy)
        budget_fit, budget_limit, total_budget, budget_passed = score_budget_fit(candidate, case)
        preference_match, matched_preferences, missing_preferences = score_preference_match(candidate, case)
        plan_completeness, missing_fields = score_plan_completeness(full_plan, candidate, case)
        daily_load, daily_load_notes = score_daily_load(candidate, case)
        warnings_total = warning_count(candidate)

        expectations = case.get("expectations", {})
        max_warning_count = int(expectations.get("max_warning_count", 0) or 0)
        min_preference_match = float(
            expectations.get("min_preference_match", DEFAULT_MIN_PREFERENCE_MATCH)
        )
        min_completeness = float(expectations.get("min_completeness", DEFAULT_MIN_COMPLETENESS))
        min_daily_load = float(expectations.get("min_daily_load", DEFAULT_MIN_DAILY_LOAD))
        warning_passed = warnings_total <= max_warning_count
        warning_score = 1.0 if warning_passed else 0.0

        checks = {
            "budget_fit": budget_passed,
            "preference_match": preference_match >= min_preference_match,
            "plan_completeness": plan_completeness >= min_completeness,
            "daily_load": daily_load >= min_daily_load,
            "warning_count": warning_passed,
        }
        passed = all(checks.values())
        overall_score = statistics.mean(
            [budget_fit, preference_match, plan_completeness, daily_load, warning_score]
        )

        return {
            "case_id": case_id,
            "title": case.get("title", ""),
            "passed": passed,
            "checks": checks,
            "metrics": {
                "budget_fit": budget_fit,
                "preference_match": preference_match,
                "plan_completeness": plan_completeness,
                "daily_load": daily_load,
                "warning_count": warnings_total,
                "overall_score": round(overall_score, 4),
            },
            "selected_candidate": {
                "id": candidate.get("id"),
                "title": candidate.get("title"),
                "rank": candidate.get("rank"),
                "score": candidate.get("score"),
                "total_budget": total_budget,
                "budget_limit": budget_limit,
            },
            "diagnostics": {
                "matched_preferences": matched_preferences,
                "missing_preferences": missing_preferences,
                "missing_fields": missing_fields[:30],
                "missing_field_count": len(missing_fields),
                "daily_load_notes": daily_load_notes,
                "warnings": candidate.get("warnings", []),
            },
        }
    except Exception as exc:
        return {
            "case_id": case_id,
            "title": case.get("title", ""),
            "passed": False,
            "checks": {
                "budget_fit": False,
                "preference_match": False,
                "plan_completeness": False,
                "daily_load": False,
                "warning_count": False,
            },
            "metrics": {
                "budget_fit": 0.0,
                "preference_match": 0.0,
                "plan_completeness": 0.0,
                "daily_load": 0.0,
                "warning_count": 1,
                "overall_score": 0.0,
            },
            "diagnostics": {"error": str(exc)},
        }


def summarize(results: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    metric_names = ["budget_fit", "preference_match", "plan_completeness", "daily_load", "overall_score"]
    averages = {
        metric: round(
            statistics.mean(float(result["metrics"].get(metric, 0.0)) for result in results),
            4,
        )
        for metric in metric_names
    }
    warning_total = sum(int(result["metrics"].get("warning_count", 0)) for result in results)
    failed = [result["case_id"] for result in results if not result.get("passed")]
    return {
        "case_count": len(results),
        "passed_count": len(results) - len(failed),
        "failed_count": len(failed),
        "failed_case_ids": failed,
        "average_metrics": averages,
        "warning_count_total": warning_total,
    }


def build_report(args: argparse.Namespace) -> Dict[str, Any]:
    cases = load_cases(args.cases)
    predictions = load_json(args.predictions) if args.predictions else None
    results = [
        evaluate_case(
            case=case,
            prediction=prediction_for_case(predictions, case, index),
            policy=args.candidate_policy,
        )
        for index, case in enumerate(cases)
    ]
    summary = summarize(results)
    return {
        "metadata": {
            "name": "AI Trip Planner MVP Evaluation Report",
            "stage": "MVP mock data",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "cases_path": str(args.cases),
            "predictions_path": str(args.predictions) if args.predictions else None,
            "candidate_policy": args.candidate_policy,
            "metrics": [
                "budget_fit",
                "preference_match",
                "plan_completeness",
                "daily_load",
                "warning_count",
            ],
            "data_policy": "Synthetic scenarios and mock planner data only; no real user data.",
        },
        "summary": summary,
        "cases": results,
    }


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate generated trip plans against MVP test cases.")
    parser.add_argument(
        "--cases",
        type=Path,
        default=Path(__file__).with_name("test_cases.json"),
        help="Path to eval test cases JSON.",
    )
    parser.add_argument(
        "--predictions",
        type=Path,
        default=None,
        help="Optional predictions JSON. If omitted, the local planner is called.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional path to write the full evaluation report JSON.",
    )
    parser.add_argument(
        "--candidate-policy",
        choices=["rank1", "top_score"],
        default="rank1",
        help="How to select a candidate when a plan contains multiple options.",
    )
    parser.add_argument(
        "--no-fail",
        action="store_true",
        help="Always exit 0 even if one or more cases fail.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = parse_args(argv)
    report = build_report(args)
    if args.output:
        write_json(args.output, report)

    summary = report["summary"]
    print(
        "Evaluation complete: "
        f"{summary['passed_count']}/{summary['case_count']} passed, "
        f"{summary['failed_count']} failed, "
        f"avg overall_score={summary['average_metrics']['overall_score']:.3f}, "
        f"warning_count_total={summary['warning_count_total']}"
    )
    if summary["failed_case_ids"]:
        print("Failed cases: " + ", ".join(summary["failed_case_ids"]))

    return 0 if args.no_fail or summary["failed_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())


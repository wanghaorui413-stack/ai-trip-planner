import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional, Union

from planner import list_destination_poi_catalog, plan_selected_pois, plan_trip, replace_candidate_poi
from single_trip_agent import convert_currency_agent, plan_full_trip_agent

# Get a logger instance for this module
# The configuration is already applied in single_main.py, so we just need to get the logger.
logger = logging.getLogger(__name__)

router = APIRouter()


class TripPlanRequest(BaseModel):
    destination: str = Field(..., min_length=1)
    from_date: str
    to_date: str
    preferences: Optional[str] = None


class MultiPlanRequest(BaseModel):
    destination: str = Field(..., min_length=1)
    days: int = Field(..., ge=1, le=21)
    start_date: Optional[str] = None
    budget: Optional[Union[float, str]] = None
    preferences: Optional[str] = None
    traveler_type: Optional[str] = "solo"


class PoiReplacementRequest(BaseModel):
    destination: str = Field(..., min_length=1)
    candidate: Dict[str, Any]
    day_index: int = Field(..., ge=0)
    poi_index: int = Field(..., ge=0)
    replacement_name: Optional[str] = None
    budget: Optional[Union[float, str]] = None
    preferences: Optional[str] = None
    traveler_type: Optional[str] = "solo"


class PoiCatalogRequest(BaseModel):
    destination: str = Field(..., min_length=1)
    profile_id: Optional[str] = "comfort"
    preferences: Optional[str] = None
    traveler_type: Optional[str] = "solo"


class SelectedPoisRequest(BaseModel):
    destination: str = Field(..., min_length=1)
    selected_pois: List[str] = Field(..., min_length=1)
    days: int = Field(..., ge=1, le=21)
    start_date: Optional[str] = None
    budget: Optional[Union[float, str]] = None
    preferences: Optional[str] = None
    traveler_type: Optional[str] = "solo"
    profile_id: Optional[str] = "comfort"


class CurrencyConvertRequest(BaseModel):
    amount: float = Field(..., gt=0)
    from_currency: str = Field(..., min_length=3, max_length=3)
    to_currency: str = Field(..., min_length=3, max_length=3)


# --- API Endpoints ---

@router.post("/plan-full-trip")
async def plan_full_trip(request: TripPlanRequest) -> Dict[str, Any]:
    logger.info(f"Received request for '/plan-full-trip' for destination: '{request.destination}'")
    try:
        # The actual work is delegated to the agent, which will have its own logging
        full_trip_info = plan_full_trip_agent(
            request.destination,
            request.from_date,
            request.to_date,
            request.preferences
        )

        # Handle errors returned from the agent
        if isinstance(full_trip_info, dict) and "error" in full_trip_info:
            error_detail = full_trip_info["error"]
            logger.error(f"Agent returned an error for destination '{request.destination}': {error_detail}")
            raise HTTPException(status_code=500, detail=error_detail)

        logger.info(f"Successfully generated trip plan for '{request.destination}'.")
        return {"data": full_trip_info}

    except Exception as e:
        # Catch any unexpected exceptions
        logger.error(f"An unexpected exception occurred in '/plan-full-trip': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {e}")


@router.post("/plan-trip-options")
def plan_trip_options(request: MultiPlanRequest) -> Dict[str, Any]:
    logger.info(
        "Received request for '/plan-trip-options' for destination: '%s'",
        request.destination,
    )
    try:
        from single_trip_agent import (
            get_context_with_sources,
            get_vector_store_status,
        )

        rag_query = (
            f"{request.destination} travel recommendations "
            f"{request.preferences or ''} itinerary highlights"
        )
        rag_context, rag_sources = get_context_with_sources(rag_query)
        trip_options = plan_trip(
            destination=request.destination,
            days=request.days,
            budget=request.budget,
            preferences=request.preferences,
            traveler_type=request.traveler_type,
            start_date=request.start_date,
            rag_context=rag_context,
            rag_sources=rag_sources,
        )
        trip_options.setdefault("rag", {}).update(get_vector_store_status())
        if isinstance(trip_options, dict) and "error" in trip_options:
            raise HTTPException(status_code=400, detail=trip_options["error"])

        logger.info(
            "Successfully generated ranked trip options for '%s'.",
            request.destination,
        )
        return {"data": trip_options}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "An unexpected exception occurred in '/plan-trip-options': %s",
            e,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {e}")


@router.post("/replace-poi")
def replace_poi(request: PoiReplacementRequest) -> Dict[str, Any]:
    logger.info(
        "Replacing POI at day %s index %s for destination '%s'.",
        request.day_index + 1,
        request.poi_index,
        request.destination,
    )
    try:
        updated_candidate = replace_candidate_poi(
            candidate=request.candidate,
            destination=request.destination,
            day_index=request.day_index,
            poi_index=request.poi_index,
            budget=request.budget,
            preferences=request.preferences,
            traveler_type=request.traveler_type,
            replacement_name=request.replacement_name,
        )
        return {"data": updated_candidate}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("POI replacement failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"POI replacement failed: {exc}") from exc

@router.post("/poi-catalog")
def poi_catalog(request: PoiCatalogRequest) -> Dict[str, Any]:
    try:
        return {
            "data": list_destination_poi_catalog(
                destination=request.destination,
                profile_id=request.profile_id or "comfort",
                preferences=request.preferences,
                traveler_type=request.traveler_type,
            )
        }
    except Exception as exc:
        logger.error("POI catalog failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"POI catalog failed: {exc}") from exc


@router.post("/plan-selected-pois")
def plan_selected_poi_route(request: SelectedPoisRequest) -> Dict[str, Any]:
    try:
        selected_plan = plan_selected_pois(
            destination=request.destination,
            selected_pois=request.selected_pois,
            days=request.days,
            budget=request.budget,
            preferences=request.preferences,
            traveler_type=request.traveler_type,
            profile_id=request.profile_id or "comfort",
            start_date=request.start_date,
        )
        if isinstance(selected_plan, dict) and "error" in selected_plan:
            raise HTTPException(status_code=400, detail=selected_plan["error"])
        return {"data": selected_plan}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Selected POI planning failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Selected POI planning failed: {exc}") from exc
@router.post("/convert-currency")
async def convert_currency(request: CurrencyConvertRequest):
    logger.info(f"Received request for '/convert-currency' from {request.from_currency} to {request.to_currency}")
    try:
        converted_result = convert_currency_agent(
            request.amount,
            request.from_currency,
            request.to_currency
        )
        logger.info(
            f"Successfully converted currency: {request.amount} {request.from_currency} -> {converted_result.get('converted_amount')} {request.to_currency}")
        return {"data": converted_result}

    except Exception as e:
        logger.error(f"An unexpected exception occurred in '/convert-currency': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Currency conversion failed: {e}")


"""Authenticated user profile and saved-trip API routes."""

import re
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from auth_store import (
    authenticate_user,
    create_access_token,
    create_user,
    delete_trip,
    get_trip,
    list_trips,
    save_trip,
    update_user,
    user_from_token,
)


router = APIRouter()
bearer_scheme = HTTPBearer(auto_error=False)


class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=254)
    display_name: str = Field(..., min_length=1, max_length=60)
    password: str = Field(..., min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=254)
    password: str = Field(..., min_length=1, max_length=128)


class UserUpdateRequest(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=60)
    preferences: Dict[str, Any] = Field(default_factory=dict)


class SavedTripRequest(BaseModel):
    title: str = Field(default="", max_length=120)
    plan: Dict[str, Any]


def current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Dict[str, Any]:
    user = user_from_token(credentials.credentials) if credentials else None
    if user is None:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    return user


@router.post("/auth/register", status_code=201)
def register(request: RegisterRequest) -> Dict[str, Any]:
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", request.email.strip()):
        raise HTTPException(status_code=422, detail="请输入有效的邮箱地址")
    try:
        user = create_user(request.email, request.display_name, request.password)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"data": {"access_token": create_access_token(user["id"]), "user": user}}


@router.post("/auth/login")
def login(request: LoginRequest) -> Dict[str, Any]:
    user = authenticate_user(request.email, request.password)
    if user is None:
        raise HTTPException(status_code=401, detail="邮箱或密码不正确")
    return {"data": {"access_token": create_access_token(user["id"]), "user": user}}


@router.get("/users/me")
def get_me(user: Dict[str, Any] = Depends(current_user)) -> Dict[str, Any]:
    return {"data": user}


@router.patch("/users/me")
def patch_me(request: UserUpdateRequest, user: Dict[str, Any] = Depends(current_user)) -> Dict[str, Any]:
    return {"data": update_user(user["id"], request.display_name, request.preferences)}


@router.post("/trips", status_code=201)
def create_saved_trip(request: SavedTripRequest, user: Dict[str, Any] = Depends(current_user)) -> Dict[str, Any]:
    return {"data": save_trip(user["id"], request.title, request.plan)}


@router.get("/trips")
def get_saved_trips(user: Dict[str, Any] = Depends(current_user)) -> Dict[str, Any]:
    return {"data": list_trips(user["id"])}


@router.get("/trips/{trip_id}")
def get_saved_trip(trip_id: str, user: Dict[str, Any] = Depends(current_user)) -> Dict[str, Any]:
    trip = get_trip(user["id"], trip_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="攻略不存在")
    return {"data": trip}


@router.delete("/trips/{trip_id}")
def remove_saved_trip(trip_id: str, user: Dict[str, Any] = Depends(current_user)) -> Dict[str, Any]:
    if not delete_trip(user["id"], trip_id):
        raise HTTPException(status_code=404, detail="攻略不存在")
    return {"data": {"deleted": True}}

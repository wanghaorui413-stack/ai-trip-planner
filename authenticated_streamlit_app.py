"""Authenticated Streamlit shell around the existing travel planner UI."""

import os
import runpy
from typing import Any, Dict

import requests
import streamlit as st


BASE_API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")
API_ROOT = f"{BASE_API_URL}/api"

st.set_page_config(
    page_title="Voyage Studio · 我的旅行攻略",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .auth-wrap {max-width: 560px; margin: 4rem auto 1.5rem; text-align: center;}
    .auth-wrap h1 {color: #173f32; font-size: 2.25rem;}
    .auth-wrap p {color: #68736d;}
    [data-testid="stSidebar"] {background: #f5f6f1;}
    </style>
    """,
    unsafe_allow_html=True,
)


def _detail(response: requests.Response) -> str:
    try:
        return str(response.json().get("detail", response.text))
    except ValueError:
        return response.text


def _auth_headers() -> Dict[str, str]:
    return {"Authorization": f"Bearer {st.session_state.get('access_token', '')}"}


def _api(method: str, path: str, **kwargs: Any) -> Any:
    response = requests.request(method, f"{API_ROOT}{path}", timeout=(5, 30), **kwargs)
    if response.status_code == 401:
        st.session_state.pop("access_token", None)
        st.session_state.pop("current_user", None)
        raise RuntimeError("登录已过期，请重新登录")
    if not response.ok:
        raise RuntimeError(_detail(response))
    return response.json().get("data")


def _accept_auth(data: Dict[str, Any]) -> None:
    st.session_state["access_token"] = data["access_token"]
    st.session_state["current_user"] = data["user"]


def _render_login() -> None:
    st.markdown(
        '<div class="auth-wrap"><h1>Voyage Studio</h1>'
        '<p>登录后保存你的攻略设计、旅行偏好和每一次出发灵感。</p></div>',
        unsafe_allow_html=True,
    )
    _, center, _ = st.columns([1, 1.15, 1])
    with center:
        login_tab, register_tab = st.tabs(["登录", "创建账户"])
        with login_tab:
            with st.form("login-form"):
                email = st.text_input("邮箱", placeholder="you@example.com")
                password = st.text_input("密码", type="password")
                submitted = st.form_submit_button("登录", type="primary", use_container_width=True)
            if submitted:
                try:
                    _accept_auth(_api("POST", "/auth/login", json={"email": email, "password": password}))
                    st.rerun()
                except (requests.RequestException, RuntimeError) as exc:
                    st.error(f"登录失败：{exc}")
        with register_tab:
            with st.form("register-form"):
                display_name = st.text_input("昵称")
                email = st.text_input("注册邮箱")
                password = st.text_input("设置密码（至少 8 位）", type="password")
                confirm = st.text_input("确认密码", type="password")
                submitted = st.form_submit_button("创建并登录", type="primary", use_container_width=True)
            if submitted:
                if password != confirm:
                    st.error("两次输入的密码不一致")
                else:
                    try:
                        _accept_auth(_api("POST", "/auth/register", json={
                            "display_name": display_name, "email": email, "password": password,
                        }))
                        st.rerun()
                    except (requests.RequestException, RuntimeError) as exc:
                        st.error(f"注册失败：{exc}")


def _render_account_sidebar() -> None:
    user = st.session_state["current_user"]
    st.sidebar.title(f"你好，{user['display_name']}")
    st.sidebar.caption(user["email"])

    with st.sidebar.expander("旅行偏好", expanded=False):
        preferences = user.get("preferences", {})
        with st.form("profile-form"):
            display_name = st.text_input("昵称", value=user["display_name"])
            interests = st.text_area(
                "常用偏好", value=str(preferences.get("interests", "")),
                placeholder="美食、历史文化、自然风光",
            )
            traveler_type = st.selectbox(
                "默认同行方式", ["solo", "couple", "friends", "family", "business", "senior"],
                index=["solo", "couple", "friends", "family", "business", "senior"].index(
                    preferences.get("traveler_type", "solo")
                    if preferences.get("traveler_type", "solo") in ["solo", "couple", "friends", "family", "business", "senior"]
                    else "solo"
                ),
            )
            budget_style = st.selectbox(
                "默认预算风格", ["经济", "舒适", "高端"],
                index=["经济", "舒适", "高端"].index(preferences.get("budget_style", "舒适"))
                if preferences.get("budget_style", "舒适") in ["经济", "舒适", "高端"] else 1,
            )
            saved = st.form_submit_button("保存偏好", use_container_width=True)
        if saved:
            try:
                st.session_state["current_user"] = _api(
                    "PATCH", "/users/me", headers=_auth_headers(),
                    json={"display_name": display_name, "preferences": {
                        "interests": interests, "traveler_type": traveler_type, "budget_style": budget_style,
                    }},
                )
                st.toast("旅行偏好已保存")
                st.rerun()
            except (requests.RequestException, RuntimeError) as exc:
                st.error(str(exc))

    st.sidebar.subheader("保存当前攻略")
    current_plan = st.session_state.get("trip_plan")
    default_title = ""
    if current_plan:
        default_title = f"{current_plan.get('destination', '')} {current_plan.get('days', '')}日攻略"
    trip_title = st.sidebar.text_input("攻略名称", value=default_title, key="saved-trip-title")
    if st.sidebar.button("保存到我的攻略", disabled=not bool(current_plan), use_container_width=True):
        try:
            _api("POST", "/trips", headers=_auth_headers(), json={"title": trip_title, "plan": current_plan})
            st.toast("攻略已保存")
            st.rerun()
        except (requests.RequestException, RuntimeError) as exc:
            st.sidebar.error(str(exc))

    st.sidebar.subheader("历史旅行攻略")
    try:
        trips = _api("GET", "/trips", headers=_auth_headers())
        if not trips:
            st.sidebar.caption("还没有保存的攻略")
        for trip in trips:
            with st.sidebar.expander(trip["title"]):
                st.caption(f"{trip['destination']} · {trip['days']} 天")
                load_col, delete_col = st.columns(2)
                if load_col.button("打开", key=f"load-{trip['id']}", use_container_width=True):
                    saved_trip = _api("GET", f"/trips/{trip['id']}", headers=_auth_headers())
                    st.session_state["trip_plan"] = saved_trip["plan"]
                    st.session_state.pop("trip_error", None)
                    st.rerun()
                if delete_col.button("删除", key=f"delete-{trip['id']}", use_container_width=True):
                    _api("DELETE", f"/trips/{trip['id']}", headers=_auth_headers())
                    st.toast("攻略已删除")
                    st.rerun()
    except (requests.RequestException, RuntimeError) as exc:
        st.sidebar.warning(str(exc))

    if st.sidebar.button("退出登录", use_container_width=True):
        for key in ("access_token", "current_user", "trip_plan", "last_trip_inputs"):
            st.session_state.pop(key, None)
        st.rerun()


if not st.session_state.get("access_token"):
    _render_login()
    st.stop()

if not st.session_state.get("current_user"):
    try:
        st.session_state["current_user"] = _api("GET", "/users/me", headers=_auth_headers())
    except (requests.RequestException, RuntimeError) as exc:
        st.error(str(exc))
        st.stop()

_render_account_sidebar()

# The existing app owns the full planner presentation. It calls set_page_config,
# which has already been called by this authenticated shell.
original_set_page_config = st.set_page_config
st.set_page_config = lambda *args, **kwargs: None
try:
    runpy.run_path(os.path.join(os.path.dirname(__file__), "streamlit_app.py"), run_name="__main__")
finally:
    st.set_page_config = original_set_page_config

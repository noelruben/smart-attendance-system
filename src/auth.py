from functools import wraps

from flask import (
    session,
    redirect,
    url_for,
    flash
)

from werkzeug.security import (
    check_password_hash
)

from src.database import (
    get_user_by_username
)


# ============================================================
# AUTHENTICATE USER
# ============================================================

def authenticate_user(
    username,
    password,
    expected_role=None
):

    username = str(
        username
    ).strip()

    user = get_user_by_username(
        username
    )

    if not user:

        return None

    if not user.get(
        "is_active"
    ):

        return None

    if (
        expected_role
        and
        user["role"] != expected_role
    ):

        return None

    if not check_password_hash(
        user["password_hash"],
        password
    ):

        return None

    return user


# ============================================================
# LOGIN USER
# ============================================================

def login_user(
    user
):

    session.clear()

    session[
        "user_id"
    ] = user["id"]

    session[
        "username"
    ] = user["username"]

    session[
        "role"
    ] = user["role"]


# ============================================================
# LOGOUT USER
# ============================================================

def logout_user():

    session.clear()


# ============================================================
# LOGIN REQUIRED
# ============================================================

def login_required(
    view
):

    @wraps(view)

    def wrapped_view(
        *args,
        **kwargs
    ):

        if (
            "user_id"
            not in session
        ):

            flash(
                "Please login to access this page.",
                "warning"
            )

            return redirect(
                url_for(
                    "home"
                )
            )

        return view(
            *args,
            **kwargs
        )

    return wrapped_view


# ============================================================
# ROLE REQUIRED
# ============================================================

def role_required(
    *allowed_roles
):

    def decorator(
        view
    ):

        @wraps(view)

        def wrapped_view(
            *args,
            **kwargs
        ):

            if (
                "user_id"
                not in session
            ):

                return redirect(
                    url_for(
                        "home"
                    )
                )

            user_role = session.get(
                "role"
            )

            if (
                user_role
                not in allowed_roles
            ):

                flash(
                    "You do not have permission "
                    "to access this page.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "dashboard"
                    )
                )

            return view(
                *args,
                **kwargs
            )

        return wrapped_view

    return decorator
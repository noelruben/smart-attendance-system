from functools import wraps

from flask import session, redirect, url_for, flash
from werkzeug.security import check_password_hash

from src.database import get_user_by_username


def authenticate_user(username, password, expected_role=None):
    """
    Authenticate a user.

    expected_role can be:
    ADMIN
    FACULTY
    STUDENT
    """

    username = str(username).strip()

    user = get_user_by_username(username)

    if not user:
        return None

    if not user.get("is_active"):
        return None

    if expected_role and user["role"] != expected_role:
        return None

    if not check_password_hash(
        user["password_hash"],
        password
    ):
        return None

    return user


def login_user(user):
    """
    Store logged-in user information in Flask session.
    """

    session.clear()

    session["user_id"] = user["id"]
    session["username"] = user["username"]
    session["role"] = user["role"]


def logout_user():
    """
    Clear the current session.
    """

    session.clear()


def login_required(view):

    @wraps(view)
    def wrapped_view(*args, **kwargs):

        if "user_id" not in session:

            flash(
                "Please login to access this page.",
                "warning"
            )

            return redirect(
                url_for("home")
            )

        return view(*args, **kwargs)

    return wrapped_view


def role_required(*allowed_roles):

    def decorator(view):

        @wraps(view)
        def wrapped_view(*args, **kwargs):

            if "user_id" not in session:

                return redirect(
                    url_for("home")
                )

            user_role = session.get("role")

            if user_role not in allowed_roles:

                flash(
                    "You do not have permission to access this page.",
                    "danger"
                )

                return redirect(
                    url_for("dashboard")
                )

            return view(*args, **kwargs)

        return wrapped_view

    return decorator
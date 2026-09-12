from database import init_db, create_user
from werkzeug.security import generate_password_hash


def create_admin():

    # Make sure database and tables exist
    init_db()

    username = "admin"

    # CHANGE THIS PASSWORD
    password = "Admin@123"

    password_hash = generate_password_hash(password)

    try:

        user_id = create_user(
            username=username,
            password_hash=password_hash,
            role="ADMIN"
        )

        print("Admin created successfully")
        print("User ID:", user_id)
        print("Username:", username)

    except Exception as e:

        print("Admin creation failed:", e)


if __name__ == "__main__":
    create_admin()
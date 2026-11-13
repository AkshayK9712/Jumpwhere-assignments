BASE = "/api/v1"


# ---------- role checks ----------
def test_guest_cannot_edit_own_account(client, make_user, bearer):
    guest = make_user("guest")
    r = client.patch(f"{BASE}/users/me", json={"name": "New"}, headers=bearer(guest))
    assert r.status_code == 403


def test_guest_can_read_own_account_and_profile(client, make_user, bearer):
    guest = make_user("guest")
    assert client.get(f"{BASE}/users/me", headers=bearer(guest)).status_code == 200
    assert client.get(f"{BASE}/users/me/profile", headers=bearer(guest)).status_code == 200


def test_user_can_update_name_and_it_is_sanitized(client, make_user, bearer):
    user = make_user("user")
    r = client.patch(f"{BASE}/users/me", json={"name": "<b>Ann</b>  Lee"}, headers=bearer(user))
    assert r.status_code == 200
    assert r.json()["name"] == "Ann Lee"


def test_update_me_rejects_null_name(client, make_user, bearer):
    user = make_user("user")
    assert client.patch(f"{BASE}/users/me", json={"name": None}, headers=bearer(user)).status_code == 422


def test_non_admin_cannot_use_admin_user_endpoints(client, make_user, bearer):
    user, other = make_user("user"), make_user("user")
    h = bearer(user)
    assert client.get(f"{BASE}/users", headers=h).status_code == 403
    assert client.get(f"{BASE}/users/{other.id}", headers=h).status_code == 403
    assert client.patch(f"{BASE}/users/{other.id}", json={"role": "admin"}, headers=h).status_code == 403
    assert client.delete(f"{BASE}/users/{other.id}", headers=h).status_code == 403


def test_user_cannot_make_themselves_admin(client, make_user, bearer):
    user = make_user("user")
    r = client.patch(f"{BASE}/users/me", json={"role": "admin"}, headers=bearer(user))
    assert r.status_code == 200 and r.json()["role"] == "user"  # unknown field is ignored


# ---------- profile ----------
def test_profile_put_and_get(client, make_user, bearer):
    user = make_user("user")
    body = {"bio": "Maintenance lead", "phone": "+91 98765 43210", "timezone": "Asia/Kolkata",
            "language": "en-IN", "preferences": {"theme": "dark"}}
    r = client.put(f"{BASE}/users/me/profile", json=body, headers=bearer(user))
    assert r.status_code == 200
    got = client.get(f"{BASE}/users/me/profile", headers=bearer(user)).json()
    assert got["timezone"] == "Asia/Kolkata" and got["preferences"] == {"theme": "dark"}


def test_profile_validation(client, make_user, bearer):
    user = make_user("user")
    h = bearer(user)
    assert client.put(f"{BASE}/users/me/profile", json={"avatar_url": "javascript:alert(1)"}, headers=h).status_code == 422
    assert client.put(f"{BASE}/users/me/profile", json={"phone": "call me"}, headers=h).status_code == 422
    assert client.put(f"{BASE}/users/me/profile", json={"language": "english"}, headers=h).status_code == 422


def test_guest_cannot_change_profile(client, make_user, bearer):
    guest = make_user("guest")
    assert client.put(f"{BASE}/users/me/profile", json={}, headers=bearer(guest)).status_code == 403


# ---------- admin user management ----------
def test_admin_lists_users_with_pagination_and_filters(client, make_user, bearer):
    admin = make_user("admin")
    make_user("user", name="Asha Rao")
    make_user("user", name="Bala Iyer")
    make_user("guest", name="Gita Nair")
    h = bearer(admin)

    page = client.get(f"{BASE}/users", params={"page_size": 2}, headers=h).json()
    assert page["total"] == 4 and page["pages"] == 2 and len(page["items"]) == 2

    guests = client.get(f"{BASE}/users", params={"role": "guest"}, headers=h).json()
    assert guests["total"] == 1

    found = client.get(f"{BASE}/users", params={"q": "asha"}, headers=h).json()
    assert [u["name"] for u in found["items"]] == ["Asha Rao"]


def test_admin_get_user_and_404(client, make_user, bearer):
    admin, user = make_user("admin"), make_user("user")
    assert client.get(f"{BASE}/users/{user.id}", headers=bearer(admin)).json()["id"] == user.id
    assert client.get(f"{BASE}/users/9999", headers=bearer(admin)).status_code == 404


def test_admin_changes_role(client, make_user, bearer):
    admin, user = make_user("admin"), make_user("user")
    r = client.patch(f"{BASE}/users/{user.id}", json={"role": "guest"}, headers=bearer(admin))
    assert r.status_code == 200 and r.json()["role"] == "guest"
    assert client.patch(f"{BASE}/users/{user.id}", json={"role": "superuser"}, headers=bearer(admin)).status_code == 422


def test_deactivated_user_is_locked_out_immediately(client, make_user, bearer):
    admin, user = make_user("admin"), make_user("user")
    user_headers = bearer(user)
    assert client.get(f"{BASE}/users/me", headers=user_headers).status_code == 200

    r = client.patch(f"{BASE}/users/{user.id}", json={"is_active": False}, headers=bearer(admin))
    assert r.status_code == 200
    assert client.get(f"{BASE}/users/me", headers=user_headers).status_code == 401


def test_admin_cannot_demote_or_deactivate_self(client, make_user, bearer):
    admin = make_user("admin")
    h = bearer(admin)
    assert client.patch(f"{BASE}/users/{admin.id}", json={"role": "user"}, headers=h).status_code == 400
    assert client.patch(f"{BASE}/users/{admin.id}", json={"is_active": False}, headers=h).status_code == 400
    # renaming yourself is fine
    assert client.patch(f"{BASE}/users/{admin.id}", json={"name": "Boss"}, headers=h).status_code == 200


def test_admin_delete_user(client, make_user, bearer):
    admin, user = make_user("admin"), make_user("user")
    h = bearer(admin)
    assert client.delete(f"{BASE}/users/{user.id}", headers=h).status_code == 204
    assert client.get(f"{BASE}/users/{user.id}", headers=h).status_code == 404


def test_admin_cannot_delete_self(client, make_user, bearer):
    admin = make_user("admin")
    assert client.delete(f"{BASE}/users/{admin.id}", headers=bearer(admin)).status_code == 400

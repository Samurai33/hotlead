import asyncio
import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api.v1.accounts import add_account
from app.schemas.account import AccountCreate


@pytest.mark.asyncio
async def test_add_account(client):
    resp = await client.post(
        "/api/v1/accounts",
        json={
            "username": "test_account_x1",
            "session_json": '{"device_id": "test"}',
            "proxy_url": "http://user:pass@proxy.example.com:8080",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == "test_account_x1"
    assert "session_json" not in data


@pytest.mark.asyncio
async def test_add_account_without_proxy_rejected(client):
    """audit C1: a proxy-less account shares the deployment host's IP with every
    other proxy-less account — a multi-accounting signal to Instagram."""
    resp = await client.post(
        "/api/v1/accounts",
        json={"username": "no_proxy_acc_x1", "session_json": '{"device_id": "test"}'},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_add_duplicate_account(client):
    await client.post(
        "/api/v1/accounts",
        json={
            "username": "duplicate_acc_x1",
            "session_json": '{"device_id": "test1"}',
            "proxy_url": "http://user:pass@proxy.example.com:8080",
        },
    )
    resp = await client.post(
        "/api/v1/accounts",
        json={
            "username": "duplicate_acc_x1",
            "session_json": '{"device_id": "test2"}',
            "proxy_url": "http://user:pass@proxy.example.com:8080",
        },
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_list_accounts(client):
    resp = await client.get("/api/v1/accounts")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_session_json_never_exposed(client):
    resp = await client.post(
        "/api/v1/accounts",
        json={
            "username": "secret_acc_x1",
            "session_json": '{"password_equivalent": "NEVER_LEAK_THIS"}',
            "proxy_url": "http://user:pass@proxy.example.com:8080",
        },
    )
    assert resp.status_code == 201
    assert "NEVER_LEAK_THIS" not in resp.text
    assert "session_json" not in resp.json()


@pytest.mark.asyncio
async def test_session_json_encrypted_at_rest(client, db):
    """audit C2: session_json must never be stored in plaintext."""
    from sqlalchemy import text

    plaintext = '{"password_equivalent": "NEVER_STORE_PLAINTEXT"}'
    resp = await client.post(
        "/api/v1/accounts",
        json={
            "username": "encrypted_acc_x1",
            "session_json": plaintext,
            "proxy_url": "http://user:pass@proxy.example.com:8080",
        },
    )
    acc_id = resp.json()["id"]

    raw = await db.execute(text("SELECT session_json FROM accounts WHERE id = :id"), {"id": acc_id})
    stored = raw.scalar_one()
    assert stored != plaintext
    assert "NEVER_STORE_PLAINTEXT" not in stored


@pytest.mark.asyncio
async def test_delete_account(client):
    add = await client.post(
        "/api/v1/accounts",
        json={
            "username": "to_delete_x1",
            "session_json": '{"device_id": "test"}',
            "proxy_url": "http://user:pass@proxy.example.com:8080",
        },
    )
    acc_id = add.json()["id"]
    resp = await client.delete(f"/api/v1/accounts/{acc_id}")
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_delete_nonexistent(client):
    resp = await client.delete(f"/api/v1/accounts/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_add_account_slashless_no_redirect(client):
    """Regression guard, same reasoning as test_jobs.test_create_job_slashless_no_redirect:
    a 307 hop here used to carry a Location: http://... that real browsers block as mixed
    content (Traefik reports scheme=http; TLS terminates at the Cloudflare edge)."""
    resp = await client.post(
        "/api/v1/accounts",
        json={
            "username": "noredirect_acc_x1",
            "session_json": '{"device_id": "test"}',
            "proxy_url": "http://user:pass@proxy.example.com:8080",
        },
    )
    assert resp.status_code == 201
    assert resp.history == []


@pytest.mark.asyncio
async def test_list_accounts_slashless_no_redirect(client):
    resp = await client.get("/api/v1/accounts")
    assert resp.status_code == 200
    assert resp.history == []


@pytest.mark.asyncio
async def test_add_account_oversized_username_rejected(client):
    """audit B7: username backs a String(150) column -- oversized input
    must 422 from Pydantic, not 500 from an unhandled
    StringDataRightTruncation at INSERT time."""
    resp = await client.post(
        "/api/v1/accounts",
        json={
            "username": "x" * 151,
            "session_json": '{"device_id": "test"}',
            "proxy_url": "http://user:pass@proxy.example.com:8080",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_accounts_pagination(client):
    """audit B5: GET /accounts had no pagination at all -- match
    prospects.list_prospects's limit/offset pattern."""
    usernames = ["paginate_acc_0_x1", "paginate_acc_1_x1", "paginate_acc_2_x1"]
    ids = []
    for username in usernames:
        resp = await client.post(
            "/api/v1/accounts",
            json={
                "username": username,
                "session_json": '{"device_id": "test"}',
                "proxy_url": "http://user:pass@proxy.example.com:8080",
            },
        )
        assert resp.status_code == 201
        ids.append(resp.json()["id"])

    page1 = await client.get("/api/v1/accounts", params={"limit": 2, "offset": 0})
    assert page1.status_code == 200
    page1_data = page1.json()
    assert len(page1_data) == 2
    # created_at desc -- the two most recently created accounts (ids[2], ids[1])
    # must be the first page.
    assert page1_data[0]["id"] == ids[2]
    assert page1_data[1]["id"] == ids[1]

    page2 = await client.get("/api/v1/accounts", params={"limit": 2, "offset": 2})
    assert page2.status_code == 200
    page2_data = page2.json()
    assert page2_data[0]["id"] == ids[0]

    assert {a["id"] for a in page1_data}.isdisjoint(a["id"] for a in page2_data)


@pytest.mark.asyncio
async def test_list_accounts_limit_out_of_range_rejected(client):
    resp = await client.get("/api/v1/accounts", params={"limit": 0})
    assert resp.status_code == 422

    resp = await client.get("/api/v1/accounts", params={"limit": 501})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_add_account_oversized_proxy_url_rejected(client):
    """audit B7: proxy_url backs a String(500) column."""
    oversized_proxy = "http://user:pass@" + ("a" * 490) + ".example.com:8080"
    assert len(oversized_proxy) > 500
    resp = await client.post(
        "/api/v1/accounts",
        json={
            "username": "oversized_proxy_acc_x1",
            "session_json": '{"device_id": "test"}',
            "proxy_url": oversized_proxy,
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_add_account_oversized_locale_rejected(client):
    """audit B7: locale backs a String(10) column."""
    resp = await client.post(
        "/api/v1/accounts",
        json={
            "username": "oversized_locale_acc_x1",
            "session_json": '{"device_id": "test"}',
            "proxy_url": "http://user:pass@proxy.example.com:8080",
            "locale": "x" * 11,
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_concurrent_add_account_same_username_returns_409_not_500(engine):
    """audit B6: the duplicate-username check is a SELECT then INSERT, not
    atomic. Two concurrent POSTs for a brand-new username can both pass the
    SELECT before either commits its INSERT; the loser must hit a clean 409
    (via the DB's unique constraint + the endpoint's IntegrityError handling),
    never a bare 500.

    Uses two independent real AsyncSessions calling add_account() directly
    (an AsyncSession isn't safe for concurrent use, so the shared `client`/`db`
    fixtures can't drive real concurrent HTTP calls here) and a barrier that
    forces both sessions' duplicate-check SELECTs to complete -- both seeing
    no existing row -- before either proceeds to INSERT, faithfully
    reproducing the race window described in the finding.
    """
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    db_a = session_factory()
    db_b = session_factory()

    barrier = asyncio.Barrier(2)
    checked = {"a": False, "b": False}

    def _wrap(session, key):
        real_execute = session.execute

        async def wrapper(*args, **kwargs):
            result = await real_execute(*args, **kwargs)
            if not checked[key]:
                checked[key] = True
                await barrier.wait()
            return result

        return wrapper

    db_a.execute = _wrap(db_a, "a")
    db_b.execute = _wrap(db_b, "b")

    payload = AccountCreate(
        username="race_acc_x1",
        session_json='{"device_id": "test"}',
        proxy_url="http://user:pass@proxy.example.com:8080",
    )

    try:
        results = await asyncio.gather(
            add_account(payload, db=db_a),
            add_account(payload, db=db_b),
            return_exceptions=True,
        )
    finally:
        # Whichever session lost the race already rolled itself back inside
        # add_account's except block -- both should be clean here.
        cleanup = session_factory()
        try:
            from sqlalchemy import delete

            from app.models.account import Account

            await cleanup.execute(delete(Account).where(Account.username == "race_acc_x1"))
            await cleanup.commit()
        finally:
            await cleanup.close()
        await db_a.close()
        await db_b.close()

    statuses = []
    for r in results:
        if isinstance(r, HTTPException):
            statuses.append(r.status_code)
        elif isinstance(r, BaseException):
            raise r
        else:
            statuses.append(201)

    assert sorted(statuses) == [201, 409]

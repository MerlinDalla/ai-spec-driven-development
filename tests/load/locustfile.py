from __future__ import annotations

import random
import string

from locust import HttpUser, between, task


def random_account_number():
    chars = string.ascii_uppercase + string.digits
    return "ACCT-" + "".join(random.choices(chars, k=12))


class AccountUser(HttpUser):
    wait_time = between(0.1, 1.0)
    host = "http://localhost:8000"

    def on_start(self):
        self.headers = {"Authorization": "Bearer test-token"}
        self.account_number = None

    @task(1)
    def create_account(self):
        payload = {
            "owner_id": f"user-{random.randint(1, 10000)}",
            "currency": random.choice(["EUR", "USD", "GBP"]),
            "opening_balance": "1000.0000",
        }
        with self.client.post(
            "/api/v1/accounts",
            json=payload,
            headers=self.headers,
            catch_response=True,
        ) as resp:
            if resp.status_code == 201:
                self.account_number = resp.json().get("account_number")
                resp.success()
            else:
                resp.failure(f"Unexpected status {resp.status_code}")

    @task(3)
    def get_balance(self):
        if not self.account_number:
            return
        with self.client.get(
            f"/api/v1/accounts/{self.account_number}",
            headers=self.headers,
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 403, 404):
                resp.success()
            else:
                resp.failure(f"Unexpected status {resp.status_code}")


class TransferUser(HttpUser):
    wait_time = between(0.2, 1.0)
    host = "http://localhost:8000"

    def on_start(self):
        self.headers = {"Authorization": "Bearer test-token"}
        self.src_account = None
        self.dst_account = None

    @task(2)
    def transfer(self):
        if not self.src_account or not self.dst_account:
            return
        import uuid

        with self.client.post(
            "/api/v1/transfers",
            json={
                "source_account_number": self.src_account,
                "destination_account_number": self.dst_account,
                "amount": "10.0000",
            },
            headers={**self.headers, "X-Idempotency-Key": str(uuid.uuid4())},
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 201, 422):
                resp.success()
            else:
                resp.failure(f"Unexpected status {resp.status_code}")

from __future__ import annotations

from datetime import datetime

from ig_post_controller.database import Database
from ig_post_controller.models import AccountRecord


class AccountService:
    def __init__(self, database: Database) -> None:
        self.database = database

    def list_accounts(self) -> list[AccountRecord]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM accounts
                WHERE archived = 0
                ORDER BY company_name COLLATE NOCASE, username COLLATE NOCASE
                """
            ).fetchall()
        return [self._row_to_account(row) for row in rows]

    def get_account(self, account_id: int) -> AccountRecord | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM accounts WHERE id = ?",
                (account_id,),
            ).fetchone()
        return self._row_to_account(row) if row else None

    def save_account(
        self,
        *,
        profile_url: str,
        username: str,
        display_name: str,
        company_name: str,
    ) -> AccountRecord:
        now = datetime.now().isoformat()
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO accounts (
                    profile_url,
                    username,
                    display_name,
                    company_name,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(username) DO UPDATE SET
                    profile_url = excluded.profile_url,
                    display_name = excluded.display_name,
                    company_name = excluded.company_name,
                    archived = 0,
                    updated_at = excluded.updated_at
                """,
                (profile_url, username, display_name, company_name, now, now),
            )
            row = connection.execute(
                "SELECT * FROM accounts WHERE username = ?",
                (username,),
            ).fetchone()
        return self._row_to_account(row)

    def delete_account(self, account_id: int) -> None:
        """Remove an account from the active list without losing downloaded records."""
        with self.database.connect() as connection:
            has_downloads = connection.execute(
                """
                SELECT 1
                FROM downloads d
                JOIN posts p ON p.id = d.post_id
                WHERE p.account_id = ?
                LIMIT 1
                """,
                (account_id,),
            ).fetchone()
            if has_downloads:
                connection.execute(
                    "UPDATE accounts SET archived = 1, updated_at = ? WHERE id = ?",
                    (datetime.now().isoformat(), account_id),
                )
            else:
                connection.execute("DELETE FROM accounts WHERE id = ?", (account_id,))

    def update_last_checked(
        self,
        account_id: int,
        *,
        last_checked_at: datetime,
        last_seen_post_shortcode: str | None = None,
        display_name: str | None = None,
    ) -> None:
        with self.database.connect() as connection:
            connection.execute(
                """
                UPDATE accounts
                SET
                    last_checked_at = ?,
                    last_seen_post_shortcode = COALESCE(?, last_seen_post_shortcode),
                    display_name = COALESCE(?, display_name),
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    last_checked_at.isoformat(),
                    last_seen_post_shortcode,
                    display_name,
                    datetime.now().isoformat(),
                    account_id,
                ),
            )

    @staticmethod
    def _row_to_account(row) -> AccountRecord:
        return AccountRecord(
            id=row["id"],
            profile_url=row["profile_url"],
            username=row["username"],
            display_name=row["display_name"],
            company_name=row["company_name"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            last_checked_at=datetime.fromisoformat(row["last_checked_at"]) if row["last_checked_at"] else None,
            last_seen_post_shortcode=row["last_seen_post_shortcode"],
        )

from app.core.database import get_connection


def save_batch_log(
    endpoint: str,
    items_count: int,
    success_count: int,
    error_count: int,
    client_ip: str | None,
    user_agent: str | None,
) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO api_batch_logs (
                endpoint,
                items_count,
                success_count,
                error_count,
                client_ip,
                user_agent
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                endpoint,
                items_count,
                success_count,
                error_count,
                client_ip,
                user_agent,
            ),
        )
        connection.commit()

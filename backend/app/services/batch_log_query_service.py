from app.core.database import get_connection
from typing import Optional

def query_batch_logs(
    limit: int = 50,
    offset: int = 0,
    endpoint: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> list[dict]:
    """
    Récupère les logs batch API avec filtres optionnels.
    - limit: nombre max de résultats
    - offset: décalage pour pagination
    - endpoint: filtre sur l'endpoint
    - date_from/date_to: bornes sur created_at (format 'YYYY-MM-DD')
    """
    query = "SELECT * FROM api_batch_logs WHERE 1=1"
    params = []
    if endpoint:
        query += " AND endpoint = ?"
        params.append(endpoint)
    if date_from:
        query += " AND date(created_at) >= date(?)"
        params.append(date_from)
    if date_to:
        query += " AND date(created_at) <= date(?)"
        params.append(date_to)
    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    with get_connection() as connection:
        rows = connection.execute(query, params).fetchall()
        return [dict(row) for row in rows]

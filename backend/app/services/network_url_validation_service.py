from urllib.parse import urlsplit, urlunsplit


ALLOWED_NETWORK_SCHEMES = {"rtsp", "http", "https"}


def sanitize_network_host(host: str) -> str:
    cleaned = host.strip()
    if not cleaned:
        raise ValueError("Host camera requis")
    if any(char in cleaned for char in {"/", "\\", "@", "?", "#"}):
        raise ValueError("Host camera invalide")
    return cleaned


def sanitize_network_path(path: str) -> str:
    cleaned = path.strip() or "/"
    if any(char in cleaned for char in {"\\", "#"}):
        raise ValueError("Chemin camera invalide")
    if not cleaned.startswith("/"):
        cleaned = f"/{cleaned}"
    return cleaned


def validate_network_stream_url(url: str) -> str:
    cleaned = url.strip()
    if not cleaned:
        raise ValueError("URL camera requise")

    parts = urlsplit(cleaned)
    scheme = parts.scheme.lower()
    if scheme not in ALLOWED_NETWORK_SCHEMES:
        raise ValueError("Schema camera non supporte")
    if not parts.netloc:
        raise ValueError("URL camera invalide")
    if parts.username or parts.password:
        # Credentials in authority are supported, but the host section must still be well-formed.
        pass
    if any(char in parts.hostname or "" for char in {"/", "\\", "@", "?", "#"}):
        raise ValueError("Host camera invalide")
    if parts.path and "\\" in parts.path:
        raise ValueError("Chemin camera invalide")

    normalized_path = parts.path
    normalized = urlunsplit(
        (
            scheme,
            parts.netloc,
            normalized_path,
            parts.query,
            parts.fragment,
        )
    )
    return normalized

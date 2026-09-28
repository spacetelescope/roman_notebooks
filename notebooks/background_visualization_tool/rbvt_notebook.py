"""Connection setup for embedding RBVT in a Jupyter notebook."""

import os
from pathlib import Path
from urllib.parse import urlsplit

import requests
from ipykernel.connect import get_connection_file
from jupyter_server.serverapp import list_running_servers


def _origin(url):
    """Accept an HTTP(S) origin without credentials, paths, or tokens."""
    parsed = urlsplit(url)
    if (parsed.scheme not in {"http", "https"} or not parsed.hostname
            or parsed.username or parsed.password or parsed.query
            or parsed.fragment or parsed.path not in {"", "/"}):
        raise ValueError(
            "NOTEBOOK_URL must contain only a scheme, hostname, and optional "
            "port, for example http://localhost:8890."
        )
    # Accessing port also validates its syntax and range.
    parsed.port
    return f"{parsed.scheme}://{parsed.netloc}"


def notebook_show_options(notebook_url=None):
    """Return Bokeh show options, matching the kernel to its local server.

    Bokeh handles JUPYTER_BOKEH_EXTERNAL_URL itself. Local discovery is
    best-effort: server authentication or a different browser-facing hostname
    can require an explicit notebook_url instead.
    """
    if os.environ.get("JUPYTER_BOKEH_EXTERNAL_URL"):
        if notebook_url is not None:
            raise ValueError(
                "JUPYTER_BOKEH_EXTERNAL_URL is configured by this deployment. "
                "Leave NOTEBOOK_URL = None to use its Bokeh proxy."
            )
        return {}
    if notebook_url is not None:
        return {"notebook_url": _origin(notebook_url)}

    matches = set()
    try:
        kernel_id = Path(get_connection_file()).stem.removeprefix("kernel-")
        for server in list_running_servers():
            url = server.get("url", "")
            parsed = urlsplit(url)
            if parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
                continue
            headers = {}
            if server.get("token"):
                headers["Authorization"] = f"token {server['token']}"
            try:
                response = requests.get(
                    url.rstrip("/") + "/api/sessions",
                    headers=headers, timeout=(2, 3), allow_redirects=False,
                )
                response.raise_for_status()
                sessions = response.json()
                if not isinstance(sessions, list):
                    continue
                if any(session.get("kernel", {}).get("id") == kernel_id
                       for session in sessions):
                    matches.add(_origin(f"{parsed.scheme}://{parsed.netloc}"))
            except (requests.RequestException, ValueError, AttributeError):
                continue
    except (OSError, RuntimeError):
        pass

    if len(matches) == 1:
        origin = matches.pop()
        print(f"Using Jupyter server {origin} for RBVT.")
        return {"notebook_url": origin}
    raise RuntimeError(
        "Could not uniquely identify this kernel's local Jupyter server. "
        "Set NOTEBOOK_URL to the scheme, hostname, and port shown in your "
        "browser (for example http://localhost:8890), then rerun the launch "
        "cell. For Nexus/JupyterHub, use the deployment's Bokeh proxy setup."
    )

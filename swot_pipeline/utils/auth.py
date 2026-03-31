from __future__ import annotations

import netrc
import os
from pathlib import Path

import requests

from swot_pipeline.models import AuthConfig

EARTHDATA_HOST = "urs.earthdata.nasa.gov"


def resolve_earthdata_credentials(auth: AuthConfig) -> tuple[str | None, str | None]:
    if auth.earthdata_username and auth.earthdata_password:
        return auth.earthdata_username, auth.earthdata_password

    env_user = os.getenv("EARTHDATA_USERNAME")
    env_pass = os.getenv("EARTHDATA_PASSWORD")
    if env_user and env_pass:
        return env_user, env_pass

    netrc_path = auth.netrc_path or Path.home() / ".netrc"
    if netrc_path.exists():
        info = netrc.netrc(str(netrc_path)).authenticators(EARTHDATA_HOST)
        if info is not None:
            login, _, password = info
            return login, password

    return None, None


def build_earthdata_session(auth: AuthConfig) -> requests.Session:
    user, password = resolve_earthdata_credentials(auth)
    session = requests.Session()
    if user and password:
        session.auth = (user, password)
    return session


def configure_gcp_credentials(auth: AuthConfig) -> None:
    if auth.gcp_credentials_path:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(auth.gcp_credentials_path)


def initialize_earth_engine(auth: AuthConfig, project_id: str | None = None) -> None:
    try:
        import ee
    except ImportError as exc:
        raise RuntimeError(
            "earthengine-api is required for publish steps. Install with pip install earthengine-api"
        ) from exc

    if auth.ee_service_account and auth.ee_private_key_path:
        credentials = ee.ServiceAccountCredentials(auth.ee_service_account, str(auth.ee_private_key_path))
        ee.Initialize(credentials, project=project_id)
    else:
        # If user has already authenticated via `earthengine authenticate`, this is enough.
        ee.Initialize(project=project_id)

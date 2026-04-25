import logging
import os
from pathlib import Path
from typing import Any

import msal
import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
TOKEN_CACHE_PATH = Path("./token_cache.json")
SCOPES = [
    "https://graph.microsoft.com/Notes.Read",
    "https://graph.microsoft.com/Notes.Read.All",
    "https://graph.microsoft.com/User.Read",
]

class GraphClient:
    """Microsoft Graph API client for OneNote access.

    Authenticates via MSAL Device Code Flow and exposes methods for
    traversing OneNote notebooks, sections, pages, and page content.
    """

    def __init__(self) -> None:
        """Initialize GraphClient from environment variables.

        Reads AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, and AZURE_TENANT_ID
        from the environment (via .env). Device Code Flow uses only
        client_id and tenant_id; client_secret is stored for reference.

        Raises:
            ValueError: If any required environment variable is missing.
        """
        self.client_id = os.getenv("AZURE_CLIENT_ID")
        self.client_secret = os.getenv("AZURE_CLIENT_SECRET")
        self.tenant_id = os.getenv("AZURE_TENANT_ID")

        missing = [
            name
            for name, val in [
                ("AZURE_CLIENT_ID", self.client_id),
                ("AZURE_CLIENT_SECRET", self.client_secret),
                ("AZURE_TENANT_ID", self.tenant_id),
            ]
            if not val
        ]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

        self._cache = self._load_cache()
        self._app = msal.PublicClientApplication(
            client_id=self.client_id,
            authority=f"https://login.microsoftonline.com/consumers",
            token_cache=self._cache,
        )
        self._access_token: str | None = None

    # ------------------------------------------------------------------
    # Token cache helpers
    # ------------------------------------------------------------------

    def _load_cache(self) -> msal.SerializableTokenCache:
        """Load the MSAL token cache from disk.

        Returns:
            A SerializableTokenCache populated from TOKEN_CACHE_PATH if it
            exists, or an empty cache otherwise.
        """
        cache = msal.SerializableTokenCache()
        if TOKEN_CACHE_PATH.exists():
            cache.deserialize(TOKEN_CACHE_PATH.read_text(encoding="utf-8"))
        return cache

    def _save_cache(self) -> None:
        """Persist the MSAL token cache to disk when it has changed."""
        if self._cache.has_state_changed:
            TOKEN_CACHE_PATH.write_text(self._cache.serialize(), encoding="utf-8")

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def authenticate(self) -> None:
        """Authenticate the user via Device Code Flow.

        Tries a silent token refresh using any cached account first.
        Falls back to the interactive Device Code Flow if no valid token
        is available. Prints the device-code URL and user code to stdout.

        Raises:
            RuntimeError: If the device flow cannot be initiated or the
                token acquisition fails.
        """
        result: dict | None = None

        accounts = self._app.get_accounts()
        if accounts:
            result = self._app.acquire_token_silent(SCOPES, account=accounts[0])
            if result:
                logger.info("Token acquired from cache.")

        if not result:
            flow = self._app.initiate_device_flow(scopes=SCOPES)
            if "user_code" not in flow:
                raise RuntimeError(
                    f"Failed to initiate device flow: {flow.get('error_description', flow)}"
                )
            print("\n" + flow["message"] + "\n")
            result = self._app.acquire_token_by_device_flow(flow)

        if "access_token" not in result:
            raise RuntimeError(
                f"Authentication failed: {result.get('error_description', result)}"
            )

        self._access_token = result["access_token"]
        self._save_cache()
        logger.info("Authentication successful.")

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        """Build the Authorization headers for Graph API requests.

        Returns:
            Dictionary containing 'Authorization' and 'Content-Type' headers.

        Raises:
            RuntimeError: If authenticate() has not been called yet.
        """
        if not self._access_token:
            raise RuntimeError("Not authenticated. Call authenticate() first.")
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }

    def _get(self, url: str, params: dict[str, Any] | None = None) -> Any:
        """Send a GET request to the Microsoft Graph API.

        Args:
            url: Full URL or a path relative to GRAPH_BASE_URL.
            params: Optional OData query parameters.

        Returns:
            Parsed JSON response body.

        Raises:
            RuntimeError: If the HTTP response status is not 200.
        """
        if not url.startswith("http"):
            url = f"{GRAPH_BASE_URL}/{url.lstrip('/')}"

        response = requests.get(url, headers=self._headers(), params=params, timeout=30)

        if response.status_code != 200:
            raise RuntimeError(
                f"Graph API request failed [{response.status_code}]: {response.text[:300]}"
            )

        return response.json()

    def _get_paginated(
        self, url: str, params: dict[str, Any] | None = None
    ) -> list[dict]:
        """Fetch all items from a paginated Graph API endpoint.

        Follows '@odata.nextLink' until all pages are consumed.

        Args:
            url: Initial endpoint URL.
            params: OData query parameters applied only to the first request.

        Returns:
            Aggregated list of all items across every page.
        """
        items: list[dict] = []
        next_url: str | None = url

        while next_url:
            data = self._get(next_url, params=params if next_url == url else None)
            items.extend(data.get("value", []))
            next_url = data.get("@odata.nextLink")

        return items

    # ------------------------------------------------------------------
    # OneNote API methods
    # ------------------------------------------------------------------

    def get_notebooks(self) -> list[dict]:
        """Retrieve all OneNote notebooks for the authenticated user.

        Returns:
            List of notebook objects. Each dict contains at least:
                - id (str): Unique notebook identifier.
                - displayName (str): Human-readable notebook name.
                - lastModifiedDateTime (str): ISO 8601 timestamp.
        """
        notebooks = self._get_paginated(
            f"{GRAPH_BASE_URL}/me/onenote/notebooks",
            params={"$select": "id,displayName,lastModifiedDateTime"},
        )
        logger.info("get_notebooks: found %d notebooks.", len(notebooks))
        return notebooks

    def get_sections(self, notebook_id: str) -> list[dict]:
        """Retrieve all sections within a specific notebook.

        Args:
            notebook_id: Unique identifier of the parent notebook.

        Returns:
            List of section objects. Each dict contains at least:
                - id (str): Unique section identifier.
                - displayName (str): Human-readable section name.
                - lastModifiedDateTime (str): ISO 8601 timestamp.
        """
        sections = self._get_paginated(
            f"{GRAPH_BASE_URL}/me/onenote/notebooks/{notebook_id}/sections",
            params={"$select": "id,displayName,lastModifiedDateTime"},
        )
        logger.info(
            "get_sections: found %d sections in notebook %s.", len(sections), notebook_id
        )
        return sections

    def get_pages(self, section_id: str) -> list[dict]:
        """Retrieve all pages within a specific section.

        Args:
            section_id: Unique identifier of the parent section.

        Returns:
            List of page objects. Each dict contains at least:
                - id (str): Unique page identifier.
                - title (str): Page title.
                - lastModifiedDateTime (str): ISO 8601 timestamp.
                - contentUrl (str): URL for fetching raw HTML content.
        """
        pages = self._get_paginated(
            f"{GRAPH_BASE_URL}/me/onenote/sections/{section_id}/pages",
            params={"$select": "id,title,lastModifiedDateTime,contentUrl"},
        )
        logger.info(
            "get_pages: found %d pages in section %s.", len(pages), section_id
        )
        return pages

    def get_page_content(self, page_id: str) -> str:
        """Retrieve the raw HTML content of a OneNote page.

        Args:
            page_id: Unique identifier of the page.

        Returns:
            Raw HTML string of the page body.

        Raises:
            RuntimeError: If the Graph API returns a non-200 status.
        """
        DEBUG_PAGE_ID = "0-14416366c9ee8a41b3649341ee22a1a5!1-9A56316C81C30D3!183"

        url = f"{GRAPH_BASE_URL}/me/onenote/pages/{page_id}/content"
        response = requests.get(url, headers=self._headers(), timeout=30)

        if page_id == DEBUG_PAGE_ID:
            print(f"\n[DEBUG] page_id     : {page_id}")
            print(f"[DEBUG] status_code : {response.status_code}")
            print(f"[DEBUG] Content-Type: {response.headers.get('Content-Type', 'N/A')}")
            print(f"[DEBUG] body length : {len(response.text)} chars")
            print(f"[DEBUG] body preview: {repr(response.text[:500])}\n")

        if response.status_code != 200:
            raise RuntimeError(
                f"Failed to fetch content for page {page_id} "
                f"[{response.status_code}]: {response.text[:300]}"
            )

        return response.text

    def get_all_pages_metadata(self) -> list[dict]:
        """Build a flat list of metadata for every page across all notebooks.

        Traverses notebooks → sections → pages and enriches each page entry
        with its parent notebook and section details.

        Returns:
            List of metadata dicts, one per page. Each dict contains:
                - page_id (str): Unique page identifier.
                - page_title (str): Page title.
                - last_modified (str): ISO 8601 last-modified timestamp.
                - content_url (str): URL to retrieve raw HTML content.
                - section_id (str): Parent section identifier.
                - section_name (str): Parent section display name.
                - notebook_id (str): Parent notebook identifier.
                - notebook_name (str): Parent notebook display name.
        """
        all_pages: list[dict] = []

        for notebook in self.get_notebooks():
            notebook_id: str = notebook["id"]
            notebook_name: str = notebook.get("displayName", "")

            for section in self.get_sections(notebook_id):
                section_id: str = section["id"]
                section_name: str = section.get("displayName", "")

                for page in self.get_pages(section_id):
                    all_pages.append(
                        {
                            "page_id": page["id"],
                            "page_title": page.get("title", ""),
                            "last_modified": page.get("lastModifiedDateTime", ""),
                            "content_url": page.get("contentUrl", ""),
                            "section_id": section_id,
                            "section_name": section_name,
                            "notebook_id": notebook_id,
                            "notebook_name": notebook_name,
                        }
                    )

        logger.info("get_all_pages_metadata: total pages found = %d.", len(all_pages))
        return all_pages


if __name__ == "__main__":
    client = GraphClient()
    print("=== 인증 시작 ===")
    client.authenticate()
    print("=== 인증 완료 ===")
    notebooks = client.get_notebooks()
    print(f"노트북 수: {len(notebooks)}")
    for nb in notebooks:
        print(f"  - {nb['displayName']}")
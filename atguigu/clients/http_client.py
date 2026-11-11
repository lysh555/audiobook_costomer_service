from httpx import AsyncClient


class LazyHttpClient:
    def __init__(self):
        self._client: AsyncClient | None = None

    @property
    def client(self) -> AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = AsyncClient()
        return self._client

    def __getattr__(self, item: str):
        return getattr(self.client, item)


http_client = LazyHttpClient()


def init_http_client():
    http_client.client


async def close_http_client():
    if http_client._client is not None:
        await http_client._client.aclose()
        http_client._client = None
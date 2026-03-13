import asyncio
import json
import logging
import ssl

_LOGGER = logging.getLogger(__name__)


class NymeaAuthError(Exception):
    """Raised when authentication fails."""


class NymeaConnectionError(Exception):
    """Raised when the connection to Nymea cannot be established."""


class NymeaClient:

    def __init__(self, host: str, port: int, username: str, password: str):
        self.host = host
        self.port = port
        self.username = username
        self.password = password

        self.reader: asyncio.StreamReader | None = None
        self.writer: asyncio.StreamWriter | None = None
        self.token: str | None = None
        self._rpc_id = 0

        self.ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        # Reset the RPC id counter – the server starts at 1 on every new connection
        self._rpc_id = 0

        try:
            self.reader, self.writer = await asyncio.wait_for(
                asyncio.open_connection(
                    self.host, self.port,
                    ssl=self.ssl_context,
                    limit=4 * 1024 * 1024,
                ),
                timeout=10,
            )
            _LOGGER.debug("Connected to Nymea at %s:%s", self.host, self.port)
        except (OSError, asyncio.TimeoutError) as err:
            raise NymeaConnectionError(
                f"Cannot connect to {self.host}:{self.port}: {err}"
            ) from err

    def is_connected(self) -> bool:
        return self.writer is not None and not self.writer.is_closing()

    async def close_connection(self) -> None:
        """Close the TCP connection but keep the token for reuse."""
        if self.writer:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except Exception:
                pass
        self.reader = None
        self.writer = None

    async def disconnect(self) -> None:
        """Close connection and clear token (full reset)."""
        if self.writer:
            try:
                self.writer.close()
                # wait_closed() can hang if server already closed – use timeout
                await asyncio.wait_for(self.writer.wait_closed(), timeout=2)
            except Exception:
                pass
        self.reader = None
        self.writer = None
        self.token = None

    # ------------------------------------------------------------------
    # Low-level RPC
    # ------------------------------------------------------------------

    async def send(self, payload: dict) -> dict:
        """Send a request and return the matching response."""
        if not self.is_connected():
            await self.connect()

        self._rpc_id += 1
        expected_id = self._rpc_id
        payload["id"] = expected_id

        try:
            self.writer.write((json.dumps(payload) + "\n").encode())
            await self.writer.drain()
        except OSError as err:
            raise NymeaConnectionError(f"Send failed: {err}") from err

        attempts = 0
        while True:
            attempts += 1
            if attempts > 100:
                raise NymeaConnectionError("Too many unmatched responses")
            try:
                line = await asyncio.wait_for(self.reader.readline(), timeout=15)
            except asyncio.TimeoutError as err:
                raise NymeaConnectionError("Read timed out") from err

            if not line:
                raise NymeaConnectionError("Nymea closed the connection")

            response = json.loads(line.decode())
            if response.get("id") == expected_id:
                return response

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    async def authenticate(self) -> None:
        if not self.is_connected():
            await self.connect()

        await self.send({"method": "JSONRPC.Hello"})

        auth = await self.send({
            "method": "JSONRPC.Authenticate",
            "params": {
                "username": self.username,
                "password": self.password,
                "deviceName": "HomeAssistant",
            },
        })

        params = auth.get("params", {})
        if not params.get("success", False):
            raise NymeaAuthError(f"Authentication failed: {auth!r}")

        self.token = params["token"]
        _LOGGER.debug("Authenticated with Nymea")

    # ------------------------------------------------------------------
    # High-level API
    # ------------------------------------------------------------------

    async def get_thing_classes(self) -> dict[str, dict]:
        if not self.token:
            await self.authenticate()

        response = await self.send({
            "method": "Integrations.GetThingClasses",
            "token": self.token,
        })

        thing_classes = response.get("params", {}).get("thingClasses", [])
        _LOGGER.debug("Fetched %d thing classes", len(thing_classes))
        return {tc["id"]: tc for tc in thing_classes if "id" in tc}

    async def get_things(self) -> list[dict]:
        if not self.token:
            await self.authenticate()

        response = await self.send({
            "method": "Integrations.GetThings",
            "token": self.token,
        })
        things = response.get("params", {}).get("things", [])
        _LOGGER.debug("Fetched %d things", len(things))
        return things

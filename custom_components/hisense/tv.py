"""Hisense TV cloud API support."""

from __future__ import annotations

import logging
import time
from typing import Any

_LOGGER = logging.getLogger(__name__)

_TV_DEVICE_INFO_URL = "https://public-wxtv.hismarttv.com/mobiletv/device/deviceInfo"
_REFRESH_URL = "https://bas-wg.hismarttv.com/aaa/refresh_token2"
_TV_CLIENT_DEVICE_ID = "o8zDV5ekrW3UoG3darGHXYPWGRbw"

_TV_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "*/*",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/132.0.0.0 Safari/537.36"
    ),
    "Referer": "https://servicewechat.com/wxf488d623a17cd7b5/69/page-frame.html",
}

_REFRESH_HEADERS = {
    "Host": "bas-wg.hismarttv.com",
    "Content-Type": "application/x-www-form-urlencoded",
    "Connection": "keep-alive",
    "Accept": "*/*",
}


def _timestamp() -> int:
    return int(time.time() * 1000)


def _tv_payload(access_token: str, device_id: str) -> dict[str, Any]:
    return {
        "_t": _timestamp(),
        "accessToken": access_token,
        "deviceIds": [device_id],
        "version": "1.2.20.3",
        "deviceType": 3,
        "type": 1,
        "deviceid": _TV_CLIENT_DEVICE_ID,
        "distributeId": 1001,
        "sign": "",
        "appKey": "commonweb",
    }


async def get_tv_device_info(session, access_token: str, device_id: str):
    """Return validated TV deviceInfo response, or None on failure."""
    try:
        async with session.post(
            _TV_DEVICE_INFO_URL,
            headers=_TV_HEADERS,
            json=_tv_payload(access_token, device_id),
        ) as response:
            result = await response.json(content_type=None)
    except Exception:
        _LOGGER.error("Failed to query Hisense TV deviceInfo", exc_info=True)
        return None

    if response.status != 200 or not isinstance(result, dict):
        _LOGGER.warning("Unexpected Hisense TV response: HTTP %s %s", response.status, result)
        return None
    if result.get("resultCode") != 0:
        _LOGGER.warning("Hisense TV deviceInfo failed: %s", result)
        return None
    data = result.get("data")
    if not isinstance(data, list) or not data:
        return None
    return result


class HiSenseTV:
    """Cloud client for a single Hisense TV."""

    def __init__(
        self,
        device_id: str,
        refresh_token: str,
        session,
        device_name: str = "",
        entity_name: str = "",
        ip: str = "",
        tv_port: int | None = None,
    ) -> None:
        self.device_id = device_id
        self.refresh_token = refresh_token
        self.session = session
        self.device_name = device_name
        self.entity_name = entity_name
        self.ip = ip
        self.tv_port = tv_port
        self.access_token: str | None = None
        self.status: dict[str, Any] = {
            "power_on": False,
            "ip": ip,
        }

    def get_status(self) -> dict[str, Any]:
        return dict(self.status)

    async def refresh(self) -> bool:
        """Refresh the cloud access token."""
        refresh_data = {
            "refreshToken": self.refresh_token,
            "appKey": "1234567890",
            "format": "1",
        }
        try:
            async with self.session.post(
                _REFRESH_URL,
                headers=_REFRESH_HEADERS,
                data=refresh_data,
            ) as response:
                result = await response.json(content_type=None)
        except Exception:
            _LOGGER.error("Failed to refresh Hisense TV token", exc_info=True)
            return False

        if not isinstance(result, list) or not result or not isinstance(result[0], dict):
            _LOGGER.error("Unexpected Hisense TV token refresh response: %s", result)
            return False
        token = result[0].get("token")
        if not token:
            _LOGGER.error("Hisense TV token refresh response did not include token")
            return False
        self.access_token = token
        return True

    async def check_status(self):
        """Fetch the real TV power state from the mobiletv cloud API."""
        if not self.access_token and not await self.refresh():
            return None

        result = await get_tv_device_info(self.session, self.access_token, self.device_id)
        if result is None:
            # Access tokens can expire independently; refresh once and retry.
            if not await self.refresh():
                return None
            result = await get_tv_device_info(self.session, self.access_token, self.device_id)
            if result is None:
                return None

        tv = next(
            (
                item
                for item in result.get("data", [])
                if isinstance(item, dict) and item.get("deviceId") == self.device_id
            ),
            None,
        )
        if tv is None:
            return None

        self.status["power_on"] = str(tv.get("status")) == "1"
        ip = tv.get("ip")
        if isinstance(ip, str) and ip:
            self.ip = ip
            self.status["ip"] = ip
        if tv.get("tvPort") is not None:
            self.tv_port = tv.get("tvPort")
        return self.get_status()

    async def turn_on(self) -> bool:
        """Turn the TV on. Waiting for a captured mobiletv control request."""
        _LOGGER.warning("Hisense TV power-on API is not configured yet")
        return False

    async def turn_off(self) -> bool:
        """Turn the TV off. Waiting for a captured mobiletv control request."""
        _LOGGER.warning("Hisense TV power-off API is not configured yet")
        return False

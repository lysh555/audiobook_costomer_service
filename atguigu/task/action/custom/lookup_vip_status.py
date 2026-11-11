from loguru import logger

from atguigu.clients import http_client
from atguigu.conf.config import settings
from atguigu.domain.action import ActionResult, Action
from atguigu.domain.state import DialogueState


class LookupVipStatusAction(Action):
    name = "action_lookup_vip_status"

    async def run(self, state: DialogueState) -> ActionResult:
        url = f"{settings.audiobook_api_base_url}/vip/status"
        try:
            response = await http_client.http_client.get(url, params={"user_id": state.sender_id})
        except Exception as error:
            logger.error("VIP状态接口调用失败：{}", error)
            return self._failure()

        if response.status_code != 200:
            return self._failure()

        try:
            payload: dict = response.json().get("data") or {}
        except ValueError:
            return self._failure()

        if not payload:
            return self._failure()

        return ActionResult(slot_updates={
            "vip_status": payload.get("vip_status") or payload.get("status") or "未开通",
            "remaining_listening_minutes": str(payload.get("remaining_listening_minutes") or 0),
            "vip_query_ok": "true",
            "vip_query_error": "",
        })

    def _failure(self) -> ActionResult:
        return ActionResult(slot_updates={
            "vip_status": "",
            "remaining_listening_minutes": "0",
            "vip_query_ok": "false",
            "vip_query_error": "暂时无法查询到你的VIP状态，请稍后再试。",
        })
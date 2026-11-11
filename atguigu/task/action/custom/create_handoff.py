from loguru import logger

from atguigu.clients import http_client
from atguigu.conf.config import settings
from atguigu.domain.action import ActionResult, Action
from atguigu.domain.state import DialogueState


class CreateHandoffAction(Action):
    name = "action_create_handoff"

    async def run(self, state: DialogueState) -> ActionResult:
        slots = state.task_state.active_task.slots
        reason = (slots.get("handoff_reason") or "").strip()

        url = f"{settings.audiobook_api_base_url}/handoff"
        payload = {"user_id": state.sender_id, "reason": reason or None}

        try:
            response = await http_client.http_client.post(url, json=payload)
        except Exception as error:
            logger.error("人工客服登记接口调用失败：{}", error)
            return self._result(False, "人工客服登记服务暂时不可用，请稍后再试。")

        data: dict = self._read_payload(response)
        if not data or not data.get("success"):
            return self._result(False, "人工客服登记没有成功，请稍后再试。")

        message = data.get("message") or "已为你登记人工客服请求，请稍等。"
        return ActionResult(slot_updates={
            "handoff_ok": "true",
            "handoff_message": message,
        })

    def _result(self, success: bool, message: str) -> ActionResult:
        return ActionResult(slot_updates={
            "handoff_ok": "true" if success else "false",
            "handoff_message": message,
        })

    def _read_payload(self, response) -> dict:
        if response.status_code != 200:
            return {}
        try:
            return response.json().get("data") or {}
        except ValueError:
            return {}
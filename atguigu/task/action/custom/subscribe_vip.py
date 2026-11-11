import re

from loguru import logger

from atguigu.clients import http_client
from atguigu.conf.config import settings
from atguigu.domain.action import ActionResult, Action
from atguigu.domain.state import DialogueState


class SubscribeVipAction(Action):
    name = "action_subscribe_vip"

    _MAX_MONTHS = 12

    async def run(self, state: DialogueState) -> ActionResult:
        slots = state.task_state.active_task.slots
        months = self._parse_months(slots.get("vip_months"))
        coupon_code = (slots.get("coupon_code") or "").strip()

        if months < 1 or months > self._MAX_MONTHS:
            return self._result(
                False,
                f"单次开通时长需要在 1 到 {self._MAX_MONTHS} 个月之间，请告诉我具体要开通几个月。",
            )

        url = f"{settings.audiobook_api_base_url}/vip/subscribe"
        payload = {
            "user_id": state.sender_id,
            "months": months,
            "coupon_code": coupon_code or None,
        }

        try:
            response = await http_client.http_client.post(url, json=payload)
        except Exception as error:
            logger.error("VIP开通接口调用失败：{}", error)
            return self._result(False, "VIP开通服务暂时不可用，请稍后再试。")

        data: dict = self._read_payload(response)
        if not data:
            return self._result(False, "VIP开通失败，请稍后再试。")

        if not data.get("success"):
            return self._result(False, data.get("message") or "本次VIP开通没有成功，请稍后重试。")

        message = data.get("message") or f"VIP会员已开通 {months} 个月。"
        return ActionResult(slot_updates={
            "vip_subscribe_ok": "true",
            "vip_subscribe_message": message,
            "vip_status": str(data.get("vip_status") or "已开通"),
        })

    def _parse_months(self, raw_value) -> int:
        """从“3个月”“半年”“一年”这类表达中解析出开通月数"""
        text = str(raw_value or "").strip()
        if not text:
            return 1
        if "半" in text:
            return 6
        if "一年" in text or "全年" in text or "包年" in text:
            return 12
        matched = re.search(r"\d+", text)
        if matched:
            return int(matched.group())
        return 1

    def _result(self, success: bool, message: str) -> ActionResult:
        return ActionResult(slot_updates={
            "vip_subscribe_ok": "true" if success else "false",
            "vip_subscribe_message": message,
        })

    def _read_payload(self, response) -> dict:
        if response.status_code != 200:
            return {}
        try:
            return response.json().get("data") or {}
        except ValueError:
            return {}
from loguru import logger

from atguigu.clients import http_client
from atguigu.conf.config import settings
from atguigu.domain.action import ActionResult, Action
from atguigu.domain.state import DialogueState


class CreateBookOrderAction(Action):
    name = "action_create_book_order"

    async def run(self, state: DialogueState) -> ActionResult:
        slots = state.task_state.active_task.slots
        book_id = (slots.get("book_id") or "").strip()
        coupon_code = (slots.get("coupon_code") or "").strip()

        if not book_id:
            return self._result(False, "还没有确认要购买的听书，请先告诉我想购买哪一本。")

        url = f"{settings.audiobook_api_base_url}/orders"
        payload = {
            "user_id": state.sender_id,
            "book_id": book_id,
            "coupon_code": coupon_code or None,
        }

        try:
            response = await http_client.http_client.post(url, json=payload)
        except Exception as error:
            logger.error("下单接口调用失败：{}", error)
            return self._result(False, "下单服务暂时不可用，请稍后再试。")

        data: dict = self._read_payload(response)
        if not data:
            return self._result(False, "下单失败，请确认听书信息后再试。")

        if not data.get("success"):
            return self._result(False, data.get("message") or "本次下单没有成功，请稍后重试。")

        order_id = str(data.get("order_id") or "")
        message = data.get("message") or f"已为你创建订单 {order_id}。"
        return ActionResult(slot_updates={
            "purchase_ok": "true",
            "purchase_message": message,
            "pay_amount": str(data.get("amount") or ""),
            "order_number": order_id,
        })

    def _result(self, success: bool, message: str) -> ActionResult:
        return ActionResult(slot_updates={
            "purchase_ok": "true" if success else "false",
            "purchase_message": message,
        })

    def _read_payload(self, response) -> dict:
        if response.status_code != 200:
            return {}
        try:
            return response.json().get("data") or {}
        except ValueError:
            return {}
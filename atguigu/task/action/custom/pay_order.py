from loguru import logger

from atguigu.clients import http_client
from atguigu.conf.config import settings
from atguigu.domain.action import ActionResult, Action
from atguigu.domain.state import DialogueState


class PayOrderAction(Action):
    name = "action_pay_order"

    async def run(self, state: DialogueState) -> ActionResult:
        slots = state.task_state.active_task.slots
        order_number = (slots.get("order_number") or "").strip()

        if not order_number:
            return self._result(False, "还没有拿到要支付的订单号，请先告诉我订单号。")

        url = f"{settings.audiobook_api_base_url}/orders/{order_number}/pay"
        try:
            response = await http_client.http_client.post(url)
        except Exception as error:
            logger.error("订单支付接口调用失败：{}", error)
            return self._result(False, "支付服务暂时不可用，请稍后再试。")

        data: dict = self._read_payload(response)
        if not data:
            return self._result(False, f"支付失败，请确认订单 {order_number} 是否正确后重试。")

        success = bool(data.get("success"))
        message = data.get("message") or (
            f"订单 {order_number} 支付成功，听书已解锁。" if success else "订单支付没有成功，请稍后重试。"
        )
        return ActionResult(slot_updates={
            "pay_ok": "true" if success else "false",
            "pay_message": message,
            "order_status": str(data.get("status") or ""),
        })

    def _result(self, success: bool, message: str) -> ActionResult:
        return ActionResult(slot_updates={
            "pay_ok": "true" if success else "false",
            "pay_message": message,
        })

    def _read_payload(self, response) -> dict:
        if response.status_code != 200:
            return {}
        try:
            return response.json().get("data") or {}
        except ValueError:
            return {}
from loguru import logger

from atguigu.clients import http_client
from atguigu.conf.config import settings
from atguigu.domain.action import ActionResult, Action
from atguigu.domain.state import DialogueState


class SubmitRefundAction(Action):
    name = "action_submit_refund"

    async def run(self, state: DialogueState) -> ActionResult:
        slots = state.task_state.active_task.slots
        order_number = (slots.get("order_number") or "").strip()
        refund_reason = (slots.get("refund_reason") or "").strip()

        url = f"{settings.audiobook_api_base_url}/orders/{order_number}/refund"
        try:
            response = await http_client.http_client.post(url, json={"reason": refund_reason})
        except Exception as error:
            logger.error("退款申请接口调用失败：{}", error)
            return self._result(False, "退款申请提交失败，服务暂时不可用，请稍后再试。")

        payload: dict = self._read_payload(response)
        if not payload:
            if response.status_code >= 500:
                return self._result(False, "退款申请提交失败，服务暂时不可用，请稍后再试。")
            return self._result(False, f"退款申请提交失败，请确认订单 {order_number} 是否正确后重试。")

        success = bool(payload.get("success"))
        message = payload.get("message") or (
            f"订单 {order_number} 的退款申请已提交，正在等待审核。"
            if success
            else f"订单 {order_number} 的退款申请没有提交成功，请稍后重试。"
        )
        return self._result(success, message)

    def _result(self, success: bool, message: str) -> ActionResult:
        return ActionResult(slot_updates={
            "refund_submitted": "true" if success else "false",
            "refund_message": message,
        })

    def _read_payload(self, response) -> dict:
        if response.status_code != 200:
            return {}
        try:
            return response.json().get("data") or {}
        except ValueError:
            return {}
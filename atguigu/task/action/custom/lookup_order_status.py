from loguru import logger

from atguigu.clients import http_client
from atguigu.conf.config import settings
from atguigu.domain.action import Action, ActionResult
from atguigu.domain.state import DialogueState


class LookupOrderStatusAction(Action):
    name = "action_lookup_order_status"

    async def run(self,state:DialogueState)->ActionResult:
        order_number = state.task_state.active_task.slots.get("order_number")

        url = f"{settings.audiobook_api_base_url}/orders/{order_number}"
        try:
            response = await http_client.http_client.get(url)
        except Exception as error:
            logger.error("订单状态接口调用失败：{}", error)
            return ActionResult(
                slot_updates={
                    "order_status":"",
                    "order_summary":"订单查询服务暂时不可用，请稍后再试。"
                }
            )

        payload:dict = self._read_payload(response)

        if not payload:
            return ActionResult(
                slot_updates={
                    "order_status":"",
                    "order_summary":f"没有查询到订单 {order_number}，请确认订单号是否正确后重试。"
                }
            )

        return ActionResult(
            slot_updates={
                "order_status":payload.get("status") or payload.get("status_desc") or "未知",
                "order_summary":f"订单金额: ¥{payload.get('amount')}"
            }

        )

    def _read_payload(self,response)->dict:
        """订单不存在时后端返回404且响应体中没有data字段，这里统一做空值兜底"""
        if response.status_code != 200:
            return {}
        try:
            return response.json().get("data") or {}
        except ValueError:
            return {}
from loguru import logger

from atguigu.clients import http_client
from atguigu.conf.config import settings
from atguigu.domain.action import ActionResult, Action
from atguigu.domain.messages import order_card_messages
from atguigu.domain.state import DialogueState


class ListMyOrdersAction(Action):
    name = "action_list_my_orders"

    _MAX_DISPLAY = 5

    async def run(self, state: DialogueState) -> ActionResult:
        url = f"{settings.audiobook_api_base_url}/users/{state.sender_id}/orders"
        try:
            response = await http_client.http_client.get(url)
        except Exception as error:
            logger.error("我的订单接口调用失败：{}", error)
            return self._result("暂时无法查询你的订单，请稍后再试。")

        payload: dict = self._read_payload(response)
        if not payload:
            return self._result("没有查询到你的订单记录，请确认当前账号后再试。")

        orders: list[dict] = payload.get("orders") or []
        if not orders:
            return self._result("你目前还没有任何听书订单，可以先搜索并购买喜欢的听书。")

        parts: list[str] = []
        for index, order in enumerate(orders[:self._MAX_DISPLAY], start=1):
            order_id = order.get("order_id") or "未知订单号"
            title = order.get("title") or "未知听书"
            status = order.get("status") or "未知状态"
            amount = order.get("amount")
            parts.append(f"{index}）{order_id}《{title}》{status}，金额 ¥{amount}")

        tail = ""
        if len(orders) > self._MAX_DISPLAY:
            tail = f"（共 {len(orders)} 笔订单，这里先展示最近 {self._MAX_DISPLAY} 笔）"

        return self._result(f"你最近的订单有：{'；'.join(parts)}。{tail}", orders)

    def _result(self, summary: str, orders: list[dict] | None = None) -> ActionResult:
        return ActionResult(
            slot_updates={"order_list_summary": summary},
            messages=order_card_messages(orders or [], limit=self._MAX_DISPLAY),
        )

    def _read_payload(self, response) -> dict:
        if response.status_code != 200:
            return {}
        try:
            return response.json().get("data") or {}
        except ValueError:
            return {}
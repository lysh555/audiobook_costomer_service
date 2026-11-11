from loguru import logger

from atguigu.clients import http_client
from atguigu.conf.config import settings
from atguigu.domain.action import ActionResult, Action
from atguigu.domain.state import DialogueState


class RedeemCouponAction(Action):
    name = "action_redeem_coupon"

    async def run(self, state: DialogueState) -> ActionResult:
        coupon_code = (state.task_state.active_task.slots.get("coupon_code") or "").strip()
        url = f"{settings.audiobook_api_base_url}/coupons/redeem"

        try:
            response = await http_client.http_client.post(url, json={"coupon_code": coupon_code})
        except Exception as error:
            logger.error("优惠码兑换接口调用失败：{}", error)
            return ActionResult(slot_updates={
                "coupon_redeemed": "false",
                "coupon_info": "优惠码兑换服务暂时不可用，请稍后再试。",
            })

        payload: dict = self._read_payload(response)
        if not payload:
            return ActionResult(slot_updates={
                "coupon_redeemed": "false",
                "coupon_info": "优惠码兑换服务暂时不可用，请稍后再试。",
            })

        success = self._judge_success(payload)
        coupon_info = (
            payload.get("coupon_info")
            or payload.get("message")
            or f"优惠码 {coupon_code} 兑换成功"
        )

        return ActionResult(slot_updates={
            "coupon_redeemed": "true" if success else "false",
            "coupon_info": coupon_info,
        })

    def _judge_success(self, payload: dict) -> bool:
        """优先使用后端返回的 success 字段，缺失时根据返回文案兜底判断"""
        success_flag = payload.get("success")
        if isinstance(success_flag, bool):
            return success_flag

        text = f"{payload.get('message') or ''}{payload.get('coupon_info') or ''}"
        return not any(word in text for word in ("无效", "已兑换", "已被兑换", "失败"))

    def _read_payload(self, response) -> dict:
        if response.status_code != 200:
            return {}
        try:
            return response.json().get("data") or {}
        except ValueError:
            return {}
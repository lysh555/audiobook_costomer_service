from loguru import logger

from atguigu.clients import http_client
from atguigu.conf.config import settings
from atguigu.domain.action import ActionResult, Action
from atguigu.domain.state import DialogueState


class ListMyCouponsAction(Action):
    name = "action_list_my_coupons"

    async def run(self, state: DialogueState) -> ActionResult:
        url = f"{settings.audiobook_api_base_url}/users/{state.sender_id}/coupons"
        try:
            response = await http_client.http_client.get(url)
        except Exception as error:
            logger.error("我的优惠券接口调用失败：{}", error)
            return self._result("暂时无法查询你的优惠券，请稍后再试。")

        payload: dict = self._read_payload(response)
        if not payload:
            return self._result("没有查询到你的优惠券记录，请确认当前账号后再试。")

        coupons: list[dict] = payload.get("coupons") or []
        if not coupons:
            return self._result("你目前没有可用的优惠券，可以关注活动或使用优惠码兑换。")

        parts: list[str] = []
        for index, coupon in enumerate(coupons, start=1):
            code = coupon.get("coupon_code") or "未知优惠码"
            info = coupon.get("coupon_info") or "优惠券"
            expires_at = str(coupon.get("expires_at") or "")[:10]
            expires_text = f"，有效期至 {expires_at}" if expires_at else ""
            parts.append(f"{index}）{code}：{info}{expires_text}")

        return self._result(
            f"你当前可用的优惠券有：{'；'.join(parts)}。"
            "下单购买听书或开通会员时告诉我要用的优惠码即可抵扣。"
        )

    def _result(self, summary: str) -> ActionResult:
        return ActionResult(slot_updates={"coupon_list_summary": summary})

    def _read_payload(self, response) -> dict:
        if response.status_code != 200:
            return {}
        try:
            return response.json().get("data") or {}
        except ValueError:
            return {}
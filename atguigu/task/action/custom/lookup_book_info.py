from loguru import logger

from atguigu.clients import http_client
from atguigu.conf.config import settings
from atguigu.domain.action import ActionResult, Action
from atguigu.domain.state import DialogueState


class LookupBookInfoAction(Action):
    name = "action_lookup_book_info"

    async def run(self, state: DialogueState) -> ActionResult:
        book_id = state.task_state.active_task.slots.get("book_id")
        url = f"{settings.audiobook_api_base_url}/books/{book_id}"
        try:
            response = await http_client.http_client.get(url)
        except Exception as error:
            logger.error("听书详情接口调用失败：{}", error)
            return self._failure(f"暂时无法查询《{book_id}》的详情，请稍后再试。")

        payload: dict = self._read_payload(response)
        if not payload:
            return self._failure(f"没有查到《{book_id}》这本听书，请确认后再试。")

        return ActionResult(slot_updates={
            "book_name": payload.get("title") or "未知",
            "author": payload.get("author") or "未知",
            "category": payload.get("category") or "未知",
            "book_found": "true",
            "book_error": "",
        })

    def _failure(self, message: str) -> ActionResult:
        return ActionResult(slot_updates={
            "book_found": "false",
            "book_error": message,
        })

    def _read_payload(self, response) -> dict:
        if response.status_code != 200:
            return {}
        try:
            return response.json().get("data") or {}
        except ValueError:
            return {}
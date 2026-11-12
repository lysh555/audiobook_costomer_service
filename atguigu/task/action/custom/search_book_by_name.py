from loguru import logger

from atguigu.clients import http_client
from atguigu.conf.config import settings
from atguigu.domain.action import ActionResult, Action
from atguigu.domain.messages import book_card_messages
from atguigu.domain.state import DialogueState


class SearchBookByNameAction(Action):
    name = "action_search_book_by_name"

    async def run(self, state: DialogueState) -> ActionResult:
        book_name = state.task_state.active_task.slots.get("book_name")
        url = f"{settings.audiobook_api_base_url}/books/search"
        try:
            response = await http_client.http_client.get(url, params={"name": book_name})
        except Exception as error:
            logger.error("听书搜索接口调用失败：{}", error)
            return self._failure(f"暂时无法搜索《{book_name}》，请稍后再试。")

        payload: dict = self._read_payload(response)
        if not payload:
            return self._failure(f"暂时无法搜索《{book_name}》，请稍后再试。")

        books = payload.get("books") or []
        if not books:
            return self._failure(f"没有找到《{book_name}》这本听书，请确认书名是否正确。")

        book: dict = books[0]
        return ActionResult(
            slot_updates={
                "book_id": str(book.get("id") or ""),
                "book_name": book.get("title") or book_name,
                "author": book.get("author") or "未知",
                "category": book.get("category") or "未知",
                "book_found": "true",
                "book_error": "",
            },
            messages=book_card_messages([book], limit=1),
        )

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
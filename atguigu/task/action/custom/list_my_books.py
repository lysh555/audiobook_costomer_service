from loguru import logger

from atguigu.clients import http_client
from atguigu.conf.config import settings
from atguigu.domain.action import ActionResult, Action
from atguigu.domain.messages import book_card_messages
from atguigu.domain.state import DialogueState


class ListMyBooksAction(Action):
    name = "action_list_my_books"

    _MAX_DISPLAY = 5

    async def run(self, state: DialogueState) -> ActionResult:
        url = f"{settings.audiobook_api_base_url}/users/{state.sender_id}/books"
        try:
            response = await http_client.http_client.get(url)
        except Exception as error:
            logger.error("我的听书接口调用失败：{}", error)
            return self._result("暂时无法查询你已购买的听书，请稍后再试。")

        payload: dict = self._read_payload(response)
        if not payload:
            return self._result("没有查询到你的听书记录，请确认当前账号后再试。")

        books: list[dict] = payload.get("books") or []
        if not books:
            return self._result("你目前还没有已购买的听书，可以先搜索并购买喜欢的听书。")

        parts: list[str] = []
        for index, book in enumerate(books[:self._MAX_DISPLAY], start=1):
            title = book.get("title") or "未知听书"
            author = book.get("author") or "未知作者"
            category = book.get("category") or "未分类"
            parts.append(f"{index}）《{title}》（{author}，{category}）")

        tail = ""
        if len(books) > self._MAX_DISPLAY:
            tail = f"（共 {len(books)} 本，这里先展示最近 {self._MAX_DISPLAY} 本）"

        return self._result(f"你已购买并可以收听的听书有：{'；'.join(parts)}。{tail}", books)

    def _result(self, summary: str, books: list[dict] | None = None) -> ActionResult:
        return ActionResult(
            slot_updates={"book_list_summary": summary},
            messages=book_card_messages(books or [], limit=self._MAX_DISPLAY),
        )

    def _read_payload(self, response) -> dict:
        if response.status_code != 200:
            return {}
        try:
            return response.json().get("data") or {}
        except ValueError:
            return {}
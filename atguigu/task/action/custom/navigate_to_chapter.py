from loguru import logger

from atguigu.clients import http_client
from atguigu.conf.config import settings
from atguigu.domain.action import ActionResult, Action
from atguigu.domain.state import DialogueState

_CN_DIGITS = {
    "零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
    "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
}
_CN_UNITS = {"十": 10, "百": 100, "千": 1000}


class NavigateToChapterAction(Action):
    name = "action_navigate_to_chapter"

    async def run(self, state: DialogueState) -> ActionResult:
        slots = state.task_state.active_task.slots
        book_id = slots.get("book_id")
        raw_chapter = slots.get("chapter_number")

        url = f"{settings.audiobook_api_base_url}/books/{book_id}"
        try:
            response = await http_client.http_client.get(url)
        except Exception as error:
            logger.error("听书详情接口调用失败：{}", error)
            return self._failure(state, f"暂时无法获取《{book_id}》的章节信息，请稍后再试。")

        payload: dict = self._read_payload(response)
        if not payload:
            return self._failure(state, f"没有查到《{book_id}》这本听书，请确认后再试。", reset_book=True)

        book_name = str(payload.get("title") or book_id)
        chapter_count = self._to_int(payload.get("chapter_count"))
        chapter_number = self._to_arabic(raw_chapter)

        if chapter_number is None or chapter_number <= 0:
            return self._failure(state, "章节号需要是正整数，例如“第3章”。")

        if chapter_count and chapter_number > chapter_count:
            return self._failure(
                state, f"《{book_name}》一共只有{chapter_count}章，没有第{chapter_number}章。"
            )

        return ActionResult(slot_updates={
            "book_name": book_name,
            "chapter_number": str(chapter_number),
            "chapter_ready": "true",
            "chapter_error": "",
        })

    def _failure(self, state: DialogueState, message: str, reset_book: bool = False) -> ActionResult:
        state.task_state.active_task.slots.pop("chapter_number", None)
        if reset_book:
            state.task_state.active_task.slots.pop("book_id", None)
        return ActionResult(slot_updates={
            "chapter_ready": "false",
            "chapter_error": message,
        })

    def _to_int(self, value) -> int:
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0

    def _to_arabic(self, value) -> int | None:
        """把“第3章”“第三章”“3”统一转成阿拉伯数字，无法识别时返回 None"""
        if value is None:
            return None

        if isinstance(value, int):
            return value

        text = str(value).strip()
        for token in ("第", "章", "节", "集", "回", " ", "　"):
            text = text.replace(token, "")
        if not text:
            return None

        if text.isdigit():
            return int(text)

        total = 0
        current = 0
        for char in text:
            if char in _CN_DIGITS:
                current = _CN_DIGITS[char]
            elif char in _CN_UNITS:
                total += (current or 1) * _CN_UNITS[char]
                current = 0
            else:
                return None
        return total + current

    def _read_payload(self, response) -> dict:
        if response.status_code != 200:
            return {}
        try:
            return response.json().get("data") or {}
        except ValueError:
            return {}
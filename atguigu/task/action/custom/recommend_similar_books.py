from loguru import logger

from atguigu.clients import http_client
from atguigu.conf.config import settings
from atguigu.domain.action import ActionResult, Action
from atguigu.domain.messages import book_card_messages
from atguigu.domain.state import DialogueState


class RecommendSimilarBooksAction(Action):
    name = "action_recommend_similar_books"

    _MAX_RESULTS = 3

    async def run(self, state: DialogueState) -> ActionResult:
        book_id = str(state.task_state.active_task.slots.get("book_id") or "").strip()
        if not book_id:
            return self._summary("请先选择一本听书，我再为你推荐相似的内容。")

        detail = await self._fetch_book(book_id)
        if not detail:
            return self._summary(f"暂时无法获取听书 {book_id} 的详情，请稍后再试。")

        title = detail.get("title") or book_id
        author = str(detail.get("author") or "").strip()
        category = str(detail.get("category") or "").strip()

        candidates = await self._collect_candidates(book_id, author, category)
        if not candidates:
            return self._summary(
                f"暂时没有找到与《{title}》相似的听书，你可以换个关键词再试试，或者告诉我你感兴趣的分类。"
            )

        return self._summary(
            self._build_summary(title, author, category, candidates),
            [book for book, _ in candidates],
        )

    async def _collect_candidates(
        self, book_id: str, author: str, category: str
    ) -> list[tuple[dict, str]]:
        """按同作者、同分类、全库兜底的顺序收集候选听书，并排除当前听书"""
        seen: set[str] = {book_id}
        candidates: list[tuple[dict, str]] = []

        for keyword, reason in ((author, "同作者"), (category, "同分类")):
            if not keyword:
                continue
            for book in await self._search(keyword):
                candidate_id = str(book.get("id") or "")
                if not candidate_id or candidate_id in seen:
                    continue
                seen.add(candidate_id)
                candidates.append((book, reason))

        if len(candidates) >= self._MAX_RESULTS:
            return candidates[: self._MAX_RESULTS]

        for book in await self._search(""):
            candidate_id = str(book.get("id") or "")
            if not candidate_id or candidate_id in seen:
                continue
            seen.add(candidate_id)
            candidates.append((book, "热门"))

        return candidates[: self._MAX_RESULTS]

    def _build_summary(
        self, title: str, author: str, category: str, candidates: list[tuple[dict, str]]
    ) -> str:
        """推荐依据只声明真实命中的维度，避免文案与实际候选来源不一致"""
        reasons = {reason for _, reason in candidates}
        basis_parts: list[str] = []
        if "同作者" in reasons and author:
            basis_parts.append(f"同作者（{author}）")
        if "同分类" in reasons and category:
            basis_parts.append(f"同分类（{category}）")

        if basis_parts:
            basis = f"根据《{title}》的{'、'.join(basis_parts)}"
        elif "热门" in reasons:
            basis = f"库里暂时没有与《{title}》同作者或同分类的听书，先为你推荐几本热门作品"
        else:
            basis = f"根据《{title}》"

        items: list[str] = []
        for index, (book, reason) in enumerate(candidates, start=1):
            book_title = book.get("title") or "未知听书"
            book_author = book.get("author") or "未知作者"
            book_category = book.get("category") or "未分类"
            items.append(f"{index}）《{book_title}》（{book_author}，{book_category}，{reason}）")

        joined = "；".join(items)
        if basis_parts:
            return f"{basis}，为你推荐：{joined}。"
        return f"{basis}：{joined}。"

    async def _fetch_book(self, book_id: str) -> dict:
        url = f"{settings.audiobook_api_base_url}/books/{book_id}"
        try:
            response = await http_client.http_client.get(url)
        except Exception as error:
            logger.error("听书详情接口调用失败：{}", error)
            return {}
        return self._read_payload(response)

    async def _search(self, keyword: str) -> list[dict]:
        url = f"{settings.audiobook_api_base_url}/books/search"
        try:
            response = await http_client.http_client.get(url, params={"keyword": keyword})
        except Exception as error:
            logger.error("听书搜索接口调用失败：{}", error)
            return []
        payload = self._read_payload(response)
        return payload.get("books") or []

    def _summary(self, summary: str, books: list[dict] | None = None) -> ActionResult:
        return ActionResult(
            slot_updates={"recommendation_summary": summary},
            messages=book_card_messages(books or [], limit=self._MAX_RESULTS),
        )

    def _read_payload(self, response) -> dict:
        if response.status_code != 200:
            return {}
        try:
            return response.json().get("data") or {}
        except ValueError:
            return {}
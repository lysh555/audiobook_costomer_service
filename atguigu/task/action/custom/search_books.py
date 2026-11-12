import re

from loguru import logger

from atguigu.clients import http_client
from atguigu.conf.config import settings
from atguigu.domain.action import ActionResult, Action
from atguigu.domain.messages import book_card_messages
from atguigu.domain.state import DialogueState


class SearchBooksAction(Action):
    name = "action_search_books"

    _MAX_CARDS = 3

    _FILLER_WORDS = (
        "推荐", "一本", "适合", "听的", "听的书", "有声书", "听书",
        "帮我", "帮忙", "给我", "请", "找", "搜索", "搜一下", "有没有",
        "想要", "想听", "想", "一些", "几本", "关于", "相关的", "的",
        "吧", "呢", "吗", "啊", "一下",
    )

    _SCENE_PROFILES = (
        (
            ("睡前", "助眠", "入睡", "催眠", "夜里", "晚上", "放松", "治愈", "舒缓", "安静"),
            ("文学", "小说"),
            "节奏舒缓、情节连贯",
        ),
        (
            ("通勤", "路上", "地铁", "公交", "开车", "碎片时间", "上班"),
            ("小说", "历史"),
            "情节性强、随时能接上",
        ),
        (
            ("学习", "涨知识", "自我提升", "充电", "长见识", "提升", "成长"),
            ("历史", "商业"),
            "知识密度高、能学到东西",
        ),
        (
            ("烧脑", "刺激", "脑洞", "硬核", "科幻", "未来"),
            ("科幻",),
            "设定硬核、脑洞大开",
        ),
    )

    async def run(self, state: DialogueState) -> ActionResult:
        raw_keyword = state.task_state.active_task.slots.get("book_name")
        keyword = str(raw_keyword or "").strip()

        matched_keyword = ""
        books: list[dict] = []
        for candidate in self._build_candidates(keyword):
            books = await self._search(candidate)
            if books:
                matched_keyword = candidate
                break

        if books:
            summary = self._build_summary(matched_keyword, books)
            return self._result(summary, books)

        all_books = await self._search("")
        scene = self._match_scene(keyword)
        if scene:
            scene_word, categories, reason = scene
            scene_books = self._filter_by_category(all_books, categories) or all_books
            summary = self._build_scene_summary(scene_word, reason, scene_books)
            return self._result(summary, scene_books)

        summary = self._build_fallback_summary(keyword, all_books)
        return self._result(summary, all_books)

    async def _search(self, keyword: str) -> list[dict]:
        url = f"{settings.audiobook_api_base_url}/books/search"
        try:
            response = await http_client.http_client.get(url, params={"keyword": keyword})
        except Exception as error:
            logger.error("听书搜索接口调用失败：{}", error)
            return []
        if response.status_code != 200:
            return []
        try:
            payload = response.json().get("data") or {}
        except ValueError:
            return []
        return payload.get("books") or []

    def _build_candidates(self, keyword: str) -> list[str]:
        """把自然语言关键词拆成可检索的候选词，例如“睡前听的书”->“睡前”"""
        if not keyword:
            return []
        candidates: list[str] = [keyword]
        cleaned = keyword
        for filler in self._FILLER_WORDS:
            cleaned = cleaned.replace(filler, " ")
        for token in re.split(r"[\s,，。、!！?？]+", cleaned):
            token = token.strip()
            if len(token) >= 2 and token not in candidates:
                candidates.append(token)
        return candidates

    def _match_scene(self, keyword: str) -> tuple[str, tuple[str, ...], str] | None:
        """识别“睡前/通勤/学习”这类场景偏好词，返回命中的场景词、目标分类和推荐理由"""
        candidates = self._build_candidates(keyword)
        for words, categories, reason in self._SCENE_PROFILES:
            for word in words:
                if any(word in candidate for candidate in candidates):
                    return word, categories, reason
        return None

    def _display_keyword(self, keyword: str) -> str:
        """用于展示的关键词，优先取剥离填充词后最干净的那个候选词"""
        candidates = self._build_candidates(keyword)
        return candidates[-1] if candidates else keyword

    def _filter_by_category(self, books: list[dict], categories: tuple[str, ...]) -> list[dict]:
        return [book for book in books if str(book.get("category") or "") in categories]

    def _build_summary(self, matched_keyword: str, books: list[dict]) -> str:
        titles = [str(book.get("title")) for book in books if book.get("title")]
        return "为你找到：" + "、".join(titles)

    def _build_scene_summary(self, scene_word: str, reason: str, books: list[dict]) -> str:
        titles = [str(book.get("title")) for book in books if book.get("title")]
        if not titles:
            return "暂时没有找到可推荐的听书，稍后再试试吧"
        return f"{scene_word}适合听{reason}的作品，为你挑了这几本：" + "、".join(titles)

    def _build_fallback_summary(self, keyword: str, books: list[dict]) -> str:
        titles = [str(book.get("title")) for book in books if book.get("title")]
        if not titles:
            return "暂时没有找到可推荐的听书，稍后再试试吧"
        display = self._display_keyword(keyword)
        if display:
            return f"库里暂时没有与“{display}”相关的听书，先为你推荐这几本热门听书：" + "、".join(titles)
        return "为你推荐这几本热门听书：" + "、".join(titles)

    def _result(self, summary: str, books: list[dict]) -> ActionResult:
        return ActionResult(
            slot_updates={"recommendation_summary": summary},
            messages=book_card_messages(books, limit=self._MAX_CARDS),
        )
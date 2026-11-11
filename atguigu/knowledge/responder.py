from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from atguigu.clients.llm_client import llm
from atguigu.domain.knowledge import KnowledgeChunk
from atguigu.domain.messages import UserMessage, BotMessage
from atguigu.domain.state import Turn
from atguigu.prompts.history_builder import HistoryBuilder
from atguigu.prompts.prompt_loader import load_prompt


class KnowledgeResponder:

    async def respond(self, turns: list[Turn], user_message: UserMessage, chunks: list[KnowledgeChunk]) -> BotMessage:
        """基于目前检索到相关知识片段结合历史对象以及用户消息生成一条回复"""
        usable_contents = [chunk.content.strip() for chunk in chunks if chunk.content and chunk.content.strip()]
        if not usable_contents:
            return BotMessage(text="这个问题我暂时没有查到相关资料，你可以换一种说法，或者把具体的订单号、听书名告诉我，我再帮你查。")

        prompt_text = load_prompt('knowledge_respond')
        prompt = PromptTemplate.from_template(prompt_text, template_format="jinja2")
        chain=prompt|llm|StrOutputParser()
        knowledge_content = "\n\n".join(usable_contents)
        result = await chain.ainvoke({
            "history" : HistoryBuilder.build(turns),
            "user_message": HistoryBuilder.render_user_message(user_message),
            "knowledge_content":knowledge_content,
        })
        return BotMessage(text=result)
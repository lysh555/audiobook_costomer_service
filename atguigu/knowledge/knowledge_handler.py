import asyncio
from atguigu.domain.knowledge import KnowledgeIntent, KnowledgeChunk
from atguigu.domain.messages import UserMessage, BotMessage
from atguigu.domain.state import DialogueState
from atguigu.knowledge.providers import KnowledgeProvider
from atguigu.knowledge.responder import KnowledgeResponder


class KnowledgeHandler:

    def __init__(self,knowledge_intents:dict[str,KnowledgeIntent],providers:list[KnowledgeProvider],knowledge_responder:KnowledgeResponder):
        """
                    构造
                :param knowledge_intents: 知识意图配置字典 {"意图ID",KnowledgeIntent对象}
                :param providers: 系统支持的知识提供者对象
                """
        self.knowledge_intents = knowledge_intents
        self.providers_by_id: dict[str,KnowledgeProvider] = {p.provider_id:p for p in providers}
        self.knowledge_responder:KnowledgeResponder = knowledge_responder


    async def handle(self,intents:list[str],state:DialogueState,user_message:UserMessage)->list[BotMessage]:
        knowledge_intents:list[KnowledgeIntent] = [self.knowledge_intents.get(intent) for intent in intents]
        knowledge_intents = [intent for intent in knowledge_intents if intent is not None]

        all_provider_ids:set[str] = set()
        for knowledge_intent in knowledge_intents:
            all_provider_ids.update(knowledge_intent.provider_ids)

        providers:list[KnowledgeProvider] = [self.providers_by_id.get(provider_id) for provider_id in all_provider_ids]
        providers = [provider for provider in providers if provider is not None]

        chunks_list = await asyncio.gather(*[provider.retrieve(state, user_message, intents) for provider in providers])
        chunks:list[KnowledgeChunk] = [chunk for chunks in chunks_list for chunk in chunks]
        bot_message:BotMessage = await self.knowledge_responder.respond(state.shared_state.current_session().turns,user_message,chunks)
        return [bot_message]
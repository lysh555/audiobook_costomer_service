from jinja2 import Template
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from atguigu.clients.llm_client import llm
from atguigu.domain.flow_catalog import ResponseTemplate, ResponseMode
from atguigu.domain.messages import UserMessage, BotMessage
from atguigu.domain.state import DialogueState
from atguigu.prompts.history_builder import HistoryBuilder


class ResponseRenderer:
    def __init__(self):
        pass

    async def respond(self,template:ResponseTemplate,state:DialogueState,user_message:UserMessage)->BotMessage:
        slots = state.task_state.active_task.slots
        render_text = Template(template.text).render(slots=slots)
        if template.mode == ResponseMode.STATIC:
            return BotMessage(text=render_text)
        else:
            llm_text = await self._call_llm(template.prompt,state,user_message,render_text)
            return BotMessage(text=llm_text)

    async def _call_llm(self,prompt_text,state:DialogueState,user_message:UserMessage,current_response:str)->str:
        prompt = PromptTemplate.from_template(template=prompt_text,template_format="jinja2")
        chain = prompt | llm | StrOutputParser()
        text = await chain.ainvoke(
            {
                'history':HistoryBuilder.build(state.shared_state.current_session().turns),
                'user_message':HistoryBuilder.render_user_message(user_message),
                'current_response':current_response
            }
        )
        return text





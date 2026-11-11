import json
from dataclasses import asdict

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from loguru import logger

from atguigu.clients.llm_client import llm
from atguigu.domain.flow_catalog import FlowCatalog
from atguigu.domain.knowledge import KnowledgeIntent
from atguigu.domain.messages import UserMessage
from atguigu.domain.plan import TurnPlan
from atguigu.domain.state import DialogueState
from atguigu.prompts.history_builder import HistoryBuilder
from atguigu.prompts.prompt_loader import load_prompt


class TurnPlanner:

    async def predict(self,state:DialogueState,user_message:UserMessage,flow_catalog:FlowCatalog,knowledge_intents:dict[str,KnowledgeIntent])->TurnPlan:

        conversation_history = HistoryBuilder.build(state.shared_state.current_session().turns)
        user_message = HistoryBuilder.render_user_message(user_message=user_message)
        focused_object_json  = json.dumps(asdict(state.shared_state.focused_object),ensure_ascii=False,indent=2) if state.shared_state.focused_object is not None else None
        task_state_json = json.dumps(asdict(state.task_state),ensure_ascii=False,indent=2)
        knowledge_intents_dict = [{knowledge_intent.id:knowledge_intent.description} for knowledge_intent in knowledge_intents.values()]
        knowledge_intents_json = json.dumps(knowledge_intents_dict)
        flows_dict = [{k:v for k,v in asdict(flow).items() if k != "steps"} for flow in flow_catalog.flows.values()]
        flows_json = json.dumps(flows_dict,ensure_ascii=False,indent=2)

        prompt = PromptTemplate.from_template(load_prompt("turn_plan"),template_format="jinja2")

        chain = prompt | llm | JsonOutputParser()

        turn_plan_dict = await chain.ainvoke({
            'user_message': user_message,
            'conversation_history': conversation_history,
            'focused_object_json': focused_object_json,
            'task_state_json': task_state_json,
            'knowledge_intents_json': knowledge_intents_json,
            'flows_json': flows_json
        })
        turn_plan:TurnPlan = TurnPlan.from_dict(turn_plan_dict)
        logger.info("生成本轮计划JSON对象：{}", turn_plan)
        return turn_plan
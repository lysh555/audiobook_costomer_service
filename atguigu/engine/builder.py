from pathlib import Path

from atguigu.chitchat.chitchat_handler import ChitchatHandler
from atguigu.chitchat.chitchat_responder import ChitchatResponder
from atguigu.clarify.clarify_responder import ClarifyResponder
from atguigu.domain.knowledge import KNOWLEDGE_INTENTS
from atguigu.engine.dialogue_engine import DialogueEngine
from atguigu.knowledge.knowledge_handler import KnowledgeHandler
from atguigu.knowledge.providers import KnowledgeProvider, build_default_providers
from atguigu.knowledge.responder import KnowledgeResponder
from atguigu.plan.turn_plan_validator import TurnPlanValidator
from atguigu.plan.turn_planner import TurnPlanner
from atguigu.task.action.builder import build_action_runner
from atguigu.task.command.processor import CommandProcessor
from atguigu.task.flow.flow_executor import FlowExecutor
from atguigu.task.flow.load_flow import FlowLoader
from atguigu.task.lifecycle.responder import TaskLifecycleResponder
from atguigu.task.response.response_renderer import ResponseRenderer
from atguigu.task.task_handler import TaskHandler


def build_engine()->DialogueEngine:
    flow_path = Path(__file__).parents[2] / "flow_config" / "user_flows.yml"
    loader = FlowLoader()
    flow_catalog = loader.load_many([flow_path])

    command_processor = CommandProcessor()
    lifecycle_responder = TaskLifecycleResponder(flow_catalog)

    action_runner = build_action_runner()

    response_renderer = ResponseRenderer()
    flow_executor = FlowExecutor(action_runner, response_renderer)
    task_handler = TaskHandler(command_processor=command_processor, task_lifecycle_responder=lifecycle_responder, flow_executor=flow_executor, flow_catalog=flow_catalog)

    knowledge_intents = KNOWLEDGE_INTENTS
    providers:list[KnowledgeProvider] = build_default_providers()

    knowledge_responder = KnowledgeResponder()

    knowledge_handler = KnowledgeHandler(knowledge_intents, providers, knowledge_responder)

    return DialogueEngine(
        turn_planner=TurnPlanner(),
        turn_plan_validator=TurnPlanValidator(),
        clarify_responder=ClarifyResponder(),
        task_handler=task_handler,
        knowledge_handler=knowledge_handler,
        chitchat_handler=ChitchatHandler(ChitchatResponder())
    )

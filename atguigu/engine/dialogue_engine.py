import time
import uuid
from dataclasses import asdict

from atguigu.chitchat.chitchat_handler import ChitchatHandler
from atguigu.clarify.clarify_responder import ClarifyResponder
from atguigu.domain.command import SetSlotsCommand
from atguigu.domain.flow_catalog import Flow, FlowStep, CollectSlotStep
from atguigu.domain.messages import UserMessage, ProcessResult, MessageType, BotMessage, MessageObject
from atguigu.domain.plan import TurnPlan, TurnPlanValidationResult, ClarifyReason
from atguigu.domain.state import DialogueState, Turn, FocusedObject
from atguigu.knowledge.knowledge_handler import KnowledgeHandler
from atguigu.plan.turn_plan_validator import TurnPlanValidator
from atguigu.plan.turn_planner import TurnPlanner
from atguigu.task.task_handler import TaskHandler


class DialogueEngine:
    def __init__(self,turn_planner:TurnPlanner,
                 turn_plan_validator:TurnPlanValidator,
                 clarify_responder:ClarifyResponder,
                 task_handler:TaskHandler,
                 knowledge_handler:KnowledgeHandler,
                 chitchat_handler:ChitchatHandler):
        self.turn_planner = turn_planner
        self.turn_plan_validator = turn_plan_validator
        self.clarify_responder = clarify_responder
        self.task_handler = task_handler
        self.knowledge_handler = knowledge_handler
        self.chitchat_handler = chitchat_handler


    async def process_message(self,state:DialogueState,user_message:UserMessage)->ProcessResult:
        self._prepare_session(state)
        turn = Turn(turn_id=str(uuid.uuid4()), user_message=user_message)
        if user_message.type == MessageType.TEXT:
            messages: list[BotMessage] = await self._handle_text_message(state, user_message)

        else:
            messages: list[BotMessage] = await self._handle_object_message(state,user_message)

        turn.bot_messages.extend(messages)
        state.shared_state.current_session().turns.append(turn)
        return ProcessResult(
            sender_id=user_message.sender_id,
            message_id=user_message.message_id,
            messages=messages
        )


    def _prepare_session(self, state:DialogueState):
        current_session = state.shared_state.current_session()
        if current_session is None:
            state.shared_state.start_session()
        else:
            if time.time() - current_session.last_activity_at > 60 * 60:
                state.shared_state.close_current_session()
                state.reset_runtime_for_new_session()
                state.shared_state.start_session()
            else:
                current_session.last_activity_at = time.time()

    async def _handle_text_message(self, state:DialogueState, user_message:UserMessage)->list[BotMessage]|None:

        turn_plan: TurnPlan = await self.turn_planner.predict(state, user_message,self.task_handler.flow_catalog,self.knowledge_handler.knowledge_intents)

        validate_result: TurnPlanValidationResult = self.turn_plan_validator.validate(
            turn_plan,state,self.task_handler.flow_catalog,self.knowledge_handler.knowledge_intents
        )

        if not validate_result.valid:
            if validate_result.reason == ClarifyReason.MISSING_FOCUSED_OBJECT:
                self.pause_active_task(state)
                bot_messages: list[BotMessage] = await self.chitchat_handler.handle(state, user_message)
                return bot_messages
            bot_messages:list[BotMessage] = await self.clarify_responder.respond(validate_result.reason,state,user_message)
            return bot_messages
        else:
            if turn_plan.task:
                bot_messages: list[BotMessage] = await self.task_handler.handle(turn_plan.task.commands,state,user_message)
                return bot_messages
            if turn_plan.knowledge:
                self.pause_active_task(state)
                bot_messages:list[BotMessage] = await self.knowledge_handler.handle(turn_plan.knowledge.intents,state,user_message)
                return bot_messages
            if turn_plan.chitchat:
                self.pause_active_task(state)
                bot_messages: list[BotMessage] = await self.chitchat_handler.handle(state,user_message)
                return bot_messages
        return None

    def pause_active_task(self, state: DialogueState):
        active_task = state.task_state.active_task
        if active_task:
            state.task_state.active_task = None
            state.task_state.paused.append(active_task)


    async def _handle_object_message(self, state: DialogueState, user_message: UserMessage) -> list[BotMessage]:

        message_object: MessageObject | None = user_message.object
        if message_object is None:
            return await self.clarify_responder.respond(ClarifyReason.OBJECT_REQUIRES_INTENT, state, user_message)
        focused_object = FocusedObject(
            **asdict(message_object)
        )
        state.shared_state.focused_object = focused_object

        if_can_fill_slot:bool =  self._can_fill_slots_from_focused_object(state)

        if if_can_fill_slot:
            slots_command:SetSlotsCommand = SetSlotsCommand(command="set_slots")
            if focused_object.type == "order":
                slots_command.slots = {"order_number": focused_object.id}
            if focused_object.type == "book":
                slots_command.slots = {"book_id": focused_object.id}
            bot_messages: list[BotMessage] = await self.task_handler.handle([slots_command],state, user_message)
            return bot_messages
        else:
            bot_messages:list[BotMessage] = await self.clarify_responder.respond(ClarifyReason.OBJECT_REQUIRES_INTENT,state,user_message)
            return bot_messages

    def _can_fill_slots_from_focused_object(self, state:DialogueState)->bool:
        active_task = state.task_state.active_task
        if not active_task:
            return False
        flow:Flow = self.task_handler.flow_catalog.get_flow(active_task.flow_id)
        step:FlowStep = flow.get_step(active_task.step_id)

        if not isinstance(step, CollectSlotStep):
            return False
        focused_object = state.shared_state.focused_object
        if step.slot_name == "order_number" and focused_object.type == "order":
            return True
        if step.slot_name == "book_id" and focused_object.type == "book":
            return True
        return False
from atguigu.domain.command import Command, StartFlowCommand, ResumeTaskCommand, SetSlotsCommand, CancelTaskCommand
from atguigu.domain.flow_catalog import FlowCatalog
from atguigu.domain.knowledge import KnowledgeIntent
from atguigu.domain.plan import TurnPlan, TurnPlanValidationResult, ClarifyReason, TaskTurnPlan, KnowledgeTurnPlan
from atguigu.domain.state import DialogueState



class TurnPlanValidator:
    def __init__(self):
        pass

    def validate(self,turn_plan: TurnPlan,state:DialogueState,flow_catalog:FlowCatalog,knowledge_intents:dict[str,KnowledgeIntent]):
        active_tracks:list[str] = []

        if turn_plan.task is not None:
            active_tracks.append("task")

        if turn_plan.knowledge is not None:
            active_tracks.append("knowledge")

        if turn_plan.chitchat is not None:
            active_tracks.append("chitchat")

        if not active_tracks:
            return TurnPlanValidationResult(valid=False,reason=ClarifyReason.MISSING_TRACK)

        if len(active_tracks) >1:
            return TurnPlanValidationResult(valid=False,reason=ClarifyReason.MULTIPLE_TRACKS)

        active_track = active_tracks[0]

        if active_track == "task":
            validation_result: TurnPlanValidationResult = self._validation_task(turn_plan.task,state,flow_catalog)
            return validation_result
        if active_track == "knowledge":
            validation_result: TurnPlanValidationResult = self._validation_knowledge(turn_plan.knowledge,knowledge_intents,state)
            return validation_result
        return TurnPlanValidationResult(valid=True)

    def _validation_task(self, task_turn_plan:TaskTurnPlan,state:DialogueState, flow_catalog:FlowCatalog)->TurnPlanValidationResult:

        if not task_turn_plan.commands:
            return TurnPlanValidationResult(valid=False,reason=ClarifyReason.MISSING_TASK_COMMANDS)

        start_flow_commands :list[Command] = [command for command in task_turn_plan.commands if isinstance(command,StartFlowCommand)]
        if start_flow_commands and len(start_flow_commands) != 1:
            return TurnPlanValidationResult(valid=False,reason=ClarifyReason.MULTIPLE_START_COMMANDS)

        resume_flow_commands:list[Command] = [command for command in task_turn_plan.commands if isinstance(command,ResumeTaskCommand)]
        if resume_flow_commands and len(resume_flow_commands) != 1:
            return TurnPlanValidationResult(valid=False,reason=ClarifyReason.MULTIPLE_RESUME_COMMANDS)

        for command in task_turn_plan.commands:
            if isinstance(command,StartFlowCommand):
                if command.flow not in flow_catalog.flows:
                    return TurnPlanValidationResult(valid=False,reason=ClarifyReason.INVALID_TASK_COMMAND)

            if isinstance(command,SetSlotsCommand):
                for slot_name in command.slots:
                    if slot_name not in flow_catalog.slots:
                        return TurnPlanValidationResult(valid=False,reason=ClarifyReason.INVALID_TASK_COMMAND)

            if isinstance(command,ResumeTaskCommand):
                paused_task_ids = [paused_task.task_id for paused_task in state.task_state.paused]
                if command.task_id not in paused_task_ids:
                    return TurnPlanValidationResult(valid=False,reason=ClarifyReason.INVALID_TASK_COMMAND)

            if isinstance(command,CancelTaskCommand):
                all_paused_task_ids = [paused_task.task_id for paused_task in state.task_state.paused]
                if state.task_state.active_task:
                    all_paused_task_ids.append(state.task_state.active_task.task_id)
                if command.task_id not in all_paused_task_ids:
                    return TurnPlanValidationResult(valid=False,reason=ClarifyReason.INVALID_TASK_COMMAND)

        return TurnPlanValidationResult(valid=True)

    def _validation_knowledge(self, knowledge_turn_plan:KnowledgeTurnPlan,knowledge_intents:dict[str,KnowledgeIntent], state:DialogueState)->TurnPlanValidationResult:

        if not knowledge_turn_plan.intents:
            return TurnPlanValidationResult(valid=False,reason=ClarifyReason.MISSING_KNOWLEDGE_INTENT)

        for intent_id in knowledge_turn_plan.intents:
            if intent_id not in knowledge_intents:
                return TurnPlanValidationResult(valid=False,reason=ClarifyReason.UNKNOWN_KNOWLEDGE_INTENT)

            knowledge_intent = knowledge_intents.get(intent_id)

            requires_object = knowledge_intent.requires_object

            focused_object = state.shared_state.focused_object

            if requires_object and (focused_object is None or focused_object.type != requires_object):
                return TurnPlanValidationResult(valid=False,reason=ClarifyReason.MISSING_FOCUSED_OBJECT)
        return TurnPlanValidationResult(valid=True)


        
                
                    
        





















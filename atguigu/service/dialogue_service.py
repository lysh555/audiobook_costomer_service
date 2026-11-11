from atguigu.domain.messages import UserMessage, ProcessResult
from atguigu.domain.state import DialogueState
from atguigu.engine.dialogue_engine import DialogueEngine
from atguigu.repository.dialogue_state_record_repository import DialogueStateRecordRepository

class DialogueService:
    """业务层职责：1.加载对话状态  2.调用对话引擎（修改对话状态）得到客服回复 3.保存/更新对话状态 4.响应本轮回复"""

    def __init__(self,dialogue_state_repository:DialogueStateRecordRepository,dialogue_engine:DialogueEngine):
        self.dialogue_state_repository=dialogue_state_repository
        self.dialogue_engine = dialogue_engine

    async def process_message(self,user_message:UserMessage)->ProcessResult:

        state:DialogueState = await self.dialogue_state_repository.load_state(user_message.sender_id)

        process_result:ProcessResult = await self.dialogue_engine.process_message(state,user_message)

        await self.dialogue_state_repository.save_state(state)

        return process_result

    async def get_state(self, sender_id:str)->DialogueState:
        state:DialogueState = await self.dialogue_state_repository.load_state(sender_id)
        return state



















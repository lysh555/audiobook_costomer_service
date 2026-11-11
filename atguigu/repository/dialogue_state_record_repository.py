from dataclasses import dataclass

from pydantic import TypeAdapter
from sqlalchemy.dialects.mysql import Insert, insert
from sqlalchemy.ext.asyncio import AsyncSession

from atguigu.domain.state import DialogueState
from atguigu.models.dialogue_state_record import DialogueStateRecord

DIALOGUE_STATE_ADAPTER = TypeAdapter(DialogueState)

class DialogueStateRecordRepository:

    def __init__(self,session:AsyncSession):
        self.session=session


    async def load_state(self,sender_id)->DialogueState:
        record:DialogueStateRecord|None = await self.session.get(DialogueStateRecord,sender_id)

        if record is None:
            return DialogueState(sender_id=sender_id)

        return DIALOGUE_STATE_ADAPTER.validate_json(record.state_json)

    async def save_state(self,state:DialogueState):
        state_json = DIALOGUE_STATE_ADAPTER.dump_json(state).decode('utf-8')
        insert_stmt:Insert = insert(DialogueStateRecord).values(sender_id=state.sender_id,state_json=state_json)
        update_stmt = insert_stmt.on_duplicate_key_update(state_json = insert_stmt.inserted.state_json)
        await self.session.execute(update_stmt)
        await self.session.commit()
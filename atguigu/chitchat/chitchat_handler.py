from atguigu.chitchat.chitchat_responder import ChitchatResponder
from atguigu.domain.messages import UserMessage, BotMessage
from atguigu.domain.state import DialogueState, Turn


class ChitchatHandler:
    def __init__(self, chitchat_responder:ChitchatResponder):
        self.chitchat_responder = chitchat_responder

    async def handle(self,state:DialogueState,user_message:UserMessage)->list[BotMessage]:

        recent_turns:list[Turn] = state.shared_state.current_session().turns
        bot_message:BotMessage = await self.chitchat_responder.respond(recent_turns,user_message)
        return [bot_message]
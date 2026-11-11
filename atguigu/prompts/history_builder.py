import json
from dataclasses import asdict

from atguigu.domain.messages import UserMessage, MessageType, BotMessage
from atguigu.domain.state import Turn


class HistoryBuilder:
    @classmethod
    def render_user_message(cls, user_message:UserMessage)->str:
        if user_message.type == MessageType.TEXT:
            return f"USER: {user_message.text.strip()}"
        else:
            return f"USER: {json.dumps(asdict(user_message.object),ensure_ascii=False)}"

    @classmethod
    def render_bot_message(cls,bot_message:BotMessage)->str:
        if bot_message.text:
            return f"BOT:{bot_message.text.strip()}"
        else:
            return f"BOT:{json.dumps(asdict(bot_message.object),ensure_ascii=False)}"


    @classmethod
    def build(cls, turns:list[Turn])->str:
        messages:list[str] = []
        for turn in turns:
            messages.append(HistoryBuilder.render_user_message(turn.user_message))

            for bot_message in turn.bot_messages:
                messages.append(HistoryBuilder.render_bot_message(bot_message))

        return "\n".join(messages)
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
    def build(cls, turns:list[Turn], max_turns:int|None=20, max_chars:int|None=4000)->str:
        if max_turns is not None and len(turns) > max_turns:
            turns = turns[-max_turns:]

        messages:list[str] = []
        for turn in turns:
            messages.append(HistoryBuilder.render_user_message(turn.user_message))

            for bot_message in turn.bot_messages:
                messages.append(HistoryBuilder.render_bot_message(bot_message))

        text = "\n".join(messages)
        if max_chars is not None and len(text) > max_chars:
            text = "……（更早的对话已省略）\n" + text[-max_chars:]
        return text
from pydantic import BaseModel, Field, model_validator

class ChatObject(BaseModel):
    type:str
    id:str
    title:str|None=None
    attributes:dict={}

class ChatRequest(BaseModel):
    sender_id:str
    text:str|None = None
    object:ChatObject |None=None
    message_id:str|None = None

    @model_validator(mode="after")
    def validate_content(self):
        if not (self.text or "").strip() and self.object is None:
            raise ValueError("text 与 object 至少需要提供一个")
        return self

class ChatBotMessage(BaseModel):
    text:str|None=None
    object:ChatObject|None=None

class ChatResponse(BaseModel):
    sender_id:str
    message_id:str
    messages:list[ChatBotMessage]=Field(default_factory=list)

class HistoryMessage(BaseModel):
    role:str
    text:str|None=None
    object:ChatObject|None=None

class HistoryResponse(BaseModel):
    sender_id:str
    messages:list[HistoryMessage]
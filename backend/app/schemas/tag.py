from pydantic import BaseModel, Field

class TagBase(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    color: str | None = Field(None, pattern="^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$")

class TagCreate(TagBase):
    pass

class TagUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=50)
    color: str | None = Field(None, pattern="^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$")

class TagRead(TagBase):
    id: int

    model_config = {"from_attributes": True}

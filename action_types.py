from pydantic import BaseModel

# action
class Tap(BaseModel):
    x: int
    y: int


# action
class Text(BaseModel):
    input_str: str


# action
class LongPress(BaseModel):
    x: int
    y: int


# action
class Swipe(BaseModel):
    x: int
    y: int
    direction: str
    dist: str
    quick: bool

class Back(BaseModel): pass
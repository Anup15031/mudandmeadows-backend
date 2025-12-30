from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class TestModel(BaseModel):
    name: str

@app.get("/")
def read_root():
    return {"message": "Hello World"}

@app.post("/test")
def test_post(item: TestModel):
    return item

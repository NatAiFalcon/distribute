

from typing import Union
from fastapi import FastAPI, HTTPException
import logging
# FastAPI 애플리케이션 생성
app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/uwb/{tag_id}")
def read_item(tag_id: int):
    try:
        temp_filename = "temp" + str(tag_id)
        with open(temp_filename + ".txt", 'r') as f:
            line = f.readline()
        return line
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        raise HTTPException(status_code=404, detail="Not Vaild tag ID")


# uwb의 좌표를 보내는 api server
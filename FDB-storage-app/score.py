from fastapi import FastAPI, File, UploadFile


# import numpy as np
# import pandas as pd
import uvicorn
from main import *
from fastapi import FastAPI, Depends
from fastapi_health import health

# def get_session():
#     return True


# def is_database_online(session: bool = Depends(get_session)):
#     return session

def healthy_condition():
    return {"healthy": True}


def healthy():
    return True

def sick():
    return False

app = FastAPI()
app.add_api_route("/health", health([healthy_condition, healthy]))


@app.post('/predict')
# async def predict_entity(file: UploadFile = File(...)):
#     extension = file.filename.split(".")[-1] in ("jpg", "jpeg", "png")
#     # print(extension)
#     return final(file)

async def predict_entity():
    return batch_predict()

if __name__ == "__main__":
    uvicorn.run(app)

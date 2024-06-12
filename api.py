from fastapi import FastAPI, HTTPException, Depends, status, Header, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from models import User, HeapLeachingPad, Wobbler, Flights, Breakage, TimePeriod, PadCreate
from sqlalchemy import create_engine, func, and_
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from db import *
import classificator, detector
import os
from settings import config
import httpx
from fastapi.responses import FileResponse
app = FastAPI()
@app.get('/')
async def root():
    return {"message": "Hello World"}

# @app.get('/api/get_logs/')
async def get_last_flight_from_airdata():
    url = "https://api.airdata.com/flights?sort=time"
    auth = ('ad_2DiijUW6ecnT5ZuRib7amdMKJAwrg', '')
    timeout = 10.0  # Timeout limit in seconds
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(url, auth=auth)
        csv_link = response.json()["data"][-1]["csvLink"]
        file_response = await client.get(csv_link)
        
    # Define the local file path where you want to save the file
    file_path = "flight_logs.csv"

    # Write the content of the response to a file
    with open(file_path, 'wb') as f:
        f.write(file_response.content)

    return file_path
# for all pads
@app.post('/api/fields', tags=["Fields"])
async def create_field(field: PadCreate, db: Session = Depends(get_db)):
    db.add(HeapLeachingPad(**field.dict()))
    db.commit()
    return field

@app.get('/api/fields', tags=["Fields"])
async def get_fields(db: Session = Depends(get_db)):
    fields = db.query(HeapLeachingPad).all()
    return fields

# @app.get('/api/wobblers', tags=["All pads"])
# async def get_wobblers(db: Session = Depends(get_db)):
#     wobblers = db.query(Wobbler).all()
#     return wobblers

# @app.get('/api/wobblers/count', tags=["All pads"])
# async def get_wobblers_count(db: Session = Depends(get_db)):
#     wobblers_count = db.query(Wobbler).count()
#     return wobblers_count

# @app.get('/api/wobblers/breakages', tags=["All pads"])
# async def get_breakages(db: Session = Depends(get_db)):
#     breakages = db.query(Breakage).all()
#     return breakages

# @app.get('/api/wobblers/breakages_today', tags=["All pads"])
# async def get_breakages_today(db: Session = Depends(get_db)):
#     today = datetime.today().date()
#     breakages_today = db.query(Breakage).filter(Breakage.time_of_detection >= today).all()
#     return breakages_today

# @app.get('/api/wobblers/breakages_last_week', tags=["All pads"])
# async def get_breakages_last_week(db: Session = Depends(get_db)):
#     today = datetime.today().date()
#     last_week = today - timedelta(days=7)
#     breakages_last_week = db.query(Breakage).filter(Breakage.time_of_detection >= last_week, Breakage.time_of_detection < today).all()
#     return breakages_last_week

@app.get('/api/wobblers/breakages_this_month', tags=["All pads"])
async def get_breakages_this_month(db: Session = Depends(get_db)):
    today = datetime.today().date()
    start_of_month = today.replace(day=1)
    breakages_this_month = db.query(Breakage).filter(Breakage.time_of_detection >= start_of_month, Breakage.time_of_detection < today).all()
    return breakages_this_month

# @app.get('/api/wobblers/breakages_over_period', tags=["All pads"])
# async def get_breakages_over_period(start_date: datetime, end_date: datetime, db: Session = Depends(get_db)):
#     breakages_over_period = db.query(Breakage.id).filter(Breakage.time_of_detection_of_breakage >= start_date, Breakage.time_of_detection_of_breakage < end_date).all()
#     return breakages_over_period

# # per heap leaching pad

@app.get('/api/wobblers/{heap_leaching_pad_id}', tags=["Per heap leaching pad"])
async def get_wobblers(heap_leaching_pad_id:int, db: Session = Depends(get_db)):
    wobblers = db.query(Wobbler).filter(Wobbler.heap_leaching_pad_id==heap_leaching_pad_id).all()
    return wobblers

# @app.get('/api/wobblers/count/{heap_leaching_pad_id}', tags=["Per heap leaching pad"])
# async def get_wobblers_count(heap_leaching_pad_id:int, db: Session = Depends(get_db)):
#     wobblers_count = db.query(Wobbler).filter(Wobbler.heap_leaching_pad_id==heap_leaching_pad_id).count()
#     return wobblers_count


# @app.get('/api/wobblers/breakages_count/{heap_leaching_pad_id}', tags=["Per heap leaching pad"])
# async def get_breakages_count(heap_leaching_pad_id: int, db: Session = Depends(get_db)):
#     breakages_count = db.query(Breakage).filter(Breakage.heap_leaching_pad_id==heap_leaching_pad_id).count()
#     breakages_count_working_not_spinning = db.query(Breakage).filter(Breakage.heap_leaching_pad_id==heap_leaching_pad_id, Breakage.status=="working_not_spinning").count()
#     breakages_count_not_spinning = db.query(Breakage).filter(Breakage.heap_leaching_pad_id==heap_leaching_pad_id, Breakage.status=="not_spinning").count()
#     return {
#         "total": breakages_count,
#         "working_not_spinning": breakages_count_working_not_spinning,
#         "not_spinning": breakages_count_not_spinning
#     }

# @app.get('/api/wobblers/breakages_today/{heap_leaching_pad_id}', tags=["Per heap leaching pad"])
# async def get_breakages_today(heap_leaching_pad_id: int, db: Session = Depends(get_db)):
#     today = datetime.today().date()
#     breakages_today = db.query(Breakage).filter(Breakage.time_of_detection >= today, Breakage.heap_leaching_pad_id==heap_leaching_pad_id).all()
#     return breakages_today

# @app.get('/api/wobblers/breakages_last_week/{heap_leaching_pad_id}', tags=["Per heap leaching pad"])
# async def get_breakages_last_week(heap_leaching_pad_id: int, db: Session = Depends(get_db)):
#     today = datetime.today().date()
#     last_week = today - timedelta(days=7)
#     breakages_last_week = db.query(Breakage).filter(Breakage.time_of_detection >= last_week, Breakage.time_of_detection < today, Breakage.heap_leaching_pad_id==heap_leaching_pad_id).all()
#     return breakages_last_week

# @app.get('/api/wobblers/breakages_this_month/{heap_leaching_pad_id}', tags=["Per heap leaching pad"])
# async def get_breakages_this_month(heap_leaching_pad_id: int, db: Session = Depends(get_db)):
#     today = datetime.today().date()
#     start_of_month = today.replace(day=1)
#     breakages_this_month = db.query(Breakage).filter(Breakage.time_of_detection >= start_of_month, Breakage.time_of_detection < today, Breakage.heap_leaching_pad_id==heap_leaching_pad_id).all()
#     return breakages_this_month

# @app.get('/api/wobblers/breakages/months/{heap_leaching_pad_id}', tags=["Per heap leaching pad"])
# def count_breakages_per_month(heap_leaching_pad_id: int, db: Session = Depends(get_db)):
#     today = datetime.today().date()
#     start_of_month = today.replace(day=1)
#     breakages_this_month = db.query(Breakage).filter(Breakage.time_of_detection >= start_of_month, Breakage.time_of_detection < today, Breakage.heap_leaching_pad_id==heap_leaching_pad_id).count()
#     return breakages_this_month

# @app.get('/api/wobblers/breakages_over_period/{heap_leaching_pad_id}', tags=["Per heap leaching pad"])
# async def get_breakages_over_period(heap_leaching_pad_id: int, start_date: datetime, end_date: datetime, db: Session = Depends(get_db)):
#     breakages_over_period = db.query(Breakage.id).filter(Breakage.time_of_detection_of_breakage >= start_date, Breakage.time_of_detection_of_breakage < end_date, Breakage.heap_leaching_pad_id==heap_leaching_pad_id).all()
#     return breakages_over_period



# @app.post('/api/wobblers/{heap_leaching_pad_id}', tags=["Per heap leaching pad"])
# async def create_wobbler(heap_leaching_pad_id, csv_file: UploadFile = File(...), db: Session = Depends(get_db)):
#     try:
#         create_wobblers_from_csv(heap_leaching_pad_id, db, csv_file.file)
#     except Exception as e:
#         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
#     return {"message": "Wobblers created successfully"}


@app.get('/api/breakages/months/{heap_leaching_pad_id}', tags=["07:Per heap leaching pad"])
async def get_breakages_count_per_date(heap_leaching_pad_id: int, period: TimePeriod, db: Session = Depends(get_db)):
    breakages_count_per_date = db.query(func.date(Breakage.time_of_detection), func.count(Breakage.id)).filter(Breakage.heap_leaching_pad_id==heap_leaching_pad_id, Breakage.time_of_detection >= period.start, Breakage.time_of_detection < period.end).group_by(func.date(Breakage.time_of_detection)).all()
    return breakages_count_per_date

@app.get('/api/breakages/{heap_leaching_pad_id}', tags=["07:Per heap leaching pad"])
async def get_breakages(heap_leaching_pad_id: int, db: Session = Depends(get_db)):
    breakages = db.query(Breakage).filter(Breakage.heap_leaching_pad_id==heap_leaching_pad_id).all()
    return breakages

@app.get('/api/breakages/repeating/{heap_leaching_pad_id}', tags=["07:Per heap leaching pad"])
async def get_breakages_repeating(heap_leaching_pad_id: int, db: Session = Depends(get_db)):
    """
    Count all wobblers which are repeatedly broken two or more times
    """
    count_repeating = db.query(Breakage.wobbler_id).filter(Breakage.heap_leaching_pad_id==heap_leaching_pad_id, Breakage.is_last_breakage==True).group_by(Breakage.wobbler_id).having(func.count(Breakage.wobbler_id) > 1).count()
    return count_repeating


@app.get('/api/flights/last/{heap_leaching_pad_id}', tags=["07:Per heap leaching pad"])
async def get_last_flight(heap_leaching_pad_id:int, db: Session = Depends(get_db)):
    last_flight = db.query(Flights).filter(Flights.heap_leaching_pad_id==heap_leaching_pad_id, Flights.when!=None).order_by(Flights.when.desc()).first()
    return last_flight.when

@app.get('/api/flights/{heap_leaching_pad_id}', tags=["07:Per heap leaching pad"])
async def get_flights(heap_leaching_pad_id:int, db: Session = Depends(get_db)):
    flights = db.query(Flights).filter(Flights.heap_leaching_pad_id==heap_leaching_pad_id).all()

    res = {
        'count': len(flights),
        'flights': flights
    }
    return res

@app.get('/api/flights/last/breakages/{heap_leaching_pad_id}', tags=["07:Per heap leaching pad"])
async def get_last_flight_breakages(heap_leaching_pad_id:int, db: Session = Depends(get_db)):
    last_flight = db.query(Flights).filter(Flights.heap_leaching_pad_id==heap_leaching_pad_id, Flights.when!=None).order_by(Flights.when.desc()).first()
    # breakages = db.query(Breakage).filter(Breakage.flight_id==last_flight.id).all()
    # count by breakage status
    working = db.query(Breakage).join(Breakage.wobbler).filter(Breakage.flight_id==last_flight.id, Wobbler.status=="working").count()
    not_working = db.query(Breakage).join(Breakage.wobbler).filter(Breakage.flight_id==last_flight.id, Wobbler.status=="not_working").count()
    return {
        'working': working,
        'not_working': not_working
    }

@app.get('/api/map/{heap_leaching_pad_id}', tags=["07:Per heap leaching pad"])
async def get_wobblers_map(heap_leaching_pad_id:int, db: Session = Depends(get_db)):
    # return image file i have
    # get absoulute path based on the relative path i provide
    # return FileResponse("full_map_0080.png")
    try:
        file =  os.path.abspath("paper_image.png")
    except Exception as e:
        print(e)
        file = "full_map.png"
    return FileResponse(file)

# # TODO: Change to map png response
# @app.get('/api/map/{heap_leaching_pad_id}', tags=["Per heap leaching pad"])
# async def get_wobblers_map(heap_leaching_pad_id:int, db: Session = Depends(get_db)):
#     """
#     Change later, meanwhile return default for pad 2

#     """
#     if heap_leaching_pad_id==2:
#         res = {}
#         res[1] = [0,0,0,0,0,0,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
#         res[2] = [1,1,0,0,2,0,0,0,0,0,2,0,0,0,0,0,0,0,0,0,0,2]
#         res[3] = [1,0,0,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,0,0,1,0]
#         res[4] = [1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
#         res[5] = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
#         res[6] = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,2,1,0,0]
#         return res
#     return None


@app.get('/api/efficiency/{heap_leaching_pad_id}', tags=["07:Per heap leaching pad"])
async def get_efficiency(heap_leaching_pad_id:int, db: Session = Depends(get_db)):
    """
    calculate by counting the number of breakages with value is_last==true and number of all wobblers on a pad
    """
    count_breakages = db.query(Breakage).filter(Breakage.heap_leaching_pad_id==heap_leaching_pad_id, Breakage.is_last_breakage==True).count()
    count_wobblers = db.query(Wobbler).filter(Wobbler.heap_leaching_pad_id==heap_leaching_pad_id).count()
    return 1-count_breakages/count_wobblers

@app.post('/api/load_data', tags=["07:Per heap leaching pad"])
async def load_data(csv_file: UploadFile = File(...), video_file: UploadFile = File(...), db: Session = Depends(get_db)):
    csv_path = f"./{csv_file.filename}"
    video_path = f"./{video_file.filename}"
    # csv_path = "May-17th-2024-03-08PM-Flight-Airdata.csv"
    # video_path="MAX_0004_02_27.MP4"
    # save video and csv file locally
    if not os.path.exists(csv_path):
        with open(csv_path, "wb") as file:
            file.write(csv_file.file.read())
    if not os.path.exists(video_path):
        with open(video_path, "wb") as file:
            file.write(video_file.file.read())
        
    detection =  detector.Detector(csv_path, video_path)
    classification = classificator.Detector(video_path, csv_path)
    detection.start_detection()
    classification.start_classification()
    
    # remove the files afterwards
    os.remove(csv_path)
    os.remove(video_path)
    # remove videos/dataset folder
    os.system("rm -r videos/dataset")
    # create dataset folder
    os.system("mkdir videos/dataset")

    try:
        print("here")
        create_wobblers_from_json(1, 1, db, 'output.json')
        print("here2")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    return "success"

# @app.post('/api/load_data', tags=["07:Per heap leaching pad"])
# async def load_data(db: Session = Depends(get_db)):
#     # csv_path = f"./{csv_file.filename}"
#     # video_path = f"./{video_file.filename}"
#     # # save video and csv file locally
#     # with open(csv_path, "wb") as file:
#     #     file.write(csv_file.file.read())
#     # with open(video_path, "wb") as file:
#     #     file.write(video_file.file.read())
    
#     # detection =  detector.Detector(csv_path, video_path)
#     # classification = classificator.Detector(video_path, csv_path)
#     # detection.start_detection()
#     # classification.start_classification()
    
#     # # remove the files afterwards
#     # os.remove(csv_path)
#     # os.remove(video_path)
#     try:
#         create_wobblers_from_json(1, 1, db, 'output.json')
#     except Exception as e:
#         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
#     return "success"



app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
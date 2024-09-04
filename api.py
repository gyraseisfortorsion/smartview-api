from fastapi import FastAPI, HTTPException, Depends, status, Header, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from models import User, HeapLeachingPad, Wobbler, Flights, Breakage, TimePeriod, PadCreate
from sqlalchemy import create_engine, func, and_, cast, Date
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from db import *
import classificator, detector
import os
from settings import config
import httpx
from typing import Optional
from datetime import datetime, timedelta
from fastapi.responses import FileResponse
app = FastAPI()
@app.get('/')
async def root():
    return {"message": "Hello World"}


@app.get('/api/get_logs/')
async def get_last_flight_from_airdata(start: Optional[str] = None, end: Optional[str] = None):
    url = "https://api.airdata.com/flights"
    auth = ('ad_2DiijUW6ecnT5ZuRib7amdMKJAwrg', '')
    timeout = 10.0  # Timeout limit in seconds
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(url, auth=auth)
        print(response.json())
        
        data = response.json()["data"]
        
        # Convert start and end to datetime objects
        start_date = datetime.strptime(start, "%Y-%m-%d %H:%M:%S")
        end_date = datetime.strptime(end, "%Y-%m-%d %H:%M:%S")

        # Find the first object whose 'time' is within the range
        iter=0
        for obj in data:
            obj_time = datetime.strptime(obj["time"], "%Y-%m-%d %H:%M:%S")
            # print(obj_time, start_date, end_date)
            if start_date <= obj_time <= end_date:
                print(obj)
                csv_link = response.json()["data"][iter]["csvLink"]
                file_response = await client.get(csv_link)
                break
            iter+=1

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



@app.get('/api/wobblers/breakages/by_field', tags=["All pads"])
async def get_breakages_by_field(
    db: Session = Depends(get_db),
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None
):
    query = db.query(HeapLeachingPad, func.count(Breakage.id)).join(Breakage)

    if date_from:
        query = query.filter(Breakage.time_of_detection >= date_from)
    if date_to:
        query = query.filter(Breakage.time_of_detection <= date_to)

    breakages_by_field = query.group_by(HeapLeachingPad.id).all()

    # Convert the HeapLeachingPad objects to dictionaries
    breakages_by_field = [{"field_id": heap_leaching_pad.id, "breakages": count} for heap_leaching_pad, count in breakages_by_field]
    return breakages_by_field


@app.get('/api/wobblers/breakages/efficiency', tags=["All pads"], description="Get the efficiency of each field based on the number of breakages and wobblers, returns field id and its efficiency")
async def get_breakages_efficiency(db: Session = Depends(get_db)):
    # Query the number of breakages and wobblers for each field
    breakages_by_field = db.query(HeapLeachingPad, func.count(Breakage.id)).join(Breakage).group_by(HeapLeachingPad.id).all()
    wobblers_by_field = db.query(HeapLeachingPad, func.count(Wobbler.id)).join(Wobbler).group_by(HeapLeachingPad.id).all()

    # Convert the query results to dictionaries for easier access
    breakages_by_field = {heap_leaching_pad.id: count for heap_leaching_pad, count in breakages_by_field}
    wobblers_by_field = {heap_leaching_pad.id: count for heap_leaching_pad, count in wobblers_by_field}

    # Calculate the efficiency for each field
    efficiencies = []
    for field_id in wobblers_by_field.keys():
        count_breakages = breakages_by_field.get(field_id, 0)
        count_wobblers = wobblers_by_field[field_id]
        efficiency = 1 - count_breakages / count_wobblers
        efficiencies.append({"field_id": field_id, "efficiency": efficiency})

    return efficiencies

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



@app.get('/api/breakages/count/{heap_leaching_pad_id}', tags=["07:Per heap leaching pad"])
async def get_breakages_count(
    heap_leaching_pad_id: int, 
    db: Session = Depends(get_db),
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None
):
    # If no date range is provided, default to the last 30 days
    if not date_from:
        date_from = datetime.now() - timedelta(days=30)
    if not date_to:
        date_to = datetime.now()

    # Query the number of breakages per day
    query = (
        db.query(
            func.count(Breakage.id),
            cast(Breakage.time_of_detection, Date)
        )
        .filter(
            Breakage.heap_leaching_pad_id == heap_leaching_pad_id,
            Breakage.time_of_detection >= date_from,
            Breakage.time_of_detection <= date_to
        )
        .group_by(cast(Breakage.time_of_detection, Date))
        .all()
    )

    # Convert the query result to a list of dictionaries
    breakages_count = [{"date": date.isoformat(), "count": count} for count, date in query]
    return breakages_count

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

# @app.get('/api/flights/last/breakages/{heap_leaching_pad_id}', tags=["07:Per heap leaching pad"])

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
    # working = db.query(Breakage).join(Breakage.wobbler).filter(Breakage.flight_id==last_flight.id, Wobbler.status=="working").count()
    heap_leaching_pad = db.query(HeapLeachingPad).filter(HeapLeachingPad.id == heap_leaching_pad_id).first()
    if not heap_leaching_pad:
        return {"error": "Heap leaching pad not found"}, 404
    # working = heap_leaching_pad.number_of_wobblers -
    not_working = db.query(Breakage).join(Breakage.wobbler).filter(Breakage.flight_id==last_flight.id, Wobbler.status=="not_working").count()
    working = heap_leaching_pad.number_of_wobblers - not_working
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
async def load_data(srt_file: UploadFile = File(...), video_file: UploadFile = File(...), db: Session = Depends(get_db)):
    # csv_path = f"./{csv_file.filename}"
    video_path = f"./{video_file.filename}"
    srt_path = f"./{srt_file.filename}"
    #csv_path = "May-17th-2024-03-08PM-Flight-Airdata.csv"
    csv_path = ""
    # video_path="MAX_0004_02_27.MP4"
    # save video and csv file locally
    if not os.path.exists(srt_path):
        with open(srt_path, "wb") as file:
            file.write(srt_file.file.read())
    if not os.path.exists(video_path):
        with open(video_path, "wb") as file:
            file.write(video_file.file.read())
        
    detection =  detector.Detector(csv_path, video_path, srt_path)
    classification = classificator.Detector(video_path, srt_path)
    print("starting detection")
    detection.start_detection()
    print("detection finished")
    os.system("rm -r videos/dataset/crops")
    print("classification started")
    classification.start_classification()
    
    # remove the files afterwards
    # os.remove(csv_path)
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

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from models import User, HeapLeachingPad, Wobbler, Breakage, Flights
from settings import Config
import uuid
from datetime import datetime, timedelta
import json

config = Config()
engine = create_engine(config.DATABASE_URL)
Base = declarative_base()
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()



def create_wobblers_from_csv(heap_leaching_pad_id: int, session: Session, csv_file):
        breakages = {}
        # add newly detected wobblers to the database
        for line in csv_file.readlines()[0:-1]:
            line = line.decode().split(',')
            wobbler = Wobbler(
                heap_leaching_pad_id=heap_leaching_pad_id,
                number_of_breakages=0,
                number_of_fixes=0,
                latitude=float(line[1]),
                longitude=float(line[2]),
                time_of_detection_of_breakage=datetime.now(),
                status=line[3][0:-1]
            )
            session.add(wobbler)
            if (line[3][0:-1]!="spinning"):
                session.commit()
                breakages[wobbler.id] = line
            else:
                session.flush()
        # add breakages to the database
        for breakage in breakages:
            breakage = Breakage(
                wobbler_id=breakage,
                time_of_detection=datetime.now(),
                time_of_repair=datetime.now() + timedelta(days=1),
                status=breakages[breakage][3][0:-1],
                is_last_breakage=True,
                heap_leaching_pad_id=heap_leaching_pad_id
            )
            session.add(breakage)
        session.commit()

def create_wobblers_from_json(flight_id: int, heap_leaching_pad_id: int, session: Session, path_json_file):
    with open(path_json_file, 'r') as json_file:
        json_file = json_file.read()
        json_file = json.loads(json_file)
        breakages = {}
        flight =  Flights(
            when=datetime.now(),
            status=True,
            heap_leaching_pad_id=heap_leaching_pad_id
        )
        session.add(flight)
        
        heap_leaching_pad = session.query(HeapLeachingPad).filter_by(id=heap_leaching_pad_id).first()
        if not heap_leaching_pad:
            raise ValueError("HeapLeachingPad not found")

        # Update the number_of_wobblers
        heap_leaching_pad.number_of_wobblers = len(json_file)
        session.add(heap_leaching_pad)
        # add newly detected wobblers to the database
        for line in json_file:
            # print(line)
            wobbler = Wobbler(
                heap_leaching_pad_id=heap_leaching_pad_id,
                number_of_breakages=0,
                number_of_fixes=0,
                latitude=line['latitude'],
                longitude=line['longitude'],
                time_of_detection_of_breakage=datetime.now(),
                status=line['predicted_class']
            )
            session.add(wobbler)
            if (line['predicted_class']!="working"):
                session.commit()
                breakages[wobbler.id] = line
            else:
                session.flush()

        # add breakages to the database
        for breakage in breakages:
            breakage = Breakage(
                wobbler_id=breakage,
                time_of_detection=datetime.now(),
                time_of_repair=datetime.now() + timedelta(days=1),
                status=breakages[breakage]['predicted_class'],
                is_last_breakage=True,
                heap_leaching_pad_id=heap_leaching_pad_id,
                flight_id=flight.id
            )
            session.add(breakage)
        

        session.commit()

def get_db():
    try:
        db = Session()
        yield db
    finally:
        db.close()

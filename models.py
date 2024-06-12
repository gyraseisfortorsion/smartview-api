from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Boolean, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    role = Column(String)  # operator, worker, management

class HeapLeachingPad(Base):
    __tablename__ = 'heap_leaching_pads'

    id = Column(Integer, primary_key=True)
    number_of_tube_lines = Column(Integer)
    rows_of_tube_lines = Column(Integer)
    columns_of_tube_lines = Column(Integer)
    number_of_wobblers = Column(Integer)
    width = Column(Float)
    length = Column(Float)
    height = Column(Float)
    operational_life = Column(Integer)

    # relationships
    wobblers = relationship('Wobbler', back_populates='heap_leaching_pad')
    breakages = relationship('Breakage', back_populates='heap_leaching_pad')
    flights = relationship('Flights', back_populates = 'heap_leaching_pad')

class StatusEnum(Enum):
    SPINNING = 'spinning'
    NOT_SPINNING = 'not_spinning'
    IN_REPAIR = 'in_repair'
    SPINNING_NOT_WORKING = 'spinning_not_working'
    REPAIRED = 'repaired'

class Wobbler(Base):
    __tablename__ = 'wobblers'

    id = Column(Integer, primary_key=True)
    heap_leaching_pad_id = Column(Integer, ForeignKey('heap_leaching_pads.id'))
    heap_leaching_pad = relationship('HeapLeachingPad', back_populates='wobblers')
    number_of_breakages = Column(Integer)
    number_of_fixes = Column(Integer)
    latitude = Column(Float)
    longitude = Column(Float)
    time_of_detection_of_breakage = Column(DateTime)
    status = Column(Enum('spinning', 'not_spinning', 'in_repair', 'spinning_not_working', 'repaired', 'working_not_spinning', 'working', 'not_working', name='status_enum'))  # Fix: Use Enum(StatusEnum) as the type for the status column

    # relationships
    heap_leaching_padpad = relationship('HeapLeachingPad', back_populates='wobblers')
    breakages = relationship('Breakage', back_populates='wobbler')
class Breakage(Base):
    __tablename__ = 'breakages'

    id = Column(Integer, primary_key=True)
    wobbler_id = Column(Integer, ForeignKey('wobblers.id'))
    # wobbler = relationship('Wobbler', back_populates='breakages')
    time_of_detection = Column(DateTime)
    time_of_repair = Column(DateTime)
    status = Column(Enum('spinning', 'not_spinning', 'in_repair', 'spinning_not_working', 'repaired', 'working_not_spinning', 'working', 'not_working', name='status_enum'))
    is_last_breakage = Column(Boolean)
    heap_leaching_pad_id = Column(Integer, ForeignKey('heap_leaching_pads.id'))
    flight_id = Column(Integer, ForeignKey('flights.id'))

    # relationships
    wobbler = relationship('Wobbler', back_populates='breakages')
    heap_leaching_pad = relationship('HeapLeachingPad', back_populates='breakages')
    flight = relationship('Flights', back_populates='breakages')

class Flights(Base):
    __tablename__ = 'flights'
    id = Column(Integer, primary_key=True)
    when = Column(DateTime)
    status= Column(Boolean)
    heap_leaching_pad_id = Column(Integer, ForeignKey('heap_leaching_pads.id'))

    # relationships 
    heap_leaching_pad = relationship('HeapLeachingPad', back_populates='flights')
    breakages = relationship('Breakage', back_populates='flight')

# HeapLeachingPad.wobblers = relationship('Wobbler', order_by=Wobbler.id, back_populates='heap_leaching_pad')


# schemas
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class TimePeriod(BaseModel):
    start: datetime
    end: datetime

class PadCreate(BaseModel):
    number_of_tube_lines: int
    rows_of_tube_lines: int
    columns_of_tube_lines: int
    number_of_wobblers: int
    width: float
    length: float
    height: float
    operational_life: int
# from db import create_wobblers_from_json, get_db

# create_wobblers_from_json(1, 1, get_db(), 'output.json')
import re
def extract_minute_second_gps_from_global_time(self, srt_file="MAX_0007.MP4.SRT"):
    with open(srt_file, 'r') as file:
        srt_content = file.read()

    # Split the .srt file into subtitle blocks
    subtitle_blocks = srt_content.strip().split('\n\n')

    # Regular expression to match global time and GPS data
    global_time_pattern = r"\d{4}-\d{2}-\d{2} \d{2}:(\d{2}):(\d{2})"
    gps_pattern = r"GPS\(E: ([0-9.]+), N: ([0-9.]+), [0-9.]+m\)"

    first_minute_second = None
    last_minute_second = None
    first_gps = None
    last_gps = None

    if subtitle_blocks:
        # Extract global time and GPS from the first entry
        first_block = subtitle_blocks[0]
        first_global_time_match = re.search(global_time_pattern, first_block)
        print(first_global_time_match.group(0))
        first_gps_match = re.search(gps_pattern, first_block)
        if first_global_time_match and first_gps_match:
            first_minute, first_second = map(int, first_global_time_match.groups())
            first_minute_second = (first_minute, first_second)
            first_gps = (float(first_gps_match.group(2)), float(first_gps_match.group(1)))  # (latitude, longitude)

        # Extract global time and GPS from the last entry
        last_block = subtitle_blocks[-1]
        last_global_time_match = re.search(global_time_pattern, last_block)
        last_gps_match = re.search(gps_pattern, last_block)
        if last_global_time_match and last_gps_match:
            last_minute, last_second = map(int, last_global_time_match.groups())
            last_minute_second = (last_minute, last_second)
            last_gps = (float(last_gps_match.group(2)), float(last_gps_match.group(1)))  # (latitude, longitude)

    return first_minute_second, last_minute_second, first_gps, last_gps
from datetime import datetime, timedelta
import re

def extract_timestamps(srt_text):
    with open(srt_text, 'r') as file:
        srt_content = file.read()

    # Split the .srt file into subtitle blocks
    subtitle_blocks = srt_content.strip().split('\n\n')

    # Regular expression to match global time and GPS data
    global_time_pattern = r"\d{4}-\d{2}-\d{2} \d{2}:(\d{2}):(\d{2})"

    if subtitle_blocks:
        # Extract global time and GPS from the first entry
        first_block = subtitle_blocks[0]
        first_global_time_match = re.search(global_time_pattern, first_block)
        timestamp_str = first_global_time_match.group(0)

        # Convert the timestamp string to a datetime object
        timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")

        # Calculate the time range
        time_range = (timestamp - timedelta(minutes=1), timestamp + timedelta(minutes=1))

        # Convert the time range to strings
        time_range_str = (time_range[0].strftime("%Y-%m-%d %H:%M:%S"), time_range[1].strftime("%Y-%m-%d %H:%M:%S"))

        return time_range_str
print(extract_minute_second_gps_from_global_time('MAX_0007.MP4.SRT'))
print(extract_timestamps('MAX_0007.MP4.SRT'))
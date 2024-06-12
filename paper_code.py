# Import the required modules
from torchvision.transforms import (
    Compose,
    Lambda,
    RandomCrop,
    RandomHorizontalFlip,
    Resize,
)
from pytorchvideo.transforms import (
    ApplyTransformToKey,
    Normalize,
    RandomShortSideScale,
    RemoveKey,
    ShortSideScale,
    UniformTemporalSubsample,
)
import cv2
from ultralytics import YOLO

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import math
import re
import csv

import torch
from torchvision.transforms import Compose
import pytorchvideo.data
from transformers import VideoMAEForVideoClassification, VideoMAEImageProcessor

import glob
from PIL import Image


import pytorchvideo.data
import re
import csv
import time
import os
from transformers import VideoMAEForVideoClassification, VideoMAEImageProcessor
import pandas as pd
import json
from torchvision.transforms import Compose


# Utility functions
def visualise_path(df):
    # Extract Latitude and Longitude columns
    latitude = df['latitude']
    longitude = df['longitude']
    # Create a scatter plot of the drone path
    plt.figure(figsize=(12, 8))
    plt.scatter(longitude, latitude, c='blue',
                marker='o', s=10, label='Drone Path')
    plt.xlabel('Longitude')
    plt.ylabel('Latitude')
    plt.title('Drone Path Visualization')
    plt.legend()
    plt.grid(True)
    plt.show()


def rhumb_destination(point, distance, bearing, options=None):
    options = options or {}
    units = options.get('units', 'kilometers')

    # Conversion factor based on the chosen unit
    if units == 'miles':
        factor = 3960
    elif units == 'kilometers':
        factor = 6371
    elif units == 'meters':
        factor = 6371000  # 1 kilometer = 1000 meters
    else:
        raise ValueError("Invalid units specified")

    # Convert distance to radians
    rad_dist = distance / factor

    # Convert bearing to radians
    rad_bearing = math.radians(bearing)

    # Convert coordinates to radians
    rad_lat = math.radians(point[1])
    rad_lon = math.radians(point[0])

    # Calculate destination coordinates
    rad_new_lat = rad_lat + rad_dist * math.cos(rad_bearing)
    rad_new_lon = rad_lon + \
        (rad_dist * math.sin(rad_bearing)) / math.cos(rad_new_lat)

    # Convert back to degrees
    new_lat = math.degrees(rad_new_lat)
    new_lon = math.degrees(rad_new_lon)

    # Return the new point
    return new_lon, new_lat


# Function to convert detections' coordinates to GPS coordinates
def convert_to_gps(p, videoHeight, videoWidth, diagonalDistance, center, bearing, options):
    # Change coordinate system so the center point of the video is (0, 0)
    normalized = [p[1] - videoHeight / 2, p[0] - videoWidth / 2]

    # Calculate the distance and bearing of the solar panel relative to the center point
    distanceFromCenterInPixels = math.sqrt(
        (videoWidth / 2 - p[0])**2 + (videoHeight / 2 - p[1])**2)
    diagonalDistanceInPixels = math.sqrt(videoWidth**2 + videoHeight**2)
    percentOfDiagonal = distanceFromCenterInPixels / diagonalDistanceInPixels
    distance = percentOfDiagonal * diagonalDistance  # in meters

    # Calculate the angle
    angle = math.atan(
        normalized[0] / (normalized[1] or 0.000001)) * 180 / math.pi

    # If the detection is in the right half of the frame, rotate it 180 degrees
    if normalized[1] >= 0:
        angle += 180

    # Use distance and bearing to get the GPS location of the panel
    point = rhumb_destination(
        center, distance, (bearing + angle) % 360, options)

    return point


def convert_to_pixel(latitude, longitude, left, right, top, bottom):
    x = int((longitude - left) / (right - left) * map_width)
    y = map_height - int((latitude - bottom) / (top - bottom) * map_height)
    return x, y


def find_gps_distance(point1, point2):
    R = 6371000

    lat1 = math.radians(point1[1])
    lon1 = math.radians(point1[0])

    lat2 = math.radians(point2[1])
    lon2 = math.radians(point2[0])

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = math.sin(dlat / 2)**2 + math.cos(lat1) * \
        math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    distance = R * c

    return distance


def draw(image, point, color, size):
    cv2.circle(image, (image.shape[1]-int(point[0]),
               int(point[1])), size, color, -1)
    return image


def make_average(latitude, longitude, gps_points, name, datetime_log):
    found = 0
    for i, points in enumerate(gps_points):
        for j, point in enumerate(points):
            distance = find_gps_distance(
                (latitude, longitude), (point[0][0], point[0][1]))
            # print("Distance", distance)
            if distance < 3.0:
                # print(f"Distance: {dis}")
                gps_points[i].append(
                    ((latitude, longitude), name, datetime_log))
                found = 1
                break

    if found == 0:
        points = []
        points.append(((latitude, longitude), name, datetime_log))
        gps_points.append(points)

    return gps_points, name


# Load the CSV file into a Pandas DataFrame
csv_file = '0076.csv'  # Replace with the path to your CSV file
observations = pd.read_csv(csv_file)
observations = observations[observations['isVideo'] == 1]


values = ["time(millisecond)", "latitude", "longitude", "compass_heading(degrees)",
          "gimbal_heading(degrees)", "ascent(feet)", 'datetime(utc)']
observations = observations.loc[:, values]
timestamps = list(observations["time(millisecond)"])
latitudes = list(observations["latitude"])
longitudes = list(observations["longitude"])
compass_bearings = list(observations["compass_heading(degrees)"])
altidutes = list(observations["ascent(feet)"])
datetime_logs = list(observations["datetime(utc)"])


# Initialize boundaries
top, bottom, left, right = -np.inf, np.inf, np.inf, -np.inf
extension_factor = 0.0001  # Adjust this factor as needed

for _, o in observations.iterrows():
    # Extend boundaries based on longitude and latitude
    top = max(top, float(o['longitude']) + extension_factor)
    bottom = min(bottom, float(o['longitude']) - extension_factor)
    left = min(left, float(o['latitude']) - extension_factor)
    right = max(right, float(o['latitude']) + extension_factor)


# Calculate the width and height of the map in GPS coordinates
width = right - left
height = top - bottom

map_height = 800
print(f"The width: {width}, the height: {height}")


# map_width = 800
if width/height < 0.5:
    map_width = int(0.5*map_height)
else:
    map_width = int(map_height*(math.radians(width)*6371000.0) /
                    (math.radians(height)*6371000.0))
# round(map_height*(width/height))*2

print(f"The width: {map_width}, the height: {map_height}")

# Assuming you have an 800x800 pixel map

fov = 54/2 * np.pi / 180   # Drone camera field of view in radians
# Multiply by altitude to get distance across the video's diagonal
fov_tan = np.tan(fov)

videoHeight = 1080
videoWidth = 1920

final_image = np.ones((map_height, map_width, 3), dtype=np.uint8)*255
paper_image = np.ones((map_height, map_width, 3), dtype=np.uint8)*255
gps_points = []

# Initialize video capture
model = YOLO('best.pt')

video_path = "DJI 0076.MP4"
cap = cv2.VideoCapture(video_path)

# Get the frames per second (fps) of the video
fps = cap.get(cv2.CAP_PROP_FPS)
# Calculate the frame interval in frames
frame_interval = round(fps * 0.2)  # 0.2 seconds (200 milliseconds)
change = 0
counter = 0
mistake_counter = 0
cumulative_time_difference = 0
current_frame_number = 0


working_directory = os.getcwd()


def run_inference(modelMAE, video):
    perumuted_sample_test_video = video.permute(1, 0, 2, 3)
    inputs = {"pixel_values": perumuted_sample_test_video.unsqueeze(0)}

    device = torch.device(
        "cuda" if torch.cuda.is_available() else "cpu")
    inputs = {k: v.to(device) for k, v in inputs.items()}
    modelMAE = modelMAE.to(device)

    with torch.no_grad():
        outputs = modelMAE(**inputs)
        logits = outputs.logits

    return logits


data_path = os.path.join(working_directory, "0080")
label2id = {'not_working': 0, 'working': 1}
id2label = {0: 'not_working', 1: 'working'}
model_ckpt = os.path.join(working_directory, "videomae_weights")
print(data_path)


modelMAE = VideoMAEForVideoClassification.from_pretrained(
    model_ckpt,
    label2id=label2id,
    id2label=id2label,
    ignore_mismatched_sizes=True,
)

image_processor = VideoMAEImageProcessor.from_pretrained(model_ckpt)
mean = image_processor.image_mean
std = image_processor.image_std
resize_to = 224
num_frames_to_sample = 16
sample_rate = 4
fps = 30
clip_duration = num_frames_to_sample * sample_rate / fps

transform = Compose(
    [
        ApplyTransformToKey(
            key="video",
            transform=Compose(
                [
                    UniformTemporalSubsample(num_frames_to_sample),
                    Lambda(lambda x: x / 255.0),
                    Normalize(mean, std),
                    Resize(resize_to),
                ]
            )
        ),
    ]
)

dataset = pytorchvideo.data.Ucf101(
    data_path=os.path.join(working_directory, "0080"),
    clip_sampler=pytorchvideo.data.make_clip_sampler("uniform", clip_duration),
    decode_audio=False,
    transform=transform,
)

print(dataset.num_videos)

df = pd.read_csv("logs.csv")
df_dict = df.set_index('file_name').T.to_dict('list')

data = []
modelMAE.eval()

with torch.no_grad():
    for i, video in enumerate(iter(dataset)):
        logits = run_inference(modelMAE, video["video"])
        name = video['video_name']
        print("Name of the files is ", name)
        # print(name, modelMAE.config.id2label[logits.argmax(-1).item()])
        predicted_label = modelMAE.config.id2label[logits.argmax(-1).item()]

        longitude, latitude, timestamp = df_dict.get(name, [None, None, None])

        data.append({
            'file_name': name,
            'predicted_class': predicted_label,
            'longitude': longitude,
            'latitude': latitude,
            'timestamp': timestamp
        })

        x_pixel, y_pixel = convert_to_pixel(
            longitude, latitude, left, right, top, bottom)

        if predicted_label == "working":
            paper_image = draw(paper_image, (x_pixel, y_pixel), (0, 255, 0), 4)
        else:
            paper_image = draw(paper_image, (x_pixel, y_pixel), (0, 0, 255), 4)


with open('output.json', 'w') as f:
    json.dump(data, f)


cv2.imshow("GPS by Pixel", final_image)
cv2.imwrite("full_map_0076.png", final_image)
cv2.imwrite("paper_image_0076.png", paper_image)
cv2.waitKey(0)

cap.release()
cv2.destroyAllWindows()

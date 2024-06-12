from ultralytics import YOLO
import cv2
import torch
import numpy as np
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
import math
from geopy.distance import geodesic
import ffmpeg

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


from pytorchvideo.transforms import (
    ApplyTransformToKey,
    Normalize,
    RandomShortSideScale,
    RemoveKey,
    ShortSideScale,
    UniformTemporalSubsample,
)

from torchvision.transforms import (
    Compose,
    Lambda,
    RandomCrop,
    RandomHorizontalFlip,
    Resize,
)
class Detector():
    def __init__(self, video_path, csv_file):
        self.video_path = video_path
        observations = pd.read_csv(csv_file)
		# observations = observations[observations['isVideo'] == 1]



        if (observations['isVideo'] == 1).any() == False:
            print("test")
            # video_path = r"MAX_0004.MP4"
            srt_path = video_path + ".SRT"

            if not os.path.exists(srt_path):
                self.extract_srt(video_path, video_path)

            first_time_tuple, last_time_tuple, first_gps, second_gps = self.extract_minute_second_gps_from_global_time(video_path+".SRT")

            observations = self.update_is_video_column(observations, first_time_tuple, last_time_tuple, first_gps, second_gps)
            observations.to_csv("test.csv", index=False)

        observations = observations[observations['isVideo'] == 1]

        values = [ "time(millisecond)", "latitude", "longitude", " compass_heading(degrees)", "gimbal_heading(degrees)", "ascent(feet)", 'datetime(utc)']
        self.observations = observations.loc[:, values]
        self.timestamps = list(observations["time(millisecond)"])
        self.latitudes = list(observations["latitude"])
        self.longitudes = list(observations["longitude"])
        self.compass_bearings = list(observations[" compass_heading(degrees)"])
        self.altidutes = list(observations["ascent(feet)"])
        self.datetime_logs = list(observations["datetime(utc)"])


        # Initialize boundaries
        self.top, self.bottom, self.left, self.right = -np.inf, np.inf, np.inf, -np.inf
        extension_factor = 0.0001  # Adjust this factor as needed

        for _, o in observations.iterrows():
            # Extend boundaries based on longitude and latitude
            self.top = max(self.top, float(o['longitude']) + extension_factor)
            self.bottom = min(self.bottom, float(o['longitude']) - extension_factor)
            self.left = min(self.left, float(o['latitude']) - extension_factor)
            self.right = max(self.right, float(o['latitude']) + extension_factor)


        # Calculate the width and height of the map in GPS coordinates
        self.width = self.right - self.left
        self.height = self.top - self.bottom

        self.map_height = 800
        print(f"The width: {self.width}, the height: {self.height}")


        # map_width = 800
        if self.width/self.height < 0.5:
            self.map_width = int(0.5*self.map_height)
        else:
            self.map_width = int(self.map_height*(math.radians(self.width)*6371000.0)/(math.radians(self.height)*6371000.0))
        # round(map_height*(width/height))*2

        print(f"The width: {self.map_width}, the height: {self.map_height}")
    
    def draw(self, image, point, color, size):
        cv2.circle(image, (image.shape[1]-int(point[0]),
                int(point[1])), size, color, -1)
        return image

    def convert_to_pixel(self, latitude, longitude, left, right, top, bottom):
        x = int((longitude - left) / (right - left) * self.map_width)
        y = self.map_height - int((latitude - bottom) / (top - bottom) * self.map_height)
        return x, y

    def extract_srt(self, input_file, output_name):
        output_file = output_name+".SRT"
        # Get information about the video file
        # input = input_file+".MP4"
        # print(f"video name: {input}")
        probe = ffmpeg.probe(input_file)

        # Filter out the subtitle streams
        subtitle_streams = [stream for stream in probe['streams'] if stream['codec_type'] == 'subtitle']

        if subtitle_streams:
            # Select the first subtitle stream (you can adjust this if there are multiple)
            subtitle_stream_index = subtitle_streams[0]['index']

            # Extract the subtitle track using ffmpeg
            ffmpeg.input(input_file).output(output_file, map='0:' + str(subtitle_stream_index)).run()

            print(f"Subtitle file extracted: {output_file}")
        else:
            print("No subtitle tracks found in the video.")

    def extract_minute_second_gps_from_global_time(self, srt_file):
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

    def find_closest_row(self, df, target_minute_second, target_gps):

        def extract_minute_second(datetime_str):
            _, time_part = datetime_str.split()
            hour, minute, second = map(int, time_part.split(':'))
            return minute, second

        # Filter rows by the target minute and second
        filtered_df = df[df['datetime(utc)'].apply(lambda x: extract_minute_second(x) == target_minute_second)]

        if filtered_df.empty:
            raise ValueError(f"No matching rows found for minute and second: {target_minute_second}")

        # Compare GPS values to find the closest row
        closest_row_index = None
        min_distance = float('inf')

        for idx, row in filtered_df.iterrows():
            row_gps = (row['latitude'], row['longitude'])  # Assuming 'latitude' and 'longitude' columns exist
            distance = geodesic(target_gps, row_gps).meters
            if distance < min_distance:
                min_distance = distance
                closest_row_index = idx

        return closest_row_index
    def update_is_video_column(self, df, start_minute_second, end_minute_second, start_gps, end_gps):
        # Find the closest rows for start and end times' GPS values
        start_row = self.find_closest_row(df, start_minute_second, start_gps)
        end_row = self.find_closest_row(df, end_minute_second, end_gps)

        # Update the 'isVideo' column in the interval
        df.loc[start_row:end_row, 'isVideo'] = 1

        return df

    def start_classification(self):


        


        data_path = os.path.join(working_directory, "videos")
        label2id = {'not_working': 0, 'working': 1}
        id2label = {0: 'not_working', 1: 'working'}
        model_ckpt = os.path.join(working_directory, "videomae_weights")
        paper_image = np.ones((self.map_height, self.map_width, 3), dtype=np.uint8)*255

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
        print(os.path.join(working_directory, "videos"))
        dataset = pytorchvideo.data.Ucf101(
                    data_path=os.path.join(working_directory, "videos"),
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
                x_pixel, y_pixel = self.convert_to_pixel(
            longitude, latitude, self.left, self.right, self.top, self.bottom)
                if predicted_label == "working":
                    paper_image = self.draw(paper_image, (x_pixel, y_pixel), (0, 255, 0), 4)
                else:
                    paper_image = self.draw(paper_image, (x_pixel, y_pixel), (0, 0, 255), 4)
                
            
        with open('output.json', 'w') as f:
            json.dump(data, f)
        cv2.imwrite("paper_image.png", paper_image)
            

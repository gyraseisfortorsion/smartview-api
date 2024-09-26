# Import the required modules
import cv2
from ultralytics import YOLO
import os
import json
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
from geopy.distance import geodesic
import glob
from PIL import Image
import ffmpeg
from datetime import datetime, timedelta
import httpx
import requests
class Detector:
	
	def __init__(self, csv_path, video_path, srt_path):
		self.video_paths = video_path               # should be a list of video names with no .mp4
		self.srt_path = srt_path
		# srt_path = video_path + ".SRT"
		# if not os.path.exists(srt_path):
		# 	self.extract_srt(video_path, video_path)
		log_date_range = self.extract_timestamps()
		print("log_date_range", log_date_range)
		self.csv_file = self.get_logs(log_date_range[0], log_date_range[1])
		print("csv_file", self.csv_file)
		observations = pd.read_csv(self.csv_file)
		# observations = observations[observations['isVideo'] == 1]

		# if (observations['isVideo'] == 1).any() == False:
		# 	print("test")
		# 	# video_path = r"MAX_0004.MP4"
		# 	# srt_path = video_path + ".SRT"

		# 	first_time_tuple, last_time_tuple, first_gps, second_gps = self.extract_minute_second_gps_from_global_time(self.srt_path)

		# 	observations = self.update_is_video_column(observations, first_time_tuple, last_time_tuple, first_gps, second_gps)
		# 	observations.to_csv("test.csv", index=False)

		# print(observations['time(millisecond)'])
		# return None

		observations = observations[observations['isVideo'] == 1]
		observations['time(millisecond)'] -= list(observations['time(millisecond)'])[0] # to start from 0

		values = [ "time(millisecond)", "latitude", "longitude", " compass_heading(degrees)", "gimbal_heading(degrees)", "ascent(feet)", 'datetime(utc)']
		self.observations = observations.loc[:, values]
		self.timestamps = list(observations["time(millisecond)"])
		self.latitudes = list(observations["latitude"])
		self.longitudes = list(observations["longitude"])
		self.compass_bearings = list(observations[" compass_heading(degrees)"])
		self.altidutes = list(observations["ascent(feet)"])
		self.datetime_logs = list(observations["datetime(utc)"])

		# print(observations['time(millisecond)'])
		# return None

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

	# Utility functions
	def visualise_path(self, df):
		# Extract Latitude and Longitude columns
		latitude = df['latitude']
		longitude = df['longitude']
		# Create a scatter plot of the drone path
		plt.figure(figsize=(12, 8))
		plt.scatter(longitude, latitude, c='blue', marker='o', s=10, label='Drone Path')
		plt.xlabel('Longitude')
		plt.ylabel('Latitude')
		plt.title('Drone Path Visualization')
		plt.legend()
		plt.grid(True)
		plt.show()

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
	
	def extract_timestamps(self):
		# srt_text =  self.video_path + ".SRT"

		srt_text = self.srt_path
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
			time_range = (timestamp - timedelta(minutes=4), timestamp + timedelta(minutes=1))

			# Convert the time range to strings
			time_range_str = (time_range[0].strftime("%Y-%m-%d %H:%M:%S"), time_range[1].strftime("%Y-%m-%d %H:%M:%S"))

			return time_range_str
	
	# def get_logs(self, start, end):
	# 	url = "https://api.airdata.com/flights"
	# 	auth = ('ad_2DiijUW6ecnT5ZuRib7amdMKJAwrg', '')
	# 	timeout = 10.0  # Timeout limit in seconds
	# 	with httpx.AsyncClient(timeout=timeout) as client:
	# 		response = client.get(url, auth=auth)
	# 		# print(response.json()["data"])
			
	# 		data = response.json()["data"]
			
	# 		# Convert start and end to datetime objects
	# 		start_date = datetime.strptime(start, "%Y-%m-%d %H:%M:%S")
	# 		end_date = datetime.strptime(end, "%Y-%m-%d %H:%M:%S")

	# 		# Find the first object whose 'time' is within the range
	# 		iter=0
	# 		for obj in data:
	# 			obj_time = datetime.strptime(obj["time"], "%Y-%m-%d %H:%M:%S")
	# 			# print(obj_time, start_date, end_date)
	# 			if start_date <= obj_time <= end_date:
	# 				print(obj)
	# 				csv_link = response.json()["data"][iter]["csvLink"]
	# 				file_response = client.get(csv_link)
	# 				break
	# 			iter+=1

	# 	# Define the local file path where you want to save the file
	# 	file_path = "flight_logs.csv"
	# 	# self.csv_file = file_path
	# 	# Write the content of the response to a file
	# 	with open(file_path, 'wb') as f:
	# 		f.write(file_response.content)

	# 	return file_path

	def get_logs(self, start, end):
		url = "https://api.airdata.com/flights"
		auth = ('ad_2DiijUW6ecnT5ZuRib7amdMKJAwrg', '')
		timeout = 10.0  # Timeout limit in seconds

		response = requests.get(url, auth=auth, timeout=timeout)
		data = response.json()["data"]

		# Convert start and end to datetime objects
		start_date = datetime.strptime(start, "%Y-%m-%d %H:%M:%S")
		end_date = datetime.strptime(end, "%Y-%m-%d %H:%M:%S")
		file_path = "flight_logs.csv"
		# Find the first object whose 'time' is within the range
		iter = 0
		for obj in data:
			obj_time = datetime.strptime(obj["time"], "%Y-%m-%d %H:%M:%S")
			if start_date <= obj_time <= end_date:
				print(obj)
				csv_link = response.json()["data"][iter]["csvLink"]
				file_response = requests.get(csv_link)
				print(file_response)
				with open(file_path, 'wb') as f:
					f.write(file_response.content)
				break
			iter += 1

		# Define the local file path where you want to save the file
		

		# Write the content of the response to a file
		

		return file_path
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

	def rhumb_destination(self, point, distance, bearing, options=None):
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
		rad_new_lon = rad_lon + (rad_dist * math.sin(rad_bearing)) / math.cos(rad_new_lat)

		# Convert back to degrees
		new_lat = math.degrees(rad_new_lat)
		new_lon = math.degrees(rad_new_lon)

		# Return the new point
		return new_lon, new_lat


	# Function to convert detections' coordinates to GPS coordinates
	def convert_to_gps(self, p, videoHeight, videoWidth, diagonalDistance, center, bearing, options):
		# Change coordinate system so the center point of the video is (0, 0)
		normalized = [p[1] - videoHeight / 2, p[0] - videoWidth / 2]

		# Calculate the distance and bearing of the solar panel relative to the center point
		distanceFromCenterInPixels = math.sqrt((videoWidth / 2 - p[0])**2 + (videoHeight / 2 - p[1])**2)
		diagonalDistanceInPixels = math.sqrt(videoWidth**2 + videoHeight**2)
		percentOfDiagonal = distanceFromCenterInPixels / diagonalDistanceInPixels
		distance = percentOfDiagonal * diagonalDistance  # in meters

		# Calculate the angle
		angle = math.atan(normalized[0] / (normalized[1] or 0.000001)) * 180 / math.pi

		# If the detection is in the right half of the frame, rotate it 180 degrees
		if normalized[1] >= 0:
			angle += 180

		# Use distance and bearing to get the GPS location of the panel
		point = self.rhumb_destination(center, distance, (bearing + angle) % 360, options)

		return point



	def convert_to_pixel(self, latitude, longitude, left, right, top, bottom):
		x = int((longitude - left) / (right - left) * self.map_width)
		y = self.map_height - int((latitude - bottom) / (top - bottom) * self.map_height)
		return x, y


	def find_gps_distance(self, point1, point2):
		R = 6371000

		lat1 = math.radians(point1[1])
		lon1 = math.radians(point1[0])

		lat2 = math.radians(point2[1])
		lon2 = math.radians(point2[0])

		dlon = lon2 - lon1
		dlat = lat2 - lat1

		a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
		c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

		distance = R * c

		return distance


	def draw(self, image, point, color, size):
		cv2.circle(image, (image.shape[1]-int(point[0]), int(point[1])), size, color, -1)
		return image


	def make_average(self, latitude, longitude, gps_points, name, datetime_log):
		found = 0
		for i, points in enumerate(gps_points):
			for j, point in enumerate(points):
				distance = self.find_gps_distance((latitude, longitude), (point[0][0], point[0][1]))
				# print("Distance", distance)
				if distance < 3.0:
					# print(f"Distance: {dis}")
					gps_points[i].append(((latitude, longitude), name, datetime_log))
					found = 1
					break

		if found == 0:
			points = []
			points.append(((latitude, longitude), name, datetime_log))
			gps_points.append(points)

		return gps_points, name

	def start_detection(self):
		# Load the CSV file into a Pandas DataFrame
		# csv_file = '0080.csv'  # Replace with the path to your CSV file

		folder = "videos/dataset/crops/"

		try:
			os.mkdir(folder)
			print("Directory created successfully!")
		except FileExistsError:
			print("Directory already exists.")
		except OSError as e:
			print(f"Error creating directory: {e}")
		
		unique_index = 0
		# Assuming you have an 800x800 pixel map

		fov =  54/2* np.pi / 180   # Drone camera field of view in radians
		fov_tan = np.tan(fov)  # Multiply by altitude to get distance across the video's diagonal

		videoHeight = 1080
		videoWidth = 1920

		final_image = np.ones((self.map_height, self.map_width, 3), dtype=np.uint8)*255
		gps_points = []

		# Initialize video capture
		model = YOLO('best.pt')

		# video_paths = [] # List that stores names of the videos  ex. ["DJI_0080", "DJI_0081"]

		# video_path = "DJI_0080.MP4"
		# cap = cv2.VideoCapture(self.video_path)

		# Get the frames per second (fps) of the video
		# fps = cap.get(cv2.CAP_PROP_FPS)
		# Calculate the frame interval in frames
		# frame_interval = round(fps * 0.2)  # 0.2 seconds (200 milliseconds)
		# change = 0
		counter = 0
		# mistake_counter =0
		# cumulative_time_difference = 0
		# current_frame_number = 0


		previous_timestamp = self.timestamps[0] - (self.timestamps[1] - self.timestamps[0])
		previous_video_time = 0
		i = 0

		for video_path in self.video_paths:

			cap = cv2.VideoCapture(video_path)

			while cap.isOpened() and i < len(self.timestamps):

				# time_difference = self.timestamps[i] - previous_timestamp
				# frame_difference = round(time_difference / 1000 * fps)
				# target_frame_number = current_frame_number + frame_difference

				# while current_frame_number < target_frame_number and cap.isOpened():
				# 	success, frame = cap.read()
				# 	if not success:
				# 		break
				# 	current_frame_number += 1

				# if not success:
				# 	break
				success, frame = cap.read()

				if not success:
					break

				current_time_ms = cap.get(cv2.CAP_PROP_POS_MSEC) + previous_video_time
				time_difference = abs(current_time_ms-self.timestamps[i])
				# print("time difference: ", time_difference)

				# print(f"{current_time_ms=} {self.timestamps[i]=}")
				if time_difference < 5 or current_time_ms >= self.timestamps[i]:
					i += 1

				if cv2.waitKey(1) & 0xFF == ord('q'):
					break

				datetime_log = self.datetime_logs[i]

				center = (self.longitudes[i], self.latitudes[i])
				x_cord, y_cord = self.convert_to_pixel(float(center[0]), float(center[1]),
										self.left, self.right, self.top, self.bottom)
				altidute = self.altidutes[i] * 0.3048

				diagonal_distance = altidute * fov_tan
				distance = diagonal_distance / 2

				if (self.compass_bearings[i] != 0):
					bearing = (self.compass_bearings[i]- 90) % 360

				# offset = math.atan(videoHeight/videoWidth) * 180 / math.pi

				# Calculate the destination points
				# top_left = self.rhumb_destination(center, distance, (bearing + offset + 180) % 360 - 180, {'units': 'meters'})
				# top_left_x, top_left_y = self.convert_to_pixel(float(top_left[0]), float(top_left[1]), self.left, self.right, self.top, self.bottom)

				# top_right = self.rhumb_destination(center, distance, (bearing - offset) % 360 - 180, {'units': 'meters'})
				# top_right_x, top_right_y = self.convert_to_pixel(float(top_right[0]), float(top_right[1]), self.left, self.right, self.top, self.bottom)

				# bottom_left = self.rhumb_destination(center, distance, (bearing - offset + 180) % 360 - 180, {'units': 'meters'})
				# bottom_left_x, bottom_left_y = self.convert_to_pixel(float(bottom_left[0]), float(bottom_left[1]), self.left, self.right, self.top, self.bottom)

				# bottom_right = self.rhumb_destination(center, distance, (bearing + offset) % 360 - 180, {'units': 'meters'})
				# bottom_right_x, bottom_right_y = self.convert_to_pixel(float(bottom_right[0]), float(bottom_right[1]), self.left, self.right, self.top, self.bottom)

				results = model.predict(frame, save=False, imgsz=640, conf=0.45, verbose=True, stream=True, half=True, device='cuda')

				detections = None

				for result in results:
					if not result:
						continue
					boxes = result.boxes
					xywh = boxes.xywh.cpu().numpy()
					detections = xywh
					for xywh_c in xywh:
						x, y, w, h = xywh_c

						# frame = cv2.circle(frame, (int(x), int(y)), 5, (255, 0, 0), 10)

				show_frame = cv2.resize(frame, (800, 600))
				# cv2.imshow('YOLOv8 Inference', show_frame)

				if detections is not None:
					counter+=1

					for detection in detections:
						unique_index += 1
						x_det, y_det, _, _ = detection

						x_gps, y_gps = self.convert_to_gps((x_det, y_det), videoHeight, videoWidth,
											diagonal_distance, center, bearing, {'units': 'meters'})

						x_plot, y_plot = self.convert_to_pixel(float(x_gps), float(y_gps), self.left, self.right,
												self.top, self.bottom)

						final_image = self.draw(final_image, (x_plot, y_plot),(255, 255, 0), 2)


						crop_size = 250
						x_det, y_det, crop_size = int(x_det), int(y_det), int(crop_size)

						cropped_image = frame[max(0, int(y_det-250)):min(int(y_det+250), frame.shape[0]),
										max(0, int(x_det-250)):min(int(x_det+250), frame.shape[1])]

						if (cropped_image.shape[0]>=500 and cropped_image.shape[1]>=500):

							# cv2.imshow("Cropped image:", cropped_image)

							image = np.uint8(cropped_image)
							image_path = folder+f"{x_gps}_{y_gps}_{unique_index}.jpg"
							cv2.imwrite(image_path, image)

							if len(gps_points) == 0:
								# print("No detection")
								points = []
								points.append(((x_gps, y_gps), image_path))
								gps_points.append(points)
							else:
								gps_points, image = self.make_average(x_gps, y_gps, gps_points, image_path, datetime_log)


				final_image = self.draw(final_image, (x_cord, y_cord),(0, 0, 255), 2)
				# cv2.imshow("GPS by Pixel", final_image)

				previous_timestamp = self.timestamps[i]
			cap.release()
			previous_video_time = current_time_ms 
				# i += 1


		def ensure_16_frames(video_frames):
			num_frames = len(video_frames)
			if num_frames < 16:
				repeat_factor = 16 // num_frames  # How many times to repeat the whole sequence
				additional_frames_needed = 16 % num_frames  # Additional frames needed to reach 16
				repeated_sequence = video_frames * repeat_factor  # Repeat the sequence to fill most of the gap
				# Add additional frames evenly from the original sequence
				additional_frames = [video_frames[i * len(video_frames) // additional_frames_needed] for i in range(additional_frames_needed)]
				video_frames = repeated_sequence + additional_frames
			elif num_frames > 16:
				# # If more than 16 frames, select 16 evenly spaced frames from the list
				# frame_indices = np.linspace(0, num_frames - 1, 16, dtype=int)
				# video_frames = [video_frames[index] for index in frame_indices]
				pass
			return video_frames

		def verify_video_frames(video_path):
			cap = cv2.VideoCapture(video_path)
			frame_count = 0
			while cap.isOpened():
				ret, _ = cap.read()
				if not ret:
					break
				frame_count += 1
			cap.release()
			return frame_count == 16


		with open('logs.csv', 'w', newline='') as file:
			writer = csv.writer(file)
			writer.writerow(["file_name", "longitude", "latitude", "timestamp"])

			for i, group in enumerate(gps_points):
				video_frames = [point[1] for point in group]
				video_frames = ensure_16_frames(video_frames)

				video_result = cv2.VideoWriter(f'videos/dataset/wobbler_{i}.avi', cv2.VideoWriter_fourcc(*'MJPG'), 30, (500, 500))
				for frame_path in video_frames:
					frame = cv2.imread(frame_path)
					frame = np.uint8(frame)

					video_result.write(frame)
				video_result.release()

				x_gps, y_gps = zip(*[point[0] for point in group])
				datetime_log = group[-1][-1]

				print("Log at", datetime_log)  

				avg_x_gps = sum(x_gps) / len(x_gps)
				avg_y_gps = sum(y_gps) / len(y_gps)

				x_pixel, y_pixel = self.convert_to_pixel(avg_x_gps, avg_y_gps, self.left, self.right, self.top, self.bottom)

				final_image = self.draw(final_image, (x_pixel, y_pixel), (0, 0, 0), 2)
				cv2.putText(final_image, f"w_{i}", (int(final_image.shape[1]-x_pixel), y_pixel), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 0, 0), 1)

				writer.writerow([f'wobbler_{i}.avi', avg_x_gps, avg_y_gps, datetime_log])

				# After saving the video, verify the number of frames
				video_path = f'videos/dataset/wobbler_{i}.avi'  # Use the path to the saved video
				if verify_video_frames(video_path):
					print(f"Video {video_path} verified with exactly 16 frames.")
				else:
					print(f"Error: Video {video_path} does not have 16 frames.")


		# cv2.imshow("GPS by Pixel", final_image)
		cv2.imwrite("full_map.png", final_image)
		# cv2.waitKey(0)

		cap.release()
		cv2.destroyAllWindows()
		return 1

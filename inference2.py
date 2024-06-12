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
# import streamlit as st
from torchvision.transforms import Compose


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

data_path = os.path.join(working_directory, "videos")
label2id = {'not_working': 0, 'working': 1, 'working_not_spinning': 2}
id2label = {0: 'not_working', 1: 'working', 2: 'working_not_spinning'}
model_ckpt = os.path.join(working_directory, "model_ckpt")
print(data_path)
# model_ckpt = "insert path"


image_processor = VideoMAEImageProcessor.from_pretrained(model_ckpt)
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



from pytorchvideo.data import Ucf101, make_clip_sampler

data_path = os.path.join(working_directory, "videos")
clip_duration = 2.0  # Duration of each clip in seconds

# Example of defining a uniform clip sampler (this is hypothetical and for illustrative purposes)
clip_sampler = make_clip_sampler("uniform", clip_duration)


dataset = Ucf101(
    data_path=data_path,
    clip_sampler=clip_sampler,
    decode_audio=False,
    transform=transform,
)

# dataset = pytorchvideo.data.Ucf101(
#     data_path=os.path.join(working_directory, "videos"),
#     clip_sampler=pytorchvideo.data.make_clip_sampler("random", clip_duration),
#     decode_audio=False,
#     transform=transform,
# )


for video in iter(dataset):
    logits = run_inference(modelMAE, video["video"])
    name = video['video_name']
    print(name, modelMAE.config.id2label[logits.argmax(-1).item()])
    predicted_label = modelMAE.config.id2label[logits.argmax(-1).item()]

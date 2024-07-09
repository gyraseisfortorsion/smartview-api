from detector import Detector as Detector
from classificator import Detector as Classificator

import time


video_path = r'DJI_0031.MP4'
srt_path = r'DJI_0031.SRT'

det = Detector(
	'',
        video_path,
        srt_path
    )

#det.start_detection()

clsf = Classificator(
	video_path,
        srt_path
    )
clsf.start_classification()



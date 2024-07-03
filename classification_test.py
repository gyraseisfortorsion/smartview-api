from detector import Detector as Detector
from classificator import Detector as Classificator

import time


def main():
    
    video_path = r'c:\Users\fano2\Downloads\DJI_0028.MP4'
    srt_path = r'c:\Users\fano2\Downloads\DJI_0028.SRT'

    det = Detector(
        video_path,
        srt_path
    )

    det.start_detection()

    clsf = Classificator(
        video_path,
        srt_path
    )

    clsf.start_classification()


if __name__ == "__main__":
    begin_time = time.time()
    main()
    print("Total time: ", time.time()-begin_time)

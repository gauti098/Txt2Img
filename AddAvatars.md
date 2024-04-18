1) At First Create AvatarImage in Django Model
2) Add init_frame.png and source.png in (private_data/avatars/{id}/first_order/)
3) Add video.mp4 in (private_data/avatars/{id}/wav2lip/)
4) Add After Effect Tracking data (private_data/avatars/{id}/fullbody/position.csv) and image (private_data/avatars/{id}/fullbody/without_swap/)
5) Add postion and scale and total frame (came from after effect) in AvatarImage database
6) Add Avatar Images and Sound Combinations.
7) Create mask.mp4 from mask sequence and put inside fullbody/mask.mp4
'''
import cv2
import os
import imageio

writer = imageio.get_writer('mask.mp4', fps=30)

allFiles = os.listdir('mask/')
allFiles.sort()

for ii in allFiles:
        img = cv2.imread('mask/'+ii,-1)
        writer.append_data(img[:,:,3])

writer.close()
'''
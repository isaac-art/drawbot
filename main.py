
import os
import cv2
import uuid
import time
import random
import requests
import subprocess
from datetime import datetime
from typing import Tuple, List, Union

from path_sender import PathSender
from image_2_paths import I2P
from robot import Robot
from utils import visualize_paths

from portrait_2_line_art import main as p2la

def get_box_bounds(box_x: int, box_y: int, box_size:int) -> Tuple[int, int, int, int]:
    """Convert grid coordinates to workspace bounds"""
    min_x = 1 + (box_x * box_size)
    max_x = min_x + box_size
    min_y = 1 + (box_y * box_size) 
    max_y = min_y + box_size
    return (min_x, max_x, min_y, max_y)

def get_random_unused_box(grid_size, box_size, drawn_boxes) -> Union[Tuple[int, int, int, int], None]:
    """Get bounds of random undrawn box, or None if all used"""
    available = []
    for x in range(grid_size):
        for y in range(grid_size):
            if (x,y) not in drawn_boxes:
                available.append((x,y))
    if not available: return None
    box_x, box_y = random.choice(available)
    drawn_boxes.add((box_x, box_y))
    return drawn_boxes, get_box_bounds(box_x, box_y, box_size)

def capture_and_process_image(bot, server_live) -> Tuple[bool, Union[Tuple[str, str, str], str]]:
    print("Opening camera...")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return False, "Error: Could not open camera"

    # Wait for camera to initialize
    time.sleep(1)

    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    face_detected = False
    face_detected_start_time = None
    required_face_time = 2  # seconds

    while not face_detected:
        ret, frame = cap.read()
        if not ret: continue

        # Resize frame for faster processing
        height, width = frame.shape[:2]
        scale_factor = 0.5
        # new_width = int(width * scale_factor)
        # new_height = int(height * scale_factor)
        # frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)

        # Detect faces
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)

        if len(faces) > 0:
            # Find largest face by area
            largest_face = max(faces, key=lambda face: face[2] * face[3])
            x, y, w, h = largest_face

            # Only start timer if face is large enough
            if w > 145 and h > 145:
                if face_detected_start_time is None:
                    face_detected_start_time = time.time()
                    print("Face detected! Hold still...")
                
                elapsed_time = time.time() - face_detected_start_time
                if elapsed_time >= required_face_time:
                    face_detected = True
                    print("Face held for 6 seconds - capturing image!")
                else:
                    print(f"Hold still for {required_face_time - elapsed_time:.1f} more seconds...")
            else:
                if face_detected_start_time is not None:
                    print("Face too small - resetting timer...")
                    face_detected_start_time = None
                else:
                    print("Face too small, please move closer...")
        

            # Add padding around face
            padding = 150
            x = max(0, x - padding)
            y = max(0, y - padding)
            w = min(frame.shape[1] - x, w + 2*padding)
            h = min(frame.shape[0] - y, h + 2*padding)

            # Crop image to face area
            frame = frame[y:y+h, x:x+w]
        else:
            if face_detected_start_time is not None:
                print("Face lost - resetting timer...")
                face_detected_start_time = None
            else:
                print("No face detected, retrying...", end="\r")
            time.sleep(0.1)
        # cv2.imshow('faces', frame)
        # cv2.waitKey(1)
    cv2.destroyAllWindows()
    cap.release()
    # exit()
    bot.servo_p_sync(0,0,-30,0,0,0)
    try:

        _, img_encoded = cv2.imencode('.jpg', frame)
        image_uuid = datetime.now().strftime("%Y%m%d_%H%M%S")
        o_filename = f"images/original_{image_uuid}.jpg"
        
        with open(o_filename, 'wb') as f:
            f.write(img_encoded.tobytes())

        # SEND TO RUNPOD FOR PROCESSING
        # subprocess.run(["python", "portrait-2-line-art.py", "--ip", "213.173.109.234", "--port", "17778", "--filepath", "linear-api.json", "--xf", o_filename])
        if server_live: res_filename = p2la(ip="213.173.110.141", port=16457, filepath="linear-api.json", image_path=o_filename)
        else: res_filename = o_filename

        return True, (image_uuid, o_filename, res_filename)
    except Exception as e:
        return False, e



if __name__ == "__main__":
    try:
        total_workspace = (1,400, 1,400) #minx,maxx, miny, maxy
        box_size = 400
        grid_size = 1
        drawn_boxes = set() 
        # (579, 153, -533, 97, -53, 178)
        is_running = True

        bot_live = True
        server_live = True
        vis = False

        if bot_live:
            bot = Robot()
            bot.clear_error()
            bot.enable_robot()
            bot.set_speed_factor(bot.speed)
            bot.set_user(6)

        while is_running:
            # GO TO CAMERA POSITION
            # if bot_live: bot.servo_p_sync(579, 153, -533, 97, -53, 178)

            drawn_boxes, work_area = get_random_unused_box(grid_size, box_size, drawn_boxes)
            print(f"Drawn in {len(drawn_boxes)} slots")
            print(f"Work Area ", work_area)
            
            
            res, data = capture_and_process_image(bot, server_live)

            if bot_live: bot.servo_p_sync(0,0,-30,0,0,0)

            if not res: 
                print(data)
                continue
            else:
                iuuid, original, result = data

                # result = "/Users/isaac/Desktop/drawbot/output/ComfyUI_00052_.png"

                i2p = I2P(image_path=result, drawing_area=(0,360,0,500))

                if vis: visualize_paths([i2p.reduced_paths])

                paths = sorted(i2p.reduced_paths, key=len, reverse=True)

                if bot_live:
                    res, msg = bot.process_paths(paths)
                    if not res: is_running = False
                    
                # GO TO CAMERA POSITION
                # if bot_live: bot.servo_p_sync(579, 153, -533, 97, -53, 178)
                # time.sleep(60) 
                # Wait for spacebar press to continue
                # key = input("Press spacebar to continue...")
                # while key != " ":
                #     key = input("Press spacebar to continue...")


    except Exception as e:
        print("MAIN LOOP ERR", e)

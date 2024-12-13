import os
import time
import cv2 as cv
import numpy as np
from skimage.morphology import skeletonize

from path_processor import PathProcessor


class I2P:
    def __init__(self, image_path="images/dog2.png", drawing_area=(1, 400, 1, 400),log=True):
        self.image_path = image_path
        self.log = log

        image = cv.imread(image_path, cv.IMREAD_GRAYSCALE)
        blurred = cv.GaussianBlur(image, (3, 3), 0)
        # cv.imshow('grey', blurred)
        # cv.waitKey()

        _, binary = cv.threshold(blurred, 125, 255, cv.THRESH_BINARY_INV)
        
        # kernel = np.ones((3,3), np.uint8)
        # binary = cv.morphologyEx(binary, cv.MORPH_OPEN, kernel)
        
        # cv.imshow('binary', binary)
        # cv.waitKey()
        

        # binary_normalized = binary / 255
        # binary_image = binary_normalized > 0
        skeleton = skeletonize(binary)
        skeleton_image = (skeleton * 255).astype(np.uint8)
        # cv.imshow('skeleton', skeleton_image)
        # cv.waitKey()

        contours, _ = cv.findContours(
            skeleton_image, 
            cv.RETR_LIST,
            cv.CHAIN_APPROX_SIMPLE
        )
        paths = []
        for contour in contours:
            # Convert each contour to a list of [x,y] coordinates
            path = contour.squeeze().tolist()
            # Handle single points or lines
            if isinstance(path[0], (int, float)):
                path = [path]
            print(len(path))
            paths.append(path)
        # # [[[639, 714], ..., [534, 119]]]
        # Get image dimensions
        image_height, image_width = image.shape[:2]

        pp = PathProcessor(
            paths, 
            drawing_area, 
            image_dimensions=(image_width, image_height),
            z_height_pen_down=0.65, 
            z_height_pen_up=-20, 
            distance_mm=3.0
        )
        self.original_paths, self.reduced_paths = pp.process_paths()

        # Filter out paths with length less than XX
        self.reduced_paths = [path for path in self.reduced_paths if len(path) >= 4]

        if self.log:
            print(f"Original Path Count: {len(self.original_paths)}")
            print(f"Reduced Path Count: {len(self.reduced_paths)}")
            original_points = sum(len(path) for path in self.original_paths)
            reduced_points = sum(len(path) for path in self.reduced_paths)

            print(f"Original paths total points: {original_points}")
            print(f"Reduced paths total points: {reduced_points}")
            print(f"Points reduction: {(original_points - reduced_points) / original_points * 100:.1f}%")

            print(f"Original paths type: {type(self.original_paths)}")
            print(f"Original paths[0] type: {type(self.original_paths[0])}")
            print(f"Original paths[0][0] type: {type(self.original_paths[0][0])}")
            print(f"Reduced paths type: {type(self.reduced_paths)}")
            print(f"Reduced paths[0] type: {type(self.reduced_paths[0])}")
            print(f"Reduced paths[0][0] type: {type(self.reduced_paths[0][0])}")

    

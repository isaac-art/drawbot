from typing import List, Tuple
from math import sqrt

class PathProcessor:
    def __init__(self, paths: List[List[List[float]]], robot_bounds: Tuple[float, float, float, float],
                 image_dimensions: Tuple[int, int],
                 z_height_pen_down: float = 22, z_height_pen_up: float = 10,
                 distance_mm: float = 1.0):
        self.paths = paths
        self.robot_bounds = robot_bounds
        self.image_width, self.image_height = image_dimensions
        self.z_height_pen_down = z_height_pen_down
        self.z_height_pen_up = z_height_pen_up
        self.distance_mm = distance_mm

    def map_to_robot_coords(self, points: List[List[float]], min_x: float, max_x: float, 
                       min_y: float, max_y: float) -> List[dict]:
        """Map points to robot coordinate system while preserving aspect ratio"""
        x_min, x_max, y_min, y_max = self.robot_bounds
        
        # Calculate available robot drawing area
        robot_width = x_max - x_min
        robot_height = y_max - y_min
        
        # Print debugging information
        print(f"\nMapping Diagnostics:")
        print(f"Image dimensions: {self.image_width}x{self.image_height}")
        print(f"Image aspect ratio: {self.image_width / self.image_height:.3f}")
        print(f"Robot bounds: {self.robot_bounds}")
        print(f"Robot drawing area: {robot_width}x{robot_height}")
        print(f"Robot aspect ratio: {robot_width / robot_height:.3f}")
        print(f"Input bounds: X({min_x:.1f}, {max_x:.1f}), Y({min_y:.1f}, {max_y:.1f})")
        print(f"Input aspect ratio: {(max_x - min_x) / (max_y - min_y):.3f}")
        
        # Calculate scaling factors
        input_width = max_x - min_x
        input_height = max_y - min_y
        input_aspect = input_width / input_height
        robot_aspect = robot_width / robot_height
        
        # Scale to fit while preserving aspect ratio
        if input_aspect > robot_aspect:
            # Width limited
            scale = robot_width / input_width
            scaled_height = input_height * scale
            y_offset = (robot_height - scaled_height) / 2
            
            print(f"\nWidth limited scaling:")
            print(f"Scale factor: {scale:.3f}")
            print(f"Scaled dimensions: {robot_width}x{scaled_height}")
            print(f"Y offset: {y_offset}")
            
            robot_points = []
            for x, y in points:
                x_robot = x_min + (x - min_x) * scale
                y_robot = y_min + y_offset + (y - min_y) * scale
                
                # Clamp values to bounds
                x_robot = max(x_min, min(x_max, x_robot))
                y_robot = max(y_min, min(y_max, y_robot))
                
                point = {
                    "x": float(x_robot),
                    "y": float(y_robot),
                    "z": float(self.z_height_pen_down),
                    "rx": 0.0,
                    "ry": 0.0,
                    "rz": 0.0
                }
                robot_points.append(point)
        else:
            # Height limited
            scale = robot_height / input_height
            scaled_width = input_width * scale
            x_offset = (robot_width - scaled_width) / 2
            
            print(f"\nHeight limited scaling:")
            print(f"Scale factor: {scale:.3f}")
            print(f"Scaled dimensions: {scaled_width}x{robot_height}")
            print(f"X offset: {x_offset}")
            
            robot_points = []
            for x, y in points:
                x_robot = x_min + x_offset + (x - min_x) * scale
                y_robot = y_min + (y - min_y) * scale
                
                # Clamp values to bounds
                x_robot = max(x_min, min(x_max, x_robot))
                y_robot = max(y_min, min(y_max, y_robot))
                
                point = {
                    "x": float(x_robot),
                    "y": float(y_robot),
                    "z": float(self.z_height_pen_down),
                    "rx": 0.0,
                    "ry": 0.0,
                    "rz": 0.0
                }
                robot_points.append(point)

        # Add pen up/down points
        if robot_points:
            start_point = robot_points[0].copy()
            start_point["z"] = self.z_height_pen_up
            
            end_point = robot_points[-1].copy()
            end_point["z"] = self.z_height_pen_up
            
            robot_points.insert(0, start_point)
            robot_points.append(end_point)

        return robot_points

    def uniform_resample(self, points: List[dict], num_points: int) -> List[dict]:
        """Resample points uniformly along the path"""
        if len(points) < 2:
            return points

        xy_points = [(p["x"], p["y"]) for p in points]

        path_length = 0
        for i in range(len(xy_points)-1):
            p1, p2 = xy_points[i], xy_points[i+1]
            path_length += sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)

        segment_length = path_length / (num_points - 1)

        resampled = [points[0]]
        current_dist = 0
        point_index = 0

        for i in range(1, num_points-1):
            target_dist = i * segment_length

            while current_dist < target_dist and point_index < len(xy_points)-1:
                p1, p2 = xy_points[point_index], xy_points[point_index+1]
                segment_dist = sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)

                if current_dist + segment_dist > target_dist:
                    ratio = (target_dist - current_dist) / segment_dist
                    x = p1[0] + ratio * (p2[0] - p1[0])
                    y = p1[1] + ratio * (p2[1] - p1[1])

                    new_point = {
                        "x": float(x),
                        "y": float(y),
                        "z": points[point_index]["z"],
                        "rx": 0.0,
                        "ry": 0.0,
                        "rz": 0.0
                    }
                    resampled.append(new_point)
                    break

                current_dist += segment_dist
                point_index += 1

        resampled.append(points[-1])
        return resampled

    def resample_points(self, points: List[dict]) -> List[dict]:
        if not points:
            return []

        drawing_points = points[1:-1]

        path_length = 0
        xy_points = [(p["x"], p["y"]) for p in drawing_points]
        for i in range(len(xy_points)-1):
            p1, p2 = xy_points[i], xy_points[i+1]
            path_length += sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
        num_points = max(2, int(path_length / self.distance_mm))

        resampled = self.uniform_resample(drawing_points, num_points)

        return [points[0]] + resampled + [points[-1]]

    def process_paths(self) -> Tuple[List[List[List[float]]], List[List[dict]]]:
        all_paths = []
        original_paths = []

        # Find min and max x, y values across all paths
        min_x = min(min(x for x, _ in path) for path in self.paths)
        max_x = max(max(x for x, _ in path) for path in self.paths)
        min_y = min(min(y for _, y in path) for path in self.paths)
        max_y = max(max(y for _, y in path) for path in self.paths)

        for path in self.paths:
            robot_points = self.map_to_robot_coords(path, min_x, max_x, min_y, max_y)
            reduced_path = self.resample_points(robot_points)
            all_paths.append(reduced_path)
            original_paths.append(robot_points)

        return original_paths, all_paths
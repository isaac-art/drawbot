import zmq
import time
import socket
from typing import Tuple, Union, List
import keyboard

class Robot:
    def __init__(self, log: bool = True):
        self.log = True
        if self.log: print("Initializing Robot")
        self.ip = '192.168.1.6'
        # self.ip = 'dobot.local'
        self.user = 6
        self.speed = 40
        self.main_port = 29999
        self.feedback_port = 30004
        res, self.connection = self.setup_connection(self.ip, self.main_port)
        res, self.feedback_connection = self.setup_connection(self.ip, self.feedback_port)
        self.running = False

    def __del__(self):
        self.close_connections()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.close_connection()

    def send_message(self, message: str) -> Tuple[bool, Union[str, Exception]]:
        try:
            # if self.log: print("Sending:", message)
            self.connection.send(message.encode())
            data = self.connection.recv(1440)
            # if self.log: print("    Response:", data)
            return True, data
        except Exception as e:
            return False, e
        
    def setup_zmq(self) -> Tuple[bool, Union[Tuple[zmq.Context, zmq.Socket], Exception]]:
        try:
            context = zmq.Context()
            socket = context.socket(zmq.SUB)
            socket.connect("tcp://localhost:5555") 
            socket.setsockopt_string(zmq.SUBSCRIBE, "")
            time.sleep(0.5)
            return True, (context, socket)
        except Exception as e:
            return False, e

    def setup_connection(self, ip: str, port: int) -> Tuple[bool, Union[socket.socket, Exception]]:
        try:
            if self.log: print(f"Attempting to connect to {ip}:{port}")
            con = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            con.connect((ip, port))
            if self.log: print(f"Connected to {ip}:{port}")
            return True, con
        except Exception as e:
            print(e)
            return False, e

    def close_connections(self) -> Tuple[bool, Union[str, Exception]]:
        try:
            if hasattr(self, 'connection'): self.connection.close()
            if hasattr(self, 'feedback_connection'): self.feedback_connection.close()
            if hasattr(self, 'zmq_socket'): self.zmq_socket.close()
            if hasattr(self, 'zmq_context'): self.zmq_context.term()
            if self.log: print("Connections closed")
            return True, "Connections closed"
        except Exception as e:
            return False, e
        
    def process_paths(self, paths:List[List[dict]]) -> Tuple[bool, Union[str, Exception]]:
        try:
            # Setup initial state
            path_count = len(paths)
            total_points = sum(len(path) for path in paths)
            self.running = True
            
            # Initialize robot
            self.enable_robot()
            self.clear_error()
            self.set_speed_factor(self.speed)
            self.set_user(self.user)
            
            completed_paths = 0
            completed_points = 0
            
            for coords_list in paths:
                
                x,y,z,rx,ry,rz = coords_list[0]['x'], coords_list[0]['y'], coords_list[0]['z'], coords_list[0]['rx'], coords_list[0]['ry'], coords_list[0]['rz']
                self.servo_p_sync(x,y,z,rx,ry,rz)
                x,y,z,rx,ry,rz = coords_list[1]['x'], coords_list[1]['y'], coords_list[1]['z'], coords_list[1]['rx'], coords_list[1]['ry'], coords_list[1]['rz']
                self.servo_p_sync(x,y,z,rx,ry,rz)
                
                # Process each path
                for coords in coords_list[1:-1]:
                    # handle_keyboard()  # Check for keyboard input
                    x,y,z,rx,ry,rz = coords['x'], coords['y'], coords['z'], coords['rx'], coords['ry'], coords['rz']
                    self.servo_p(x,y,z,rx,ry,rz)
                    time.sleep(1.0/30)
                    completed_points += 1

                self.sync()
                x,y,z,rx,ry,rz = coords_list[-1]['x'], coords_list[-1]['y'], coords_list[-1]['z'], coords_list[-1]['rx'], coords_list[-1]['ry'], coords_list[-1]['rz']
                self.servo_p_sync(x,y,z,rx,ry,rz)

                completed_paths += 1
                if self.log:
                    print(f"Progress: {completed_paths/path_count*100:.1f}% complete")
            
            return True, "Done"
            
        except KeyboardInterrupt as ki:
            if self.log:
                print("\nShutting down gracefully...")
            self.running = False    
            self.close_connections()
            return False, "Shutting down gracefully"
            
        except Exception as e:
            if self.log:
                print(f"\nError occurred: {e}")
            self.running = False    
            self.close_connections()
            return False, str(e)

    def run_bot_listener(self) -> Tuple[bool, Union[str, Exception]]:
        res, zmq_tuple = self.setup_zmq()
        if not res:
            return False, zmq_tuple
        self.zmq_context, self.zmq_socket = zmq_tuple
        
        self.running = True
        self.enable_robot()
        self.clear_error()
        self.set_speed_factor(self.speed)
        self.set_user(self.user)
        
        # self.servo_p_sync(0,0,-30,0,0,0)
        try:
            while self.running:
                # Receive coordinates from ZMQ
                print("waiting for ZMQ")
                coords_list = self.zmq_socket.recv_json() #blocking
                print(f"{len(coords_list)}")
                print(f"coords_list type: {type(coords_list)}")
                print(f"coords_list[0] type: {type(coords_list[0])}")
                # MOVE TO FIRST POS AND PEN DOWN
                x,y,z,rx,ry,rz = coords_list[0]['x'], coords_list[0]['y'], coords_list[0]['z'], coords_list[0]['rx'], coords_list[0]['ry'], coords_list[0]['rz']
                self.servo_p_sync(x,y,z,rx,ry,rz)
                x,y,z,rx,ry,rz = coords_list[1]['x'], coords_list[1]['y'], coords_list[1]['z'], coords_list[1]['rx'], coords_list[1]['ry'], coords_list[1]['rz']
                self.servo_p_sync(x,y,z,rx,ry,rz)

                # LOOP OVER MAIN DRAWING AT 30hz
                for coords in coords_list[1:-1]:
                    x,y,z,rx,ry,rz = coords['x'], coords['y'], coords['z'], coords['rx'], coords['ry'], coords['rz']
                    self.servo_p(x,y,z,rx,ry,rz)
                    time.sleep(1.0/30)

                self.sync()
                # MOVE TO LAST POS AND PEN IP
                self.sync()
                x,y,z,rx,ry,rz = coords_list[-1]['x'], coords_list[-1]['y'], coords_list[-1]['z'], coords_list[-1]['rx'], coords_list[-1]['ry'], coords_list[-1]['rz']
                self.servo_p_sync(x,y,z,rx,ry,rz)
        except KeyboardInterrupt:
            if self.log: print("\nShutting down gracefully...")
            payload = True, "Shutting down gracefully"
            self.running = False    
            self.close_connections()
            return True, "ok"
        except Exception as e:
            if self.log: print(f"\nError occurred, shutting down: {e}")
            payload = False, e
            self.running = False    
            self.close_connections()
            return True, "ok"

    # ROBOT COMMANDS
    def enable_robot(self) -> Tuple[bool, Union[str, Exception]]:
        return self.send_message("EnableRobot()")

    def clear_error(self) -> Tuple[bool, Union[str, Exception]]:
        return self.send_message("ClearError()")
    
    def reset_robot(self) -> Tuple[bool, Union[str, Exception]]:
        return self.send_message("ResetRobot()")
    
    def set_speed_factor(self, speed: int) -> Tuple[bool, Union[str, Exception]]:
        return self.send_message(f"SpeedFactor({speed})")

    def set_user(self, user: int) -> Tuple[bool, Union[str, Exception]]:
        return self.send_message(f"User({user})")
    
    def get_robot_mode(self) -> Tuple[bool, Union[str, Exception]]:
        return self.send_message("RobotMode()")
    
    def mov_l(self, x: float, y: float, z: float, rx: float, ry: float, rz: float) -> Tuple[bool, Union[str, Exception]]:
        return self.send_message(f"MovL({x},{y},{z},{rx},{ry},{rz})")
    
    def mov_j(self, a: float, b: float, c: float, d: float, e: float, f: float) -> Tuple[bool, Union[str, Exception]]:
        return self.send_message(f"MovJ({a},{b},{c},{d},{e},{f})")
    
    def servo_p(self, x: float, y: float, z: float, rx: float, ry: float, rz: float) -> Tuple[bool, Union[str, Exception]]:
        return self.send_message(f"ServoP({x},{y},{z},{rx},{ry},{rz})")
    
    def sync(self) -> Tuple[bool, Union[str, Exception]]:
        return self.send_message("Sync()")

    def servo_p_sync(self, x: float, y: float, z: float, rx: float, ry: float, rz: float) -> Tuple[bool, Union[str, Exception]]:
        try:
            res, data = self.send_message(f"ServoP({x},{y},{z},{rx},{ry},{rz})")
            res, data = self.send_message("Sync()")
            return res, data
        except Exception as e:
            return False, e


if __name__ == "__main__":
    robot = Robot()
    # res, message = robot.run_bot_listener()
    # print(res, message)

    robot.clear_error()
    robot.enable_robot()
    robot.set_speed_factor(robot.speed)
    robot.set_user(robot.user)
    robot.servo_p_sync(0,0,-30,0,0,0)
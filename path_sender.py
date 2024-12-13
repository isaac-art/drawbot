import zmq
from typing import List, Tuple, Union
import time

class PathSender:
    def __init__(self, log: bool = True):
        self.log = log

        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUB)
        self.socket.bind("tcp://localhost:5555")

    def __del__(self):
        self.close_connection()

    def close_connection(self) -> Tuple[bool, Union[str, Exception]]:
        try:
            self.socket.close()
            self.context.term()
            if self.log: print("ZMQ connection closed")
            return True, "ZMQ connection closed"
        except Exception as e:
            return False, e

    def send_paths(self, paths: List[List[dict]]) -> Tuple[bool, Union[str, Exception]]:
        try:
            if self.log: print(f"Sending {len(paths)} paths")
            time.sleep(0.1)
            for path in paths:
                print("-"*120)
                print("sending:", path)
                self.socket.send_json(path)
            payload = True, "All paths sent successfully"
        except Exception as e:
            if self.log: print("send_paths exception: ", e)
            payload = False, e
        finally:
            return payload
        

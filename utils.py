import matplotlib.pyplot as plt
from typing import List

ROBOT_MODE = {
    1:	"ROBOT_MODE_INIT",
    2:	"ROBOT_MODE_BRAKE_OPEN",
    3:	"",
    4:	"ROBOT_MODE_DISABLED",
    5:	"ROBOT_MODE_ENABLE",
    6:	"ROBOT_MODE_BACKDRIVE",
    7:	"ROBOT_MODE_RUNNING",
    8:	"ROBOT_MODE_RECORDING",
    9:	"ROBOT_MODE_ERROR",
    10:	"ROBOT_MODE_PAUSE",
    11:	"ROBOT_MODE_JOG"
}


def visualize_paths(all_paths: List[List[List[dict]]], title: str = "All Paths Visualization") -> None:
    """Visualize all paths on a single plot"""
    plt.figure(figsize=(10, 10))

    colors = ['k', 'r', 'y', 'g', 'b', 'm', 'c']
    for i, paths in enumerate(all_paths):
        color = colors[i % len(colors)]
        for path in paths:
            print(path)
            x = [p["x"]+i*5  for p in path] 
            y = [p["y"]+i*5 for p in path]
            plt.plot(x, y, f'{color}-', linewidth=1)
            plt.plot(x, y, f'{color}.', markersize=2)

    plt.title(title)
    plt.xlabel('X (mm)')
    plt.ylabel('Y (mm)')
    plt.axis('equal')
    plt.grid(True)
    plt.xlim(0, 360)
    plt.ylim(500, 0)  # Reversed y-axis to put 0,0 at top left
    plt.show()

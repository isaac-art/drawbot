# Drawing on Dobot CR5 

```bash
python-m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Drawing demo
`python main.py`


### Robot
```python

import robot

robot = Robot()
robot.enable_robot()
robot.set_speed_factor(50)
robot.set_user(6) #set coordinate system
robot.servo_p_sync(0,0,-30,0,0,0)
robot.mov_l(0,0,-30,0,0,0)
```

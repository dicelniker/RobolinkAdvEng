import math

from swarm2 import *
from codrone_edu import *

class Choreography():

    def __init__(self):
        return

    def runSequence(self, swarm):
        drones = swarm.get_drone_objects()
        drone1, drone2, drone3 = drones[0], drones[1], drones[2]

        # Define spiral parameters
        radius = 0.5  # radius of circle in meters
        height = 0.5  # total height to ascend in meters
        duration = 4  # time to complete spiral in seconds
        steps = 20  # number of points in the spiral

        for i in range(steps):
            # Calculate position for this step
            t = i / (steps - 1)  # normalized time from 0 to 1

            # Parametric equations for circular spiral
            x = radius * math.cos(2 * math.pi * t)  # CCW motion
            y = radius * math.sin(2 * math.pi * t)  # CCW motion
            z = height * t  # Linear increase in height

            # Send position commands to all drones
            for drone in [drone1, drone2, drone3]:
                drone.sendControlPosition(x, y, z, 0.5, 0, 0)

            # Wait a short time between movements for smooth motion
            sleep(duration / steps)



        sleep(2)
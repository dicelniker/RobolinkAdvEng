import math

from swarm2 import *
from codrone_edu import *

class Choreography():

    def __init__(self):
        return

    def runSequence(self, swarm):
        drones = swarm.get_drone_objects()
        drone1, drone2, drone3 = drones[0], drones[1], drones[2]

        # Define spiral parameters for drones 1 and 3
        radius = 0.5  # radius of circle in meters
        height = 0.5  # total height to ascend in meters
        duration = 4  # time to complete spiral in seconds
        steps = 20  # number of points in the spiral

        # Have drone 2 hover briefly before flip
        drone2.hover(1)
        drone2.flip("front")

        # Execute spiral for drones 1 and 3
        for i in range(steps):
            # Calculate position for this step
            t = i / (steps - 1)  # normalized time from 0 to 1

            # Parametric equations for circular spiral
            x = radius * math.cos(2 * math.pi * t)  # CCW motion
            y = radius * math.sin(2 * math.pi * t)  # CCW motion
            z = height * t  # Linear increase in height

            # Send position commands to drones 1 and 3
            drone1.sendControlPosition(x, y, z, 0.5, 0, 0)
            drone3.sendControlPosition(x, y, z, 0.5, 0, 0)

            # Wait a short time between movements for smooth motion
            sleep(duration / steps)

        # Wait for flip to complete and drone to stabilize
        sleep(4)
        # meow
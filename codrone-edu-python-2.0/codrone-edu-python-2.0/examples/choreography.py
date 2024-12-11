import math

from swarm2 import *
from codrone_edu import *

class Choreography():

    def __init__(self):
        return

    def runSequence(self, swarm):
        drones = swarm.get_drone_objects()
        drone1, drone2, drone3 = drones[0], drones[1], drones[2]

        # Define movement parameters
        forward_distance = 3.0  # total forward distance in meters
        amplitude = 0.3  # how far to wiggle side to side in meters
        steps = 30  # number of points in the path
        duration = 6  # total time for movement in seconds

        for i in range(steps):
            # Calculate position for this step
            t = i / (steps - 1)  # normalized time from 0 to 1

            # Calculate positions
            x = forward_distance * t  # Move forward gradually
            y = amplitude * math.sin(4 * math.pi * t)  # Side to side wiggle (2 complete waves)
            z = 0  # Maintain constant height

            # Send position commands to all drones
            for drone in [drone1, drone2, drone3]:
                drone.sendControlPosition(x, y, z, 0.5, 0, 0)

            # Wait a short time between movements for smooth motion
            sleep(duration / steps)
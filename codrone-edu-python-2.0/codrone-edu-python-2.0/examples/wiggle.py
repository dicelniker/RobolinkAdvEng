import math

from codrone_edu.swarm import *

class Choreography():

    def __init__(self):
        return

    def runSequence(self, swarm, selected_drone_indices):
        sync = Sync()

        # Define movement parameters
        forward_distance = 2.0  # total forward distance in meters
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
            for i in selected_drone_indices:
                seq = Sequence(i)
                seq.add('sendControlPosition', x, y, z, 0.5, 0, 0)
                sync.add(seq)

            # Wait a short time between movements for smooth motion
            sleep(duration / steps)

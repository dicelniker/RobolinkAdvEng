import math

from codrone_edu.swarm import *

class Choreography():

    def __init__(self):
        return

    def runSequence(self, swarm, selected_drone_indices):
        # Define spiral parameters
        radius = 0.1  # radius of circle in meters
        height = 0.2  # total height to ascend in meters
        duration = 4  # time to complete spiral in seconds
        steps = 20  # number of points in the spiral

        sync = Sync()
        for i in range(steps):
            # Calculate position for this step
            t = i / (steps - 1)  # normalized time from 0 to 1

            # Parametric equations for circular spiral
            x = radius * math.cos(2 * math.pi * t)  # CCW motion
            y = radius * math.sin(2 * math.pi * t)  # CCW motion
            z = height * t  # Linear increase in height

            # Send position commands to all drones
            for i in selected_drone_indices:
                seq = Sequence(i)
                seq.add('sendControlPosition', x, y, z, 0.5, 0, 0)
                # Wait a short time between movements for smooth motion
                seq.add('sequence_sleep', duration/steps)
                sync.add(seq)

        swarm.run(sync)


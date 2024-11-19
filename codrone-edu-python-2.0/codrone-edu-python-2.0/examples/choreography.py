from swarm2 import *
from codrone_edu import *

class Choreography():

    def __init__(self):
        return

    def runSequence(self,swarm):

        drones = swarm.get_drone_objects()

        drone1 = drones[0]
        drone2 = drones[1]
        drone3 = drones[2]
        drone4 = drones[3]

        drone1.sendControlPosition(-0.5, 0, 0, 0.5, 0, 0)
        drone2.sendControlPosition(0, 0.5, 0, 0.5, 0, 0)
        drone3.sendControlPosition(0.5, 0, 0, 0.5, 0, 0)
        drone4.sendControlPosition(0, -0.5, 0, 0.5, 0, 0)

        sleep(2.5)

        drone1.sendControlPosition(0, -0.5, 0, 0.5, 0, 0)
        drone2.sendControlPosition(-0.5, 0, 0, 0.5, 0, 0)
        drone3.sendControlPosition(0, 0.5, 0, 0.5, 0, 0)
        drone4.sendControlPosition(0.5, 0, 0, 0.5, 0, 0)

        sleep(2.5)


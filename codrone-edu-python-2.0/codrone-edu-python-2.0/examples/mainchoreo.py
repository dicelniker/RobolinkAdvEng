import math

from swarm2 import *
from codrone_edu import *

class Choreography2():

    def __init__(self):
        return

    def runSequence(self,swarm):

        drones = swarm.get_drone_objects()

        drone1 = drones[0]
        drone2 = drones[1]
        drone3 = drones[2]

        sleep(5)

        swarm.all_drones("sendControlPosition", 0,0,1,0.25,359,90)

        sleep(6)

        swarm.all_drones("sendControlPosition", 0,0,-1,0.25,359,90)

        sleep(5)

        drone1.sendControlPosition(0.5,0,0,0.5,0,0)
        drone3.sendControlPosition(-0.5,0,0,0.5,0,0)
        drone2.hover()

        sleep(4)

        drone1.sendControlPosition(0,-1.83,0,0.5,0,0)
        drone3.sendControlPosition(0,1.83,0,0.5,0,0)
        drone2.hover()

        sleep(12)

        drone1.sendControlPosition(-1,0,0,0.5,0,0)
        drone3.sendControlPosition(1,0,0,0.5,0,0)
        drone2.hover()

        sleep(6.7)

        drone1.sendControlPosition(0,1.83,0,0.5,0,0)
        drone3.sendControlPosition(0,-1.83,0,0.5,0,0)
        drone2.hover()

        sleep(5.5)
        #
        # swarm.all_drones("drone_buzzer", 260, 1.5)
        #
        # sleep(2)
        #
        # drone1.sendControlPosition(0,0,-1,0.8,0,0)
        #
        drone1.hover()
        drone2.sendControlPosition(0,0,-0.5,0.5,0,0)
        drone3.hover()

        sleep(3)

        drone2.set_drone_LED(255,0,0,100)

        for i in range (765):
            if (i<=255):
                drone2.set_drone_LED(255-i, i, 0, 100)
            if (i> 255 & i <= 510):
                drone2.set_drone_LED(0, 255-(i-255), (i-255), 100)
            else:
                drone2.set_drone_LED(i-510, 0, 255-(i-510), 100)
            sleep(0.01)

        # drone3.sendControlPosition(0,0,0,0,359,180)
        #
        # sleep(3)
        #
        # swarm.all_drones("hover")

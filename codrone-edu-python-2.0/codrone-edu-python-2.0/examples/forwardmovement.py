import math

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
        """
                drone movement command

                Use real values for position and velocity, and
                integer values for heading and rotational Velocity.
                :param positionX: float	-10.0 ~ 10.0	meter	Front (+), Back (-)
                :param positionY: float	-10.0 ~ 10.0	meter	Left(+), Right(-)
                :param positionZ: float	-10.0 ~ 10.0	meter	Up (+), Down (-)
                :param velocity: float	0.5 ~ 2.0	m/s	position movement speed
                :param heading: Int16	-360 ~ 360	degree	Turn left (+), turn right (-)
                :param rotationalVelocity:
                :return: Int16	10 ~ 360	degree/s	left and right rotation speed
        """

        drone1.sendControlPosition(1,0,0,0.5,0,0)
        drone2.sendControlPosition(1, 0, 0, 0.5, 0, 0)
        drone3.sendControlPosition(1, 0, 0, 0.5, 0, 0)



        sleep(2)
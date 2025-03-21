import math
from codrone_edu.swarm import *


class Hexagon:

    def __init__(self):
        return

    def run_sequence(self, swarm, selected_drone_indices):
        drones = swarm.get_drones()
        if len(selected_drone_indices) != 6:
            print("Please select six drones to run the choreography")
            return

        drone1 = drones[selected_drone_indices[0]]
        drone2 = drones[selected_drone_indices[1]]
        drone3 = drones[selected_drone_indices[2]]
        drone4 = drones[selected_drone_indices[3]]
        drone5 = drones[selected_drone_indices[4]]
        drone6 = drones[selected_drone_indices[5]]

        a = 1.5*math.sqrt(3)/2
        b = 1.5*0.5

        sleep(2)

        speed = 0.75
        drone1.sendControlPosition(0,-1.5,0,0.75,0,0)
        drone2.sendControlPosition(-1*a,-1*b,0,0.75,0,0)
        drone3.sendControlPosition(-1*a,b,0,0.75,0,0)
        drone4.sendControlPosition(0,1.5,0,0.75,0,0)
        drone5.sendControlPosition(a,b,0,0.75,0,0)
        drone6.sendControlPosition(a,-1*b,0,0.75,0,0)

        sleep(3)

        drone1.sendControlPosition(-1.5,0,0,speed,0,0)
        drone2.sendControlPosition(0,1.5,0,speed,0,0)
        drone3.sendControlPosition(1.5,0,0,speed,0,0)
        drone4.sendControlPosition(0,-1.5,0,speed,0,0)
        drone1.sendControlPosition(-1*a,-1*b,0,0.75,0,0)
        drone2.sendControlPosition(-1*a,b,0,0.75,0,0)
        drone3.sendControlPosition(0,1.5,0,0.75,0,0)
        drone4.sendControlPosition(a,b,0,0.75,0,0)
        drone5.sendControlPosition(a,-1*b,0.75,0,0,0)
        drone6.sendControlPosition(0,-1.5,0,0.75,0,0)

        sleep(3)

        drone1.sendControlPosition(0,-1.5,0,speed,0,0)
        drone2.sendControlPosition(-1.5,0,0,speed,0,0)
        drone3.sendControlPosition(0,1.5,0,speed,0,0)
        drone4.sendControlPosition(1.5,0,0,speed,0,0)
        drone1.sendControlPosition(-1*a,b,0,0.75,0,0)
        drone2.sendControlPosition(0,1.5,0,0.75,0,0)
        drone3.sendControlPosition(a,b,0,0.75,0,0)
        drone4.sendControlPosition(a,-1*b,0,0.75,0,0)
        drone5.sendControlPosition(0,-1.5,0,0.75,0,0)
        drone6.sendControlPosition(-1*a,-1*b,0,0.75,0,0)

        sleep(3)

        drone1.sendControlPosition(1.5,0,0,speed,0,0)
        drone2.sendControlPosition(0,-1.5,0,speed,0,0)
        drone3.sendControlPosition(-1.5,0,0,speed,0,0)
        drone4.sendControlPosition(0,1.5,0,speed,0,0)
        drone1.sendControlPosition(0,1.5,0,0.75,0,0)
        drone2.sendControlPosition(a,b,0,0.75,0,0)
        drone3.sendControlPosition(a,-1*b,0,0.75,0,0)
        drone4.sendControlPosition(0,-1.5,0,0.75,0,0)
        drone5.sendControlPosition(-1*a,-1*b,0,0.75,0,0)
        drone6.sendControlPosition(-1*a,b,0,0.75,0,0)

        sleep(3)
        drone1.sendControlPosition(a,b,0,0.75,0,0)
        drone2.sendControlPosition(a,-1*b,0,0.75,0,0)
        drone3.sendControlPosition(0,-1.5,0,0.75,0,0)
        drone4.sendControlPosition(-1*a,-1*b,0,0.75,0,0)
        drone5.sendControlPosition(-1*a,b,0,0.75,0,0)
        drone6.sendControlPosition(0,1.5,0,0.75,0,0)

        sleep(3)

        drone1.sendControlPosition(0,1.5,0,speed,0,0)
        drone2.sendControlPosition(1.5,0,0,speed,0,0)
        drone3.sendControlPosition(0,-1.5,0,speed,0,0)
        drone4.sendControlPosition(-1.5,0,0,speed,0,0)
        drone1.sendControlPosition(a,-1*b,0,0.75,0,0)
        drone2.sendControlPosition(0,-1.5,0,0.75,0,0)
        drone3.sendControlPosition(-1*a,-1*b,0,0.75,0,0)
        drone4.sendControlPosition(-1*a,b,0,0.75,0,0)
        drone5.sendControlPosition(0,1.5,0,0.75,0,0)
        drone6.sendControlPosition(a,b,0,0.75,0,0)

        sleep(3)

        drone1.sendControlPosition(0,0,1,0.75,0,0)

        sleep(0.5)

        drone2.sendControlPosition(0,0,1,0.75,0,0)

        sleep(0.5)

        drone3.sendControlPosition(0,0,1,0.75,0,0)

        sleep(0.5)

        drone4.sendControlPosition(0,0,1,0.75,0,0)

        sleep(0.5)

        drone5.sendControlPosition(0,0,1,0.75,0,0)

        sleep(0.5)

        drone6.sendControlPosition(0,0,1,0.75,0,0)

        sleep(2)

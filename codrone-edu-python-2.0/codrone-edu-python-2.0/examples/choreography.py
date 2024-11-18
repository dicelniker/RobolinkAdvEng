from swarm2 import *

class Choreography():

    def __init__(self):
        return

    def runSequence(self,swarm):

        drones = swarm.get_drone_objects()
        drone1 = drones[0]
        drone2 = drones[1]
        drone3 = drones[2]
        drone4 = drones[3]

        dist = 150

        swarm.one_drone(drone1, "move_backward", distance=dist, units="cm", speed=0.3)
        swarm.one_drone(drone2, "move_left", distance=dist, units="cm", speed=0.3)
        swarm.one_drone(drone3, "move_forward", distance=dist, units="cm", speed=0.3)
        swarm.one_drone(drone4, "move_right", distance=dist, units="cm", speed=0.3)

        sleep(2)

        swarm.one_drone(drone1, "move_right", distance=dist, units="cm", speed=0.3)
        swarm.one_drone(drone2, "move_backward", distance=dist, units="cm", speed=0.3)
        swarm.one_drone(drone3, "move_left", distance=dist, units="cm", speed=0.3)
        swarm.one_drone(drone4, "move_forward", distance=dist, units="cm", speed=0.3)

        sleep(2)

        swarm.one_drone(drone1, "move_forward", distance=dist, units="cm", speed=0.3)
        swarm.one_drone(drone2, "move_right", distance=dist, units="cm", speed=0.3)
        swarm.one_drone(drone3, "move_backward", distance=dist, units="cm", speed=0.3)
        swarm.one_drone(drone4, "move_left", distance=dist, units="cm", speed=0.3)

        sleep(2)

        swarm.one_drone(drone1, "move_left", distance=dist, units="cm", speed=0.3)
        swarm.one_drone(drone2, "move_forward", distance=dist, units="cm", speed=0.3)
        swarm.one_drone(drone3, "move_right", distance=dist, units="cm", speed=0.3)
        swarm.one_drone(drone4, "move_backward", distance=dist, units="cm", speed=0.3)

        sleep(2)
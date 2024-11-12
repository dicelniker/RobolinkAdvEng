from swarm2 import *

class Choreography():

    def __init__(self):
        return

    def runSequence(self,swarm):

        '''
        swarm.all_drones("hover", 1)

        positions1 = [[0, 0, 0.5], [0, 0, 0.7]]
        positions2 = [[0, 0, 0.7], [0, -0.3, 0.5]]

        swarm.all_drones("hover", 3)

        swarm.drone_positions(positions1, 0.2)

        sleep(10)

        swarm.drone_positions(positions2, 0.2)

        sleep(5)
        '''

        swarm.all_drones("spiral", 50, 3, 1)


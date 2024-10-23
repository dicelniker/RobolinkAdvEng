from codrone_edu.drone import *
from codrone_edu.swarm import *

init_time = time.time()

swarm = Swarm()
swarm.connect()

end_time = time.time()
print("Time to connect: ", end_time - init_time)

swarm.all_drones("takeoff")
swarm.all_drones("hover",1)

for i in range(3):

    swarm.all_drones("sendControlWhile", 0,0,0,30,2000)
    swarm.all_drones("sendControlWhile", 0,0,0,-20,2000)

swarm.all_drones("land")

swarm.close()

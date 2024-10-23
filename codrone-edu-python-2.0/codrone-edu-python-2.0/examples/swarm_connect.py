from codrone_edu.drone import *
from codrone_edu import *
from codrone_edu.swarm import *
from swarm2 import *

init_time = time.time()

swarm = Swarm2()
swarm.connect()

end_time = time.time()
print("Time to connect: ", end_time - init_time)

swarm.all_drones("takeoff")
swarm.all_drones("hover",1)

positions1 = [[0, 0, 0.5], [0, 0, 0.7]]
positions2 = [[0, 0, 0.7], [0, -0.3, 0.5]]

timer = time.time()

print("Hover for 3 seconds")

swarm.all_drones("hover",3)

print(time.time() - timer)

timer = time.time()

print("Go To Position 1")

swarm.drone_positions(positions1)

print(time.time()-timer)

timer = time.time()

sleep(10)

print("Go To Position 2")

swarm.drone_positions(positions2)

print(time.time()-timer)
timer = time.time()

sleep(5)

swarm.all_drones("land")

print(time.time()-timer)

swarm.close()
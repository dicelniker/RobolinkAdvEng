from swarm2 import *

init_time = time.time()

swarm = Swarm2()

print(swarm.swarm_size())

list = []

for i in range (1,100):

    print(i)

    swarm.connect()

    init_time = time.time()

    swarm.all_drones("get_battery")

    end_time = time.time()

    list.append(end_time - init_time)

    swarm.close()

print(list)
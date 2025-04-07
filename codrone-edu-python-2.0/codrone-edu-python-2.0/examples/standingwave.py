from codrone_edu.swarm import *

swarm = Swarm()
swarm.connect()
swarm.takeoff()

sync = Sync()

"""
All drones go to the same height
Even indices go down first, odd indices go up first to create a ~~~ standing wave ~~~
"""

for i in range(len(swarm.get_drones())):
    seq = Sequence(i)
    seq.add('send_absolute_position', 0, 0, 1, 1, 0, 0)
    if i % 2 == 1:
        for j in range(3):
            seq.add('send_absolute_position', 0, 0, 1.3, 1, 0, 0)
            seq.add('send_absolute_position', 0, 0, 0.7, 1, 0, 0)
    else:
        for j in range(3):
            seq.add('send_absolute_position', 0, 0, 0.7, 1, 0, 0)
            seq.add('send_absolute_position', 0, 0, 1.3, 1, 0, 0)
    sync.add(seq)

swarm.run(sync)

# Prints all the steps in the sequence for drone 0
for i in sync.get_sync()[0]:
    print(i)

swarm.land()

swarm.close()

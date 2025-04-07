from codrone_edu.swarm import *

swarm = Swarm()
swarm.connect()
swarm.takeoff()

sync = Sync()

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

for i in sync.get_sync()[0]:
    print(i)

swarm.land()

swarm.close()

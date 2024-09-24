from codrone_edu.drone import *

drone = Drone()
drone.pair()


drone.takeoff()

xflow = []
yflow = []

for i in range(90):
    drone.hover(0.1)
    xflow.append(drone.get_flow_x())
    yflow.append(drone.get_flow_y())
drone.land()
print(xflow)
print(yflow)



drone.close()
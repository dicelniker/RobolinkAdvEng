from codrone_edu.drone import *
import pandas as pd

drone = Drone()
drone.pair()


drone.takeoff()

x = []
y = []
z = []
for i in range(900):
    drone.hover(0.1)
    x.append(drone.get_pos_x())
    y.append(drone.get_pos_y())
    z.append(drone.get_pos_z())
drone.land()
print(x)
print(y)
print(z)
df = pd.DataFrame({'x': x, 'y': y, 'z': z})

# Saving the DataFrame to a CSV file
df.to_csv('drone3hoverdata.csv', index=False)



drone.close()
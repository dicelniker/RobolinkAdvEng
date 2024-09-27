import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import pandas as pd

# Function to load data from a CSV file
def load_drone_data(csv_file):
    data = pd.read_csv(csv_file)
    x = data['x'].values
    y = data['y'].values
    z = data['z'].values
    return x, y, z

# Function to calculate the range (difference between max and min) for x, y, and z
def calculate_range(x, y, z):
    x_range = np.max(x) - np.min(x)
    y_range = np.max(y) - np.min(y)
    z_range = np.max(z) - np.min(z)
    return x_range, y_range, z_range

# List of drone data files and corresponding drone names
drones = [
    ('drone1hoverdata.csv', 'Drone1'),
    ('drone2hoverdata.csv', 'Drone2'),
    ('drone3hoverdata.csv', 'Drone3'),
    ('drone4hoverdata.csv', 'Drone4'),
    ('celdronehoverdata.csv', 'CelDrone'),
    ('celdronesilvhoverdata.csv', 'CelDroneSilver')
]

# Create the figure
fig = plt.figure(figsize=(10, 5))  # Adjust the figure size

# Colors for each drone's plot
colors = ['b', 'r', 'g', 'c', 'm', 'y']

# Plot for all drones
ax1 = fig.add_subplot(121, projection='3d')  # 3D plot for all drones
ax2 = fig.add_subplot(122)  # 2D plot for all drones

# Loop through each drone to plot and calculate ranges
for i, (csv_file, drone_name) in enumerate(drones):
    # Load the data
    x, y, z = load_drone_data(csv_file)

    # Plot data for each drone
    ax1.plot(x, y, z, linestyle='-', color=colors[i], label=drone_name)
    ax2.plot(x, y, linestyle='-', color=colors[i], label=drone_name)

    # Calculate the range for x, y, and z
    x_range, y_range, z_range = calculate_range(x, y, z)
    print(f'{drone_name} - X Range: {x_range:.2f}, Y Range: {y_range:.2f}, Z Range: {z_range:.2f}')

# Customize plots
ax1.set_xlabel('X Location')
ax1.set_ylabel('Y Location')
ax1.set_zlabel('Z Location')
ax1.set_title('Drone Locations Over Time (3D)')
ax1.legend()

ax2.set_xlabel('X Location')
ax2.set_ylabel('Y Location')
ax2.set_title('Drone Locations Over Time (2D)')
ax2.legend()

# Adjust layout
plt.tight_layout()
plt.show()

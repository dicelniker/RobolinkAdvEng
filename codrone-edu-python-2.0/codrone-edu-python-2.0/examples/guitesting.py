import tkinter as tk
from swarm2 import *
from tkinter import colorchooser
import random

droneIcons = []

swarm = Swarm2()
#num_drones = swarm.swarm_size()

num_drones = 10  # Specify the number of drones

def open_color_picker(drone):
    color_code = colorchooser.askcolor(title="Choose Drone Color")

    if color_code[1]:
        new_color = color_code[1]
        rgb_value = color_code[0]
        print(f"Selected RGB color: {rgb_value}")

        # Update the drone's color in the dictionary
        drone["color"] = new_color
        # Use canvas.itemconfig to change the fill color of the oval
        canvas.itemconfig(drone["oval"], fill=new_color)

root = tk.Tk()
root.title("Swarm GUI")

# Function definitions for swarm control buttons
def swarm_connect():
    print("Swarm is connecting...")
    swarm.connect()

def swarm_takeoff():
    print("Swarm is taking off...")
    swarm.all_drones("takeoff")

def swarm_land():
    print("Swarm is landing...")
    swarm.all_drones("land")

def swarm_close():
    print("Swarm is disconnecting...")
    swarm.close()

# Control buttons
button1 = tk.Button(root, text="SWARM CONNECT", command=swarm_connect)
button1.pack(pady=5)

button2 = tk.Button(root, text="SWARM TAKEOFF", command=swarm_takeoff)
button2.pack(pady=5)

button3 = tk.Button(root, text="SWARM LAND", command=swarm_land)
button3.pack(pady=5)

button4 = tk.Button(root, text="SWARM DISCONNECT", command=swarm_close)
button4.pack(pady=5)

# Inputs for grid dimensions
tk.Label(root, text="Rows:").pack()
rows_input = tk.Entry(root)
rows_input.pack()

tk.Label(root, text="Columns:").pack()
cols_input = tk.Entry(root)
cols_input.pack()

# Function to create the grid and place drones
def create_grid():
    global canvas, rows, cols

    # Get user-defined rows and columns
    rows = int(rows_input.get())
    cols = int(cols_input.get())

    # Clear any existing canvas and drones
    if 'canvas' in globals():
        canvas.destroy()
    droneIcons.clear()

    # Grid and padding setup
    cell_width = 50
    cell_height = 50
    padding = 20  # Padding on all sides

    # Canvas dimensions adjusted to include padding on all sides
    canvas_width = cols * cell_width + 2 * padding
    canvas_height = rows * cell_height + 2 * padding

    canvas = tk.Canvas(root, width=canvas_width, height=canvas_height, bg="white")
    canvas.pack()

    # Draw the grid with padding
    for i in range(rows + 1):
        canvas.create_line(padding, i * cell_height + padding, cols * cell_width + padding, i * cell_height + padding)
    for j in range(cols + 1):
        canvas.create_line(j * cell_width + padding, padding, j * cell_width + padding, rows * cell_height + padding)

    # Place drones in an orderly manner, wrapping across rows
    for i in range(num_drones):
        row = i // (cols)
        col = (i) % (cols)
        x = col * cell_width + padding
        y = row * cell_height + padding
        color = random.choice(["red", "blue", "green", "yellow", "purple", "orange", "black", "turquoise", "pink"])
        drone_oval = canvas.create_oval(x - 5, y - 5, x + 5, y + 5, fill=color)

        # Save drone data, including color and associated canvas object ID
        drone = {"color": color, "position": (row, col), "oval": drone_oval}
        droneIcons.append(drone)

        # Bind click event to open color picker for each drone
        def on_drone_click(event, drone=drone):
            open_color_picker(drone)

        canvas.tag_bind(drone_oval, "<Button-1>", on_drone_click)

# Button to generate grid
generate_button = tk.Button(root, text="Generate Grid", command=create_grid)
generate_button.pack(pady=10)

root.mainloop()

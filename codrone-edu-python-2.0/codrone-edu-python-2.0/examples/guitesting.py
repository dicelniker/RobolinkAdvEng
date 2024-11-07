import tkinter as tk
from swarm2 import *
from tkinter import colorchooser
import colorsys

droneIcons = []

swarm = Swarm2()
num_drones = swarm.connect()

def hsv_to_rgb(h, s, v):
    rgb_float = colorsys.hsv_to_rgb(h, s, v)
    return tuple(int(255 * c) for c in rgb_float)

def open_color_picker(drone, index):
    color_code = colorchooser.askcolor(title="Choose Drone Color")

    if color_code[1]:
        new_color = color_code[1]
        rgb_value = color_code[0]
        print(f"Selected RGB color: {rgb_value}")

        drone["color"] = new_color
        canvas.itemconfig(drone["oval"], fill=new_color)

        r, g, b = map(int, rgb_value)
        swarm.drone_color(index, r, g, b)

root = tk.Tk()
root.title("Swarm GUI")

def swarm_takeoff():
    print("Swarm is taking off...")
    swarm.all_drones("takeoff")

def swarm_land():
    print("Swarm is landing...")
    swarm.all_drones("land")

def swarm_close():
    print("Swarm is disconnecting...")
    swarm.close()

def swarm_choreo():
    sleep(3)
    print("Starting Choreography")
    swarm.all_drones("flip", "front")


button2 = tk.Button(root, text="SWARM TAKEOFF", font=('verdana 15'), command=swarm_takeoff)
button2.pack(pady=5)

button3 = tk.Button(root, text="SWARM LAND", font=('verdana 15'), command=swarm_land)
button3.pack(pady=5)

button4 = tk.Button(root, text="SWARM DISCONNECT", font=('verdana 15'), command=swarm_close)
button4.pack(pady=5)

button5 = tk.Button(root, text="SWARM CHOREOGRAPHY", font=('verdana 15'), command=swarm_choreo)
button5.pack(pady=5)

tk.Label(root, text="Rows:", font=('verdana 15')).pack()
rows_input = tk.Entry(root)
rows_input.pack()

tk.Label(root, text="Columns:", font=('verdana 15')).pack()
cols_input = tk.Entry(root)
cols_input.pack()

def create_grid():
    global canvas, rows, cols

    rows = int(rows_input.get())
    cols = int(cols_input.get())

    if 'canvas' in globals():
        canvas.destroy()
    droneIcons.clear()

    cell_width = 100
    cell_height = 100
    padding = 20

    canvas_width = cols * cell_width + 2 * padding
    canvas_height = rows * cell_height + 2 * padding

    canvas = tk.Canvas(root, width=canvas_width, height=canvas_height, bg="white")
    canvas.pack()

    for i in range(rows + 1):
        canvas.create_line(padding, i * cell_height + padding, cols * cell_width + padding, i * cell_height + padding)
    for j in range(cols + 1):
        canvas.create_line(j * cell_width + padding, padding, j * cell_width + padding, rows * cell_height + padding)

    hue_increment = 360 / num_drones
    for i in range(num_drones):
        row = i // cols
        col = i % cols
        x = col * cell_width + padding
        y = row * cell_height + padding

        hue = (i * hue_increment) / 360
        rgb = hsv_to_rgb(hue, 1, 1)
        color_hex = f'#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}'

        drone_oval = canvas.create_oval(x - 15, y - 15, x + 15, y + 15, fill=color_hex)
        swarm.drone_color(i, *rgb)

        drone = {"color": color_hex, "position": (row, col), "oval": drone_oval}
        droneIcons.append(drone)

        def on_drone_click(event, drone=drone, index=i):
            open_color_picker(drone, index)

        canvas.tag_bind(drone_oval, "<Button-1>", on_drone_click)

generate_button = tk.Button(root, text="Generate Grid",  font=('verdana 15'), command=create_grid)
generate_button.pack(pady=10)

root.mainloop()

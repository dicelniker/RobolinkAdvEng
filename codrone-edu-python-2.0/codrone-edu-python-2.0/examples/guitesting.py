import tkinter as tk
from swarm2 import *
from tkinter import colorchooser
import random
import matplotlib.colors as mcolors

# GUI is now under a class
class SwarmGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Swarm GUI")
        self.canvas = None
        self.droneIcons = []
        self.swarm = Swarm2()
        self.rows_input = None
        self.cols_input = None
        self.create_inputs()

    # This function converts a string of a color into a list of the color's RGBA values
    def process_color(self, color_str):
        rgba_color = list(mcolors.to_rgba(color_str))
        for i in range(4):
            rgba_color[i] = int(255 * rgba_color[i])

        return rgba_color

    # This function opens a color chooser menu, where the user chooses what color the drone should be
    def open_color_picker(self, drone):
        color_code = colorchooser.askcolor(title="Choose Drone Color")

        if color_code[1]:
            new_color = color_code[1]
            rgb_value = color_code[0]
            print(f"Selected RGB color: {rgb_value}")

            # Update the drone's color in the dictionary
            drone["color"] = new_color

            # Convert string into RGBA list
            rgba_color = self.process_color(drone["color"])

            # Change the drone's LED color on the drone
            self.swarm.one_drone(drone["drone_obj"], "set_drone_LED", *rgba_color)

            # Use canvas.itemconfig to change the fill color of the oval
            self.canvas.itemconfig(drone["oval"], fill=new_color)

    # This function creates the labels and text inputs for the number of rows and columns for the swarm
    def create_inputs(self):
        # Inputs for grid dimensions
        tk.Label(self.root, text="Rows:").pack()
        self.rows_input = tk.Entry(self.root)
        self.rows_input.pack()

        tk.Label(self.root, text="Columns:").pack()
        self.cols_input = tk.Entry(self.root)
        self.cols_input.pack()

        # Button to generate grid
        generate_button = tk.Button(self.root, text="Generate Grid", command=self.create_grid)
        generate_button.pack(pady=10)

    # Function to create the grid and place drones
    def create_grid(self):
        global swarm_drones, num_drones, canvas, rows, cols

        # Connect all drones
        self.swarm.connect()
        swarm_drones = self.swarm.get_drone_objects() # storing Drone objects
        num_drones = len(swarm_drones)

        # Get user-defined rows and columns
        rows = int(self.rows_input.get())
        cols = int(self.cols_input.get())

        # Clear any existing canvas and drones
        if 'canvas' in globals() or self.canvas is not None:
            self.canvas.destroy()
        self.droneIcons.clear()

        # Grid and padding setup
        cell_width = 50
        cell_height = 50
        padding = 20  # Padding on all sides

        # Canvas dimensions adjusted to include padding on all sides
        canvas_width = cols * cell_width + 2 * padding
        canvas_height = rows * cell_height + 2 * padding

        self.canvas = tk.Canvas(self.root, width=canvas_width, height=canvas_height, bg="white")
        self.canvas.pack()

        # Draw the grid with padding
        for i in range(rows + 1):
            self.canvas.create_line(padding, i * cell_height + padding, cols * cell_width + padding,
                               i * cell_height + padding)
        for j in range(cols + 1):
            self.canvas.create_line(j * cell_width + padding, padding, j * cell_width + padding,
                               rows * cell_height + padding)

        # Place drones in an orderly manner (50 centimeters away from each other), wrapping across rows
        for i in range(num_drones):
            row = i // (cols)
            col = (i) % (cols)
            x = col * cell_width + cell_width // 2 + padding
            y = row * cell_height + cell_height // 2 + padding
            color = random.choice(["red", "blue", "green", "yellow", "purple", "orange", "black", "turquoise", "pink"])
            drone_oval = self.canvas.create_oval(x - 5, y - 5, x + 5, y + 5, fill=color)

            rgba_color = self.process_color(color)  # Convert string into RGBA list

            # Save drone data, including color, associated canvas object ID, and Drone object
            drone = {"color": rgba_color, "position": (x, y), "oval": drone_oval, "drone_obj": swarm_drones[i]}

            # Change the drone's LED color on the drone
            self.swarm.one_drone(drone["drone_obj"], "set_drone_LED", *rgba_color)

            # Store drone dictionary to droneIcons
            self.droneIcons.append(drone)

            # Bind click event to open color picker for each drone
            def on_drone_click(event, drone=drone):
                self.open_color_picker(drone)

            self.canvas.tag_bind(drone_oval, "<Button-1>", on_drone_click)

    def run(self):
        self.root.mainloop()

app = SwarmGUI()
app.run()
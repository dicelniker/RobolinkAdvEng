import tkinter as tk
from swarm2 import *
from tkinter import colorchooser
import matplotlib.colors as mcolors

class SwarmGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Swarm GUI")
        self.root.configure(bg='#e6f3ff')  # Slightly darker light blue background
        self.canvas = None
        self.droneIcons = []
        self.swarm = Swarm2()
        self.rows_input = None
        self.cols_input = None
        self.generate_button = None
        self.create_inputs()
        self.create_control_buttons()
        self.choreo = Choreography()
        self.default_colors = ["red", "white", "green", "blue", "purple", "black"]

    def process_color(self, color_str):
        rgba_color = list(mcolors.to_rgba(color_str))
        for i in range(4):
            rgba_color[i] = int(255 * rgba_color[i])
        return rgba_color

    def open_color_picker(self, drone):
        color_code = colorchooser.askcolor(title="Choose Drone Color")
        if color_code[1]:
            new_color = color_code[1]
            rgb_value = color_code[0]
            print(f"Selected RGB color: {rgb_value}")
            drone["color"] = new_color
            rgba_color = self.process_color(drone["color"])
            self.swarm.one_drone(drone["drone_obj"], "set_drone_LED", *rgba_color)
            self.canvas.itemconfig(drone["oval"], fill=new_color)

    def create_control_buttons(self):
        button_style = {
            'font': ('Helvetica', 10, 'bold'),
            'bg': '#dff0e0',  # Slightly darker light green
            'fg': '#2c3e50',
            'relief': 'solid',
            'bd': 1,
            'width': 15,
            'height': 1
        }

        take_off_button = tk.Button(self.root, text="Take Off", command=self.take_off, **button_style)
        take_off_button.pack(pady=5)

        land_button = tk.Button(self.root, text="Land", command=self.land, **button_style)
        land_button.pack(pady=5)

        choreography_button = tk.Button(self.root, text="Run Choreography", command=self.run_choreography, **button_style)
        choreography_button.pack(pady=5)

    def take_off(self):
        print("Taking off...")
        self.swarm.all_drones("takeoff")

    def land(self):
        print("Landing...")
        self.swarm.all_drones("land")
        self.swarm.all_drones("emergency_stop")

    def run_choreography(self):
        print("Running choreography...")
        self.choreo.runSequence(self.swarm)

    def create_inputs(self):
        label_style = {
            'font': ('Helvetica', 10, 'bold'),
            'bg': '#e6f3ff',  # Match root background
            'fg': '#2c3e50'
        }

        entry_style = {
            'font': ('Helvetica', 10, 'bold'),
            'relief': 'solid',
            'bd': 1,
            'highlightthickness': 1,
            'highlightbackground': '#4169E1',  # Blue outline
            'highlightcolor': '#4169E1',  # Blue outline when focused
            'bg': 'white'
        }

        button_style = {
            'font': ('Helvetica', 10, 'bold'),
            'bg': '#dff0e0',  # Slightly darker light green
            'fg': '#2c3e50',
            'relief': 'solid',
            'bd': 1,
            'width': 15,
            'height': 1
        }

        tk.Label(self.root, text="Rows:", **label_style).pack()
        self.rows_input = tk.Entry(self.root, **entry_style)
        self.rows_input.pack(pady=5)

        tk.Label(self.root, text="Columns:", **label_style).pack()
        self.cols_input = tk.Entry(self.root, **entry_style)
        self.cols_input.pack(pady=5)

        self.generate_button = tk.Button(self.root, text="Generate Grid", command=self.create_grid, **button_style)
        self.generate_button.pack(pady=10)

    def create_grid(self):
        global swarm_drones, num_drones, canvas, rows, cols

        self.generate_button.config(state="disabled")
        self.rows_input.config(state="disabled")
        self.cols_input.config(state="disabled")

        self.swarm.connect()
        swarm_drones = self.swarm.get_drone_objects()
        num_drones = len(swarm_drones)

        rows = int(self.rows_input.get())
        cols = int(self.cols_input.get())

        if hasattr(self, 'canvas') and self.canvas is not None:
            self.canvas.destroy()
        self.droneIcons.clear()

        cell_width = 50
        cell_height = 50
        padding = 20

        canvas_width = cols * cell_width + 2 * padding
        canvas_height = rows * cell_height + 2 * padding

        self.canvas = tk.Canvas(self.root, width=canvas_width, height=canvas_height, bg="white")
        self.canvas.pack()

        # Draw grid lines with thin blue lines
        for i in range(rows + 1):
            self.canvas.create_line(padding, i * cell_height + padding,
                                  cols * cell_width + padding, i * cell_height + padding,
                                  fill='#4169E1', width=1)
        for j in range(cols + 1):
            self.canvas.create_line(j * cell_width + padding, padding,
                                  j * cell_width + padding, rows * cell_height + padding,
                                  fill='#4169E1', width=1)

        drones_placed = 0
        current_row = 0

        while drones_placed < num_drones and current_row < rows:
            for col in range(cols + 1):
                if drones_placed >= num_drones:
                    break

                x = col * cell_width + padding
                y = current_row * cell_height + padding

                color_index = drones_placed % len(self.default_colors)
                color = self.default_colors[color_index]

                drone_oval = self.canvas.create_oval(x - 5, y - 5, x + 5, y + 5, fill=color)
                rgba_color = self.process_color(color)

                drone = {"color": rgba_color, "position": (x, y),
                        "oval": drone_oval, "drone_obj": swarm_drones[drones_placed]}
                self.swarm.one_drone(drone["drone_obj"], "set_drone_LED", *rgba_color)
                self.droneIcons.append(drone)

                def on_drone_click(event, drone=drone):
                    self.open_color_picker(drone)

                self.canvas.tag_bind(drone_oval, "<Button-1>", on_drone_click)
                drones_placed += 1

            current_row += 1

    def run(self):
        self.root.mainloop()

app = SwarmGUI()
app.run()
#meow
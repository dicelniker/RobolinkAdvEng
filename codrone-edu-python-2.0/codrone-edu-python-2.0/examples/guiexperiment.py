import tkinter as tk
from codrone_edu.swarm import *
from tkinter import colorchooser
import matplotlib.colors as mcolors

#pink e61848
#dark blue 05001c
#blue 242d78
#light blue 3fd4ff

class SwarmGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Swarm GUI")
        self.root.configure(bg='#05001c')  # dark blue
        self.canvas = None
        self.droneIcons = []
        self.swarm = Swarm()
        self.rows_input = None
        self.cols_input = None
        self.generate_button = None
        self.forward_border = None  # Store border frames as attributes
        self.backward_border = None
        self.left_border = None
        self.right_border = None
        self.forward_button = None # Store buttons as attributes
        self.backward_button = None
        self.left_button = None
        self.right_button = None

        self.create_inputs()
        self.create_control_buttons()
        self.default_colors = ["red", "white", "green", "blue", "purple", "black"]
        self.bind_keys()
        self.root.geometry("500x650")


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
            'bg': '#e61848',  # pink
            'fg': '#fff',
            'relief': 'solid',
            'bd': 1,
            'width': 15,
            'height': 1,
            'cursor': "heart"
        }

        # Flight control buttons
        take_off_button = tk.Button(self.root, text="Take Off", command=self.take_off, **button_style)
        take_off_button.pack(pady=5)

        land_button = tk.Button(self.root, text="Land", command=self.land, **button_style)
        land_button.pack(pady=15)


        movement_frame = tk.Frame(self.root, bg='#05001c')
        movement_frame.pack(pady=10)

        # Movement buttons
        movement_button_style = {
            'font': ('Helvetica', 12, 'bold'),  # Slightly larger and bolder
            'bg': '#05001c',  # Dark Blue - default button color
            'fg': 'white',
            'relief': 'solid',
            'padx': 3,  # Padding to make the buttons bigger
            'pady': 3,
            'width': 2,  # Explicit width to control button size
            'height': 1,  # Explicit height
            'foreground': '#e61848', # default text color
            'activeforeground': '#3fd4ff',
            'borderwidth': 0 # Remove default button border
        }

        pink_border_style = {
            'highlightbackground': '#e61848', # default border color
            'highlightcolor': '#e61848',
            'highlightthickness': 2,
            'bd': 0
        }

        light_blue_border_style = {
            'highlightbackground': '#3fd4ff', # highlight border color
            'highlightcolor': '#3fd4ff',
            'highlightthickness': 2,
            'bd': 0
        }

        def highlight_button(border_frame, button):
            border_frame.config(highlightbackground='#3fd4ff', highlightcolor='#3fd4ff') # light blue border
            button.config(bg='white', fg='#3fd4ff') # white button, light blue text

        def reset_button(border_frame, button):
            border_frame.config(highlightbackground='#e61848', highlightcolor='#e61848') # pink border
            button.config(bg='#05001c', fg='white') # dark blue button, white text


        # Forward Button with Border
        self.forward_border = tk.Frame(movement_frame, **pink_border_style)
        self.forward_button = tk.Button(self.forward_border, text="↑", command=lambda: [self.forward(), highlight_button(self.forward_border, self.forward_button), self.root.after(100, lambda: reset_button(self.forward_border, self.forward_button))], **movement_button_style)
        self.forward_button.pack(in_=self.forward_border) # Pack button inside the border frame

        # Backward Button with Border
        self.backward_border = tk.Frame(movement_frame, **pink_border_style)
        self.backward_button = tk.Button(self.backward_border, text="↓", command=lambda: [self.backward(), highlight_button(self.backward_border, self.backward_button), self.root.after(100, lambda: reset_button(self.backward_border, self.backward_button))], **movement_button_style)
        self.backward_button.pack(in_=self.backward_border) # Pack button inside the border frame

        # Left Button with Border
        self.left_border = tk.Frame(movement_frame, **pink_border_style)
        self.left_button = tk.Button(self.left_border, text="←", command=lambda: [self.left(), highlight_button(self.left_border, self.left_button), self.root.after(100, lambda: reset_button(self.left_border, self.left_button))], **movement_button_style)
        self.left_button.pack(in_=self.left_border) # Pack button inside the border frame

        # Right Button with Border
        self.right_border = tk.Frame(movement_frame, **pink_border_style)
        self.right_button = tk.Button(self.right_border, text="→", command=lambda: [self.right(), highlight_button(self.right_border, self.right_button), self.root.after(100, lambda: reset_button(self.right_border, self.right_button))], **movement_button_style)
        self.right_button.pack(in_=self.right_border) # Pack button inside the border frame


        tk.Label(self.root, text="Sequences:", font=("Helvetica", 10, "bold"), bg='#05001c', fg='#3fd4ff').pack()

        # Grid layout for the movement buttons - Place the border frames instead of buttons
        self.forward_border.grid(row=0, column=1, padx=5, pady=5)
        self.left_border.grid(row=1, column=0, padx=5, pady=5)
        self.backward_border.grid(row=1, column=1, padx=5, pady=5)
        self.right_border.grid(row=1, column=2, padx=5, pady=5)

        # Create frame for choreography buttons
        choreo_frame = tk.Frame(self.root, bg='#05001c')
        choreo_frame.pack(pady=10)

        # Choreography buttons
        choreo_buttons = [
            ("Main Choreo", self.run_main_choreo),
            ("Hexagon", self.run_hexagon),
            ("Spiral and Flip", self.run_spiral_and_flip),
            ("Upward Spiral", self.run_upward_spiral),
            ("Wiggle", self.run_wiggle)
        ]

        for text, command in choreo_buttons:
            btn = tk.Button(choreo_frame, text=text, command=command, **button_style)
            btn.pack(pady=3)

    def take_off(self):
        print("Taking off...")
        self.swarm.all_drones("takeoff")

    def land(self):
        print("Landing...")
        self.swarm.all_drones("land")
        self.swarm.all_drones("emergency_stop")

    def forward(self):
        print("Moving forward...")

    def backward(self):
        print("Moving backward...")

    def left(self):
        print("Moving left...")

    def right(self):
        print("Moving right...")

    def run_main_choreo(self):
        print("Running main choreography...")
        import mainchoreo
        mainchoreo.run_sequence(self.swarm)

    def run_hexagon(self):
        print("Running hexagon choreography...")
        import hexagon
        hexagon.run_sequence(self.swarm)

    def run_spiral_and_flip(self):
        print("Running spiral and flip choreography...")
        import spiralandflip
        spiralandflip.run_sequence(self.swarm)

    def run_upward_spiral(self):
        print("Running upward spiral choreography...")
        import upwardspiral
        upwardspiral.run_sequence(self.swarm)

    def run_wiggle(self):
        print("Running wiggle choreography...")
        import wiggle
        wiggle.run_sequence(self.swarm)

    def create_inputs(self):
        self.label_style = {
            'font': ('Helvetica', 10, 'bold'),
            'bg': '#05001c',  # Match root background
            'fg': '#3fd4ff'
        }

        self.entry_style = {
            'font': ('Helvetica', 10, 'bold'),
            'relief': 'solid',
            'bd': 1,
            'highlightthickness': 1,
            'highlightbackground': '#4169E1',  # Blue outline
            'highlightcolor': '#4169E1',  # Blue outline when focused
            'bg': 'white'
        }

        self.button_style = {
            'font': ('Helvetica', 10, 'bold'),
            'bg': '#e61848',  # pink
            'fg': '#fff',
            'relief': 'solid',
            'bd': 1,
            'width': 15,
            'height': 1,
            'cursor': "heart"

        }


        tk.Label(self.root, text="Rows:", **self.label_style).pack()
        self.rows_input = tk.Entry(self.root, **self.entry_style)
        self.rows_input.pack(pady=5)

        tk.Label(self.root, text="Columns:", **self.label_style).pack()
        self.cols_input = tk.Entry(self.root, **self.entry_style)
        self.cols_input.pack(pady=5)

        self.generate_button = tk.Button(self.root, text="Generate Grid", command=self.create_grid, **self.button_style)
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

    def bind_keys(self):
        def key_highlight(border_frame, button):
            border_frame.config(highlightbackground='#3fd4ff', highlightcolor='#3fd4ff')
            button.config(bg='white', fg='#3fd4ff')

        def key_reset(border_frame, button):
            border_frame.config(highlightbackground='#e61848', highlightcolor='#e61848')
            button.config(bg='#05001c', fg='white')

        self.root.bind("<Up>", lambda event: [self.forward(), key_highlight(self.forward_border, self.forward_button), self.root.after(100, lambda: key_reset(self.forward_border, self.forward_button))])
        self.root.bind("<Down>", lambda event: [self.backward(), key_highlight(self.backward_border, self.backward_button), self.root.after(100, lambda: key_reset(self.backward_border, self.backward_button))])
        self.root.bind("<Left>", lambda event: [self.left(), key_highlight(self.left_border, self.left_button), self.root.after(100, lambda: key_reset(self.left_border, self.left_button))])
        self.root.bind("<Right>", lambda event: [self.right(), key_highlight(self.right_border, self.right_button), self.root.after(100, lambda: key_reset(self.right_border, self.right_button))])
        self.root.bind("w", lambda event: [self.forward(), key_highlight(self.forward_border, self.forward_button), self.root.after(100, lambda: key_reset(self.forward_border, self.forward_button))])
        self.root.bind("s", lambda event: [self.backward(), key_highlight(self.backward_border, self.backward_button), self.root.after(100, lambda: key_reset(self.backward_border, self.backward_button))])
        self.root.bind("a", lambda event: [self.left(), key_highlight(self.left_border, self.left_button), self.root.after(100, lambda: key_reset(self.left_border, self.left_button))])
        self.root.bind("d", lambda event: [self.right(), key_highlight(self.right_border, self.right_button), self.root.after(100, lambda: key_reset(self.right_border, self.right_button))])
        # To ensure the key presses are registered, the window must have focus.
        # Calling focus_set() here and/or on specific widgets can help.
        self.root.focus_set()

    def run(self):
        self.root.mainloop()

app = SwarmGUI()
app.run()

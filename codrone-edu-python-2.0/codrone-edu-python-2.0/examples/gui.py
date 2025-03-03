import tkinter as tk
from codrone_edu.swarm import *
from tkinter import colorchooser
import matplotlib.colors as mcolors

#pink e61848
#dark blue 05001c
#blue 242d78
#light blue 3fd4ff
#button hover purple #d098fa
#arrow button hover #7214ff

class SwarmGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Swarm GUI")
        self.root.configure(bg='#05001c')  # dark blue
        self.canvas = None
        self.droneIcons = []
        self.swarm = Swarm()
        self.swarm.connect()
        self.hasGeneratedGrid = False

        self.rows_input = None
        self.cols_input = None
        self.generate_button = None
        self.forward_border = None
        self.backward_border = None
        self.left_border = None
        self.right_border = None
        self.forward_button = None
        self.backward_button = None
        self.left_button = None
        self.right_button = None

        self.light_blue = '#3fd4ff'  # Define light blue color
        self.grid_line_color = '#4169E1' # Define grid line color
        self.dark_blue = '#05001c' # Define dark blue color
        self.pink = '#e61848' # Define pink color
        self.hover_purple = '#d098fa' # Define hover purple for red buttons
        self.arrow_hover_blue = '#7214ff' # Define hover blue for arrow buttons

        # --- Title Label ---
        title_label = tk.Label(
            self.root,
            text="CoDrone EDU - Swarm",
            font=('Terminal', 18, 'bold'),
            bg=self.dark_blue,
            fg=self.light_blue,
            pady=10  # Add some padding below the title
        )
        title_label.grid(row=0, column=0, columnspan=2) # Place title at the top, spanning columns

        self.create_input_section()
        self.create_control_buttons()
        self.default_colors = ['red', 'blue', 'orange', 'yellow', 'green', 'light blue', 'purple', 'pink', 'white', 'black']
        self.bind_keys()
        self.root.geometry("390x490")

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
            self.swarm.one_drone(drone["drone_index"], "set_drone_LED", *rgba_color)
            self.swarm.one_drone(drone["drone_index"], "set_controller_LED", *rgba_color)
            self.canvas.itemconfig(drone["oval"], fill=new_color)

    def create_control_buttons(self):
        button_style = {
            'font': ('Helvetica', 10, 'bold'),
            'bg': self.pink,
            'fg': '#fff',
            'relief': 'solid',
            'bd': 1,
            'width': 15,
            'height': 1,
            'cursor': "heart"
        }
        movement_button_style = {
            'font': ('Helvetica', 12, 'bold'),
            'bg': '#05001c', # default background is dark blue
            'fg': 'white', # default foreground is white (for arrow symbol)
            'relief': 'solid',
            'padx': 3,
            'pady': 3,
            'width': 2,
            'height': 1,
            'foreground': '#e61848', # initial foreground color - will be overridden by fg: 'white'
            'activeforeground': '#3fd4ff',
            'borderwidth': 0
        }
        pink_border_style = {
            'highlightbackground': '#e61848',
            'highlightcolor': '#e61848',
            'highlightthickness': 2,
            'bd': 0
        }
        light_blue_border_style = {
            'highlightbackground': '#3fd4ff',
            'highlightcolor': '#3fd4ff',
            'highlightthickness': 2,
            'bd': 0
        }

        def highlight_button(border_frame, button):
            border_frame.config(highlightbackground='#3fd4ff', highlightcolor='#3fd4ff')
            button.config(bg='white', fg='#3fd4ff')

        def reset_button(border_frame, button):
            border_frame.config(highlightbackground='#e61848', highlightcolor='#e61848')
            button.config(bg='#05001c', fg='white')

        def on_button_enter(event):
            event.widget.config(bg=self.hover_purple)

        def on_button_leave(event):
            event.widget.config(bg=self.pink)

        def on_arrow_button_enter(event):
            event.widget.config(bg=self.arrow_hover_blue) # Change background color for arrow buttons on hover

        def on_arrow_button_leave(event):
            event.widget.config(bg='#05001c') # Reset background color for arrow buttons on leave to default dark blue

        # --- Left Section (Takeoff/Landing) with Border ---
        left_control_frame = tk.Frame(self.root, borderwidth=2, relief='solid', padx=5, pady=5, highlightbackground=self.light_blue, highlightcolor=self.light_blue) # Border only, removed bg=self.light_blue, added highlight bg and color
        left_control_frame.grid(row=2, column=0, padx=10, pady=10, sticky=tk.N + tk.S + tk.W + tk.E) # row changed to 2

        take_off_button = tk.Button(left_control_frame, text="Take Off", command=self.take_off, **button_style)
        take_off_button.pack(pady=5)
        take_off_button.bind("<Enter>", on_button_enter) # Hover effect for red buttons
        take_off_button.bind("<Leave>", on_button_leave) # Hover effect for red buttons

        land_button = tk.Button(left_control_frame, text="Land", command=self.land, **button_style)
        land_button.pack(pady=15)
        land_button.bind("<Enter>", on_button_enter) # Hover effect for red buttons
        land_button.bind("<Leave>", on_button_leave) # Hover effect for red buttons

        # --- Auto-Stabilization Buttons ---
        stabilize_button = tk.Button(left_control_frame, text="Stabilize Swarm",
                                           command=self.stabilize_swarm, **button_style)
        stabilize_button.pack(pady=15)  # Adjust pady as needed
        stabilize_button.bind("<Enter>", on_button_enter)
        stabilize_button.bind("<Leave>", on_button_leave)

        # --- Right Section (Sequences) with Border ---
        right_control_frame = tk.Frame(self.root, bg=self.dark_blue, borderwidth=2, relief='solid', padx=5, pady=5, highlightbackground=self.light_blue, highlightcolor=self.light_blue) # Set bg to dark blue, with border
        right_control_frame.grid(row=2, column=1, padx=10, pady=10, sticky=tk.N + tk.S + tk.W + tk.E) # row changed to 2

        tk.Label(right_control_frame, text="Sequences:", font=("Helvetica", 10, "bold"), bg=self.dark_blue, fg=self.light_blue).pack() # bg and fg set explicitly

        choreo_frame = tk.Frame(right_control_frame, bg=self.dark_blue) # choreo frame bg also dark blue to match
        choreo_frame.pack(pady=10)

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
            btn.bind("<Enter>", on_button_enter) # Hover effect for red buttons
            btn.bind("<Leave>", on_button_leave) # Hover effect for red buttons

        # --- Movement Buttons ---
        movement_frame = tk.Frame(self.root, bg='#05001c')
        movement_frame.grid(row=4, column=0, columnspan=2, pady=10) # row changed to 4

        self.forward_border = tk.Frame(movement_frame, **pink_border_style)
        self.forward_button = tk.Button(self.forward_border, text="↑", command=lambda: [self.forward(), highlight_button(self.forward_border, self.forward_button), self.root.after(100, lambda: reset_button(self.forward_border, self.forward_button))], **movement_button_style)
        self.forward_button.pack(in_=self.forward_border)
        self.forward_button.config(fg='white') # set arrow color to white
        self.forward_button.bind("<Enter>", on_arrow_button_enter) # Hover effect for arrow buttons
        self.forward_button.bind("<Leave>", on_arrow_button_leave) # Hover effect for arrow buttons

        self.backward_border = tk.Frame(movement_frame, **pink_border_style)
        self.backward_button = tk.Button(self.backward_border, text="↓", command=lambda: [self.backward(), highlight_button(self.backward_border, self.backward_button), self.root.after(100, lambda: reset_button(self.backward_border, self.backward_button))], **movement_button_style)
        self.backward_button.pack(in_=self.backward_border)
        self.backward_button.config(fg='white') # set arrow color to white
        self.backward_button.bind("<Enter>", on_arrow_button_enter) # Hover effect for arrow buttons
        self.backward_button.bind("<Leave>", on_arrow_button_leave) # Hover effect for arrow buttons

        self.left_border = tk.Frame(movement_frame, **pink_border_style)
        self.left_button = tk.Button(self.left_border, text="←", command=lambda: [self.left(), highlight_button(self.left_border, self.left_button), self.root.after(100, lambda: reset_button(self.left_border, self.left_button))], **movement_button_style)
        self.left_button.pack(in_=self.left_border)
        self.left_button.config(fg='white') # set arrow color to white
        self.left_button.bind("<Enter>", on_arrow_button_enter) # Hover effect for arrow buttons
        self.left_button.bind("<Leave>", on_arrow_button_leave) # Hover effect for arrow buttons

        self.right_border = tk.Frame(movement_frame, **pink_border_style)
        self.right_button = tk.Button(self.right_border, text="→", command=lambda: [self.right(), highlight_button(self.right_border, self.right_button), self.root.after(100, lambda: reset_button(self.right_border, self.right_button))], **movement_button_style)
        self.right_button.pack(in_=self.right_border)
        self.right_button.config(fg='white') # set arrow color to white
        self.right_button.bind("<Enter>", on_arrow_button_enter) # Hover effect for arrow buttons
        self.right_button.bind("<Leave>", on_arrow_button_leave) # Hover effect for arrow buttons

        self.forward_border.grid(row=0, column=1, padx=5, pady=5) # row changed to 0
        self.left_border.grid(row=1, column=0, padx=5, pady=5) # row changed to 1
        self.backward_border.grid(row=1, column=1, padx=5, pady=5) # row changed to 1
        self.right_border.grid(row=1, column=2, padx=5, pady=5) # row changed to 1

    def take_off(self):
        if not self.hasGeneratedGrid:
            print("Please generate grid before running commands.")
            return None
        selected_drone_indices = []
        for index, drone in enumerate(self.droneIcons):
            if drone["selected"].get():
                selected_drone_indices.append(index)

        num_selected_drones = len(selected_drone_indices)

        if num_selected_drones == num_drones:
            print("Taking off ALL drones (all selected)...")
            self.swarm.all_drones("takeoff")  # Take off all drones
        elif num_selected_drones == 0:
            print("No drones selected. Not taking off.")  # Do nothing
        else:
            print(f"Taking off selected drones: {selected_drone_indices}")
            for index in selected_drone_indices:
                self.swarm.one_drone(index, "takeoff")  # Take off only selected drones

    def land(self):
        if not self.hasGeneratedGrid:
            print("Please generate grid before running commands.")
            return None
        selected_drone_indices = []
        for index, drone in enumerate(self.droneIcons):
            if drone["selected"].get():
                selected_drone_indices.append(index)

        num_selected_drones = len(selected_drone_indices)

        if num_selected_drones == num_drones:
            print("Landing ALL drones (all selected)...")
            self.swarm.all_drones("land")  # Land all drones
        elif num_selected_drones == 0:
            print("No drones selected. Not landing.")  # Do nothing
        else:
            print(f"Landing selected drones: {selected_drone_indices}")
            for index in selected_drone_indices:
                self.swarm.one_drone(index, "land")  # Land only selected drones

    def forward(self):
        if not self.hasGeneratedGrid:
            print("Please generate grid before running commands.")
            return None
        selected_drone_indices = []
        for index, drone in enumerate(self.droneIcons):
            if drone["selected"].get():
                selected_drone_indices.append(index)

        num_selected_drones = len(selected_drone_indices)

        if num_selected_drones == num_drones: # Check if ALL drones are selected
            print("Moving forward for ALL drones (all selected)...")
            self.swarm.move_forward(10.0, units="cm", speed=1.0) # Move all drones
        elif num_selected_drones == 0: # Check if NO drones are selected
            print("No drones selected. Not moving forward.") # Do nothing - no movement
        else: # Some drones are selected (but not all)
            print(f"Moving forward for selected drones: {selected_drone_indices}")
            for index in selected_drone_indices:
                self.swarm.one_drone(index, "move_forward", 20.0, units="cm", speed=20.0) # Move only selected

    def backward(self):
        if not self.hasGeneratedGrid:
            print("Please generate grid before running commands.")
            return None
        selected_drone_indices = []
        for index, drone in enumerate(self.droneIcons):
            if drone["selected"].get():
                selected_drone_indices.append(index)

        num_selected_drones = len(selected_drone_indices)

        if num_selected_drones == num_drones: # Check if ALL drones are selected
            print("Moving backward for ALL drones (all selected)...")
            self.swarm.move_backward(10.0, units="cm", speed=1.0) # Move all drones
        elif num_selected_drones == 0: # Check if NO drones are selected
            print("No drones selected. Not moving backward.") # Do nothing - no movement
        else: # Some drones are selected (but not all)
            print(f"Moving backward for selected drones: {selected_drone_indices}")
            for index in selected_drone_indices:
                self.swarm.one_drone(index, "move_backward", 20.0, units="cm", speed=20.0) # Move only selected

    def left(self):
        if not self.hasGeneratedGrid:
            print("Please generate grid before running commands.")
            return None
        selected_drone_indices = []
        for index, drone in enumerate(self.droneIcons):
            if drone["selected"].get():
                selected_drone_indices.append(index)

        num_selected_drones = len(selected_drone_indices)

        if num_selected_drones == num_drones: # Check if ALL drones are selected
            print("Moving left for ALL drones (all selected)...")
            self.swarm.move_left(10.0, units="cm", speed=1.0) # Move all drones
        elif num_selected_drones == 0: # Check if NO drones are selected
            print("No drones selected. Not moving left.") # Do nothing - no movement
        else: # Some drones are selected (but not all)
            print(f"Moving left for selected drones: {selected_drone_indices}")
            for index in selected_drone_indices:
                self.swarm.one_drone(index, "move_left", 20.0, units="cm", speed=20.0) # Move only selected

    def right(self):
        if not self.hasGeneratedGrid:
            print("Please generate grid before running commands.")
            return None
        selected_drone_indices = []
        for index, drone in enumerate(self.droneIcons):
            if drone["selected"].get():
                selected_drone_indices.append(index)

        num_selected_drones = len(selected_drone_indices)

        if num_selected_drones == num_drones: # Check if ALL drones are selected
            print("Moving right for ALL drones (all selected)...")
            self.swarm.move_right(10.0, units="cm", speed=1.0) # Move all drones
        elif num_selected_drones == 0: # Check if NO drones are selected
            print("No drones selected. Not moving right.") # Do nothing - no movement
        else: # Some drones are selected (but not all)
            print(f"Moving right for selected drones: {selected_drone_indices}")
            for index in selected_drone_indices:
                self.swarm.one_drone(index, "move_right", 20.0, units="cm", speed=20.0) # Move only selected.

    def run_main_choreo(self):
        print("Running main choreography...")
        # import mainchoreo
        # mainchoreo.run_sequence(self.swarm)
    def run_hexagon(self):
        print("Running hexagon choreography...")
        # import hexagon
        # hexagon.run_sequence(self.swarm)
    def run_spiral_and_flip(self):
        print("Running spiral and flip choreography...")
        # import spiralandflip
        # spiralandflip.run_sequence(self.swarm)
    def run_upward_spiral(self):
        print("Running upward spiral choreography...")
        # import upwardspiral
        # upwardspiral.run_sequence(self.swarm)
    def run_wiggle(self):
        print("Running wiggle choreography...")
        # import wiggle
        # wiggle.run_sequence(self.swarm)

    def create_input_section(self):
        self.label_style = {
            'font': ('Helvetica', 10, 'bold'),
            'bg': self.light_blue,
            'fg': '#05001c'
        }
        self.entry_style = {
            'font': ('Helvetica', 10, 'bold'),
            'relief': 'solid',
            'bd': 1,
            'highlightthickness': 1,
            'highlightbackground': '#4169E1',
            'highlightcolor': '#4169E1',
            'bg': 'white'
        }
        self.button_style = {
            'font': ('Helvetica', 10, 'bold'),
            'bg': self.pink,
            'fg': '#fff',
            'relief': 'solid',
            'bd': 1,
            'width': 12,
            'height': 1,
            'cursor': "heart"
        }

        def on_button_enter(event):
            event.widget.config(bg=self.hover_purple)

        def on_button_leave(event):
            event.widget.config(bg=self.pink)

        # --- Input Section Frame with Border ---
        input_frame = tk.Frame(self.root, bg=self.light_blue, borderwidth=2, relief='solid', padx=10, pady=5) # Frame with border
        input_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=10) # row changed to 1 - below title

        tk.Label(input_frame, text="Rows:", **self.label_style).grid(row=0, column=0, padx=(0, 5), pady=5, sticky='e')
        self.rows_input = tk.Entry(input_frame, **self.entry_style, width=5)
        self.rows_input.grid(row=0, column=1, padx=(0, 10), pady=5, sticky='w')

        tk.Label(input_frame, text="Columns:", **self.label_style).grid(row=0, column=2, padx=(10, 5), pady=5, sticky='e')
        self.cols_input = tk.Entry(input_frame, **self.entry_style, width=5)
        self.cols_input.grid(row=0, column=3, padx=(0, 10), pady=5, sticky='w')

        self.generate_button = tk.Button(input_frame, text="Generate Grid", command=self.create_grid, **self.button_style)
        self.generate_button.grid(row=0, column=4, padx=(10, 0), pady=5)
        self.generate_button.bind("<Enter>", on_button_enter) # Hover effect for red buttons
        self.generate_button.bind("<Leave>", on_button_leave) # Hover effect for red buttons

    def stabilize_swarm(self):
        """
        Retrieves drone heights, calculates average, and commands drones to hover.
        """
        if not self.hasGeneratedGrid:
            print("Grid not generated, cannot auto-stabilize.")
            return

        # Find median height of selected drones
        selected_drone_indices = []
        pos = self.swarm.get_position_data()
        height = []
        for i in pos:
            height.append(i[3])
        for drone in self.droneIcons:
            if drone["selected"].get():
                selected_drone_indices.append(drone["drone_index"])

        height_list = []
        height_indices = []
        dropped = []
        for i in selected_drone_indices:
            if (height[i] == 0.0 or height[i] == 999.9):
                dropped.append(i)
            else:
                height_list.append(height[i])
                height_indices.append(i)

        height_list.sort()

        if not height_list:  # Check if height_list is empty
            print("No valid height data received from selected drones to calculate median.")
            return  # Exit if no valid height data

        mid_index = len(height_list) // 2
        median_height = (height_list[mid_index - 1] + height_list[mid_index]) / 2 if len(height_list) % 2 == 0 else \
            height_list[mid_index]

        print(f"Median height of selected drones: {median_height:.2f} cm")
        print(f"Dropped indices: {dropped}, Height list: {height_list}, Height Indices: {height_indices}")

        # Collect movement commands for all selected drones
        movement_commands = []
        delay_ms = 100  # Increased delay for stabilization
        for drone in self.droneIcons:
            if drone["selected"].get():
                current_height = height[drone["drone_index"]]
                positionZ_meters = median_height - current_height

                if drone["drone_index"] in height_indices:
                    if 0.05 <= abs(positionZ_meters):
                        movement_commands.append({
                            "drone_index": drone["drone_index"],
                            "positionZ_meters": positionZ_meters
                        })
                        # Print statement showing movement for each drone
                        print(
                            f"Drone {drone['drone_index']} (color: {self.default_colors[drone['drone_index']]}) will move by {positionZ_meters:.2f} meters vertically from a height of {height[drone["drone_index"]]}.")
                    else:
                        print(
                            f"Drone {drone['drone_index']} (color: {self.default_colors[drone['drone_index']]}) height difference ({positionZ_meters:.2f}m) below threshold of 0.05m. No movement commanded.")

        # Execute movement commands with delays
        for i, command in enumerate(movement_commands):
            idx = command["drone_index"]
            posZ = command["positionZ_meters"]
            self.swarm.one_drone(idx, "move_distance",0, 0, posZ, 0.25)
    def create_grid(self):
        global swarm_drones, num_drones, canvas, rows, cols
        self.root.geometry("390x690")
        self.hasGeneratedGrid = True
        # --- Disable Input and Button during grid generation ---
        self.generate_button.config(state="disabled")
        self.rows_input.config(state="disabled")
        self.cols_input.config(state="disabled")

        # --- Connect to Swarm and Get Drone Objects ---
        swarm_drones = self.swarm.get_drones()
        num_drones = len(swarm_drones)

        # --- Get Rows and Columns from Input ---
        rows = int(self.rows_input.get())
        cols = int(self.cols_input.get())

        # --- Clear Existing Canvas if Present ---
        if self.canvas:
            self.canvas.destroy()
        self.droneIcons.clear()

        # --- Define Canvas and Grid Parameters ---
        cell_width = 50
        cell_height = 50
        padding = 20
        canvas_width = cols * cell_width + 2 * padding
        canvas_height = rows * cell_height + 2 * padding

        # --- Create Canvas Widget ---
        self.canvas = tk.Canvas(self.root, width=canvas_width, height=canvas_height, bg="white")
        self.canvas.grid(row=3, column=0, columnspan=2, pady=10, sticky=tk.N + tk.S + tk.W + tk.E) # row changed to 3

        # --- Draw Grid Lines ---
        for i in range(rows + 1):
            self.canvas.create_line(padding, i * cell_height + padding,
                                  cols * cell_width + padding, i * cell_height + padding,
                                  fill=self.grid_line_color, width=1)
        for j in range(cols + 1):
            self.canvas.create_line(j * cell_width + padding, padding,
                                  j * cell_width + padding, rows * cell_height + padding,
                                  fill=self.grid_line_color, width=1)

        # --- Place Drone Icons on the Grid ---
        drones_placed = 0
        current_row = 0
        self.drone_checkboxes = []

        while drones_placed < num_drones and current_row < rows:
            for col in range(cols + 1):
                if drones_placed >= num_drones:
                    break

                # Calculate position for the drone icon
                x = col * cell_width + padding
                y = current_row * cell_height + padding
                checkbox_x_offset = 2
                checkbox_y_offset = -14

                # Determine drone color from default color list
                color_index = drones_placed % len(self.default_colors)
                color = self.default_colors[color_index]

                # Create oval for drone icon
                drone_oval = self.canvas.create_oval(x - 5, y - 5, x + 5, y + 5, fill=color)
                rgba_color = self.process_color(color)

                # Store drone information
                drone = {"color": rgba_color, "position": (x, y),
                         "oval": drone_oval, "drone_index": drones_placed,
                         "drone_obj": swarm_drones[drones_placed], "selected": tk.BooleanVar(value=True)}
                self.swarm.one_drone(drone["drone_index"], "set_drone_LED",*rgba_color)
                self.droneIcons.append(drone)

                # Create Checkbutton for drone selection
                drone_checkbox = tk.Checkbutton(
                    self.canvas,
                    text=drone["drone_index"],  # No text for checkbox itself
                    variable=drone["selected"],  # Link to drone's 'selected' state
                    bg="white",  # Match canvas background
                    highlightbackground="white",  # Remove highlight border
                    highlightcolor="white",
                    bd=0,  # Remove default border
                    onvalue=True,
                    offvalue=False
                )
                self.drone_checkboxes.append(drone_checkbox)  # Store checkbox reference

                # Place Checkbutton on canvas, to the right of the icon
                self.canvas.create_window(x + checkbox_x_offset, y + checkbox_y_offset, window=drone_checkbox)

                # Bind click event to drone icon for color picking
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
        self.root.focus_set()

    def run(self):
        self.root.mainloop()

app = SwarmGUI()
app.run()

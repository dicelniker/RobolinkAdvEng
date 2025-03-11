import math
import tkinter as tk
from tkinter import colorchooser

import matplotlib.colors as mcolors
from codrone_edu.swarm import *


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

        # Create a main container frame to organize the layout
        self.main_container = tk.Frame(self.root, bg='#05001c')
        self.main_container.pack(expand=True, fill='both', padx=10, pady=10)

        # Create left frame for controls
        self.left_frame = tk.Frame(self.main_container, bg='#05001c')
        self.left_frame.pack(side='left', fill='y', padx=(0, 10))

        # Create right frame for the graph
        self.right_frame = tk.Frame(self.main_container, bg='#05001c')
        self.right_frame.pack(side='left', expand=True, fill='both')

        # Title Label (in left frame)
        title_label = tk.Label(
            self.left_frame,
            text="CoDrone EDU - Swarm",
            font=('Terminal', 18, 'bold'),
            bg=self.dark_blue,
            fg=self.light_blue,
            pady=10
        )
        title_label.pack(pady=(0, 10))

        self.create_input_section()
        self.create_control_buttons()
        self.default_colors = ['red', 'blue', 'orange', 'yellow', 'green', 'light blue', 'purple', 'pink', 'white', 'black']
        self.bind_keys()
        self.root.geometry("400x690")
        self.create_grid()

    def process_color(self, color_str):
        rgba_color = list(mcolors.to_rgba(color_str))
        for i in range(4):
            rgba_color[i] = int(255 * rgba_color[i])
        return rgba_color
    #
    # def open_color_picker(self, drone):
    #     color_code = colorchooser.askcolor(title="Choose Drone Color")
    #     if color_code[1]:
    #         new_color = color_code[1]
    #         rgb_value = color_code[0]
    #         print(f"Selected RGB color: {rgb_value}")
    #         drone["color"] = new_color
    #         rgba_color = self.process_color(drone["color"])
    #         self.swarm.one_drone(drone["drone_index"], "set_drone_LED", *rgba_color)
    #         self.swarm.one_drone(drone["drone_index"], "set_controller_LED", *rgba_color)
    #         self.canvas.itemconfig(drone["oval"], fill=new_color)

    def create_control_buttons(self):
        button_style = {
            'font': ('Helvetica', 10, 'bold'),
            'bg': self.pink,
            'fg': '#fff',
            'relief': 'solid',
            'bd': 1,
            'width': 15,
            'height': 1,
            'cursor': "hand2"
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
            'borderwidth': 0,
            'cursor': 'hand2'
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
        left_control_frame = tk.Frame(self.left_frame, borderwidth=2, relief='solid', padx=5, pady=5,
                                      highlightbackground=self.light_blue, highlightcolor=self.light_blue)
        left_control_frame.pack(fill='x', pady=10)

        take_off_button = tk.Button(left_control_frame, text="Take Off", command=self.take_off, **button_style)
        take_off_button.pack(pady=5)
        take_off_button.bind("<Enter>", on_button_enter) # Hover effect for red buttons
        take_off_button.bind("<Leave>", on_button_leave) # Hover effect for red buttons

        land_button = tk.Button(left_control_frame, text="Land", command=self.land, **button_style)
        land_button.pack(pady=15)
        land_button.bind("<Enter>", on_button_enter) # Hover effect for red buttons
        land_button.bind("<Leave>", on_button_leave) # Hover effect for red buttons

        # --- Other Buttons ---
        stabilize_button = tk.Button(left_control_frame, text="Stabilize Swarm",
                                           command=self.stabilize_swarm, **button_style)
        stabilize_button.pack(pady=15)  # Adjust pady as needed
        stabilize_button.bind("<Enter>", on_button_enter)
        stabilize_button.bind("<Leave>", on_button_leave)

        # stabilize_button = tk.Button(left_control_frame, text="Update Positions",
        #                              command=self.update_timer, **button_style)
        # stabilize_button.pack(pady=15)  # Adjust pady as needed
        # stabilize_button.bind("<Enter>", on_button_enter)
        # stabilize_button.bind("<Leave>", on_button_leave)

        # --- Right Section (Sequences) with Border ---
        right_control_frame = tk.Frame(self.left_frame, bg=self.dark_blue, borderwidth=2, relief='solid',
                                       padx=5, pady=5, highlightbackground=self.light_blue,
                                       highlightcolor=self.light_blue)
        right_control_frame.pack(fill='x', pady=10)

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
        movement_frame = tk.Frame(self.left_frame, bg='#05001c')
        movement_frame.pack(pady=10)

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
            self.swarm.all_drones("takeoff")  # Take off all drones (already synchronized)
        elif num_selected_drones > 0:
            print(f"Taking off selected drones (synchronized): {selected_drone_indices}")
            sync_takeoff = Sync() # Create a Sync object
            for index in selected_drone_indices:
                seq = Sequence(index) # Create a Sequence for each selected drone, initialize with index
                seq.add("takeoff") # Add the takeoff action to the sequence using Sequence.add
                sync_takeoff.add(seq) # Add sequence to Sync object using Sync.add
            self.swarm.run(sync_takeoff, type="parallel") # Run synchronized takeoff for selected drones
        else:
            print("No drones selected. Not taking off.")

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
            self.swarm.all_drones("land")  # Land all drones (already synchronized)
        elif num_selected_drones > 0:
            print(f"Landing selected drones (synchronized): {selected_drone_indices}")
            sync_land = Sync() # Create a Sync object
            for index in selected_drone_indices:
                seq = Sequence(index) # Create a Sequence for each selected drone, initialize with index
                seq.add("land") # Add the land action to the sequence using Sequence.add
                sync_land.add(seq) # Add sequence to Sync object using Sync.add
            self.swarm.run(sync_land, type="parallel") # Run synchronized land for selected drones
        else:
            print("No drones selected. Not landing.")

    def forward(self):
        if not self.hasGeneratedGrid:
            print("Please generate grid before running commands.")
            return None
        selected_drone_indices = []
        for index, drone in enumerate(self.droneIcons):
            if drone["selected"].get():
                selected_drone_indices.append(index)

        num_selected_drones = len(selected_drone_indices)

        if num_selected_drones > 0:
            print(f"Moving forward for selected drones: {selected_drone_indices}")
            sync_forward = Sync()
            for index in selected_drone_indices:
                seq = Sequence(index)
                seq.add("move_distance", 0.2, 0, 0, 0.5)
                sync_forward.add(seq)

                # Update displayed position
                drone = self.droneIcons[index]
                new_x = drone["x_position"] + 0.2  # Add 0.2m to x position
                self.set_drone_position(index, new_x, drone["y_position"], drone["z_position"])

            self.swarm.run(sync_forward, type="parallel")
        else:
            print("No drones selected. Not moving forward.")

    def backward(self):
        if not self.hasGeneratedGrid:
            print("Please generate grid before running commands.")
            return None
        selected_drone_indices = []
        for index, drone in enumerate(self.droneIcons):
            if drone["selected"].get():
                selected_drone_indices.append(index)

        num_selected_drones = len(selected_drone_indices)

        if num_selected_drones > 0:
            print(f"Moving backward for selected drones: {selected_drone_indices}")
            sync_backward = Sync()
            for index in selected_drone_indices:
                seq = Sequence(index)
                seq.add("move_distance", -0.2, 0, 0, 0.5)
                sync_backward.add(seq)

                # Update displayed position
                drone = self.droneIcons[index]
                new_x = drone["x_position"] - 0.2  # Subtract 0.2m from x position
                self.set_drone_position(index, new_x, drone["y_position"], drone["z_position"])

            self.swarm.run(sync_backward, type="parallel")
        else:
            print("No drones selected. Not moving backward.")

    def left(self):
        if not self.hasGeneratedGrid:
            print("Please generate grid before running commands.")
            return None
        selected_drone_indices = []
        for index, drone in enumerate(self.droneIcons):
            if drone["selected"].get():
                selected_drone_indices.append(index)

        num_selected_drones = len(selected_drone_indices)

        if num_selected_drones > 0:
            print(f"Moving left for selected drones: {selected_drone_indices}")
            sync_left = Sync()
            for index in selected_drone_indices:
                seq = Sequence(index)
                seq.add("move_distance", 0, 0.2, 0, 0.5)
                sync_left.add(seq)

                # Update displayed position
                drone = self.droneIcons[index]
                new_y = drone["y_position"] + 0.2  # Add 0.2m to y position
                self.set_drone_position(index, drone["x_position"], new_y, drone["z_position"])

            self.swarm.run(sync_left, type="parallel")
        else:
            print("No drones selected. Not moving left.")

    def right(self):
        if not self.hasGeneratedGrid:
            print("Please generate grid before running commands.")
            return None
        selected_drone_indices = []
        for index, drone in enumerate(self.droneIcons):
            if drone["selected"].get():
                selected_drone_indices.append(index)

        num_selected_drones = len(selected_drone_indices)

        if num_selected_drones > 0:
            print(f"Moving right for selected drones: {selected_drone_indices}")
            sync_right = Sync()
            for index in selected_drone_indices:
                seq = Sequence(index)
                seq.add("move_distance", 0, -0.2, 0, 0.5)
                sync_right.add(seq)

                # Update displayed position
                drone = self.droneIcons[index]
                new_y = drone["y_position"] - 0.2  # Subtract 0.2m from y position
                self.set_drone_position(index, drone["x_position"], new_y, drone["z_position"])

            self.swarm.run(sync_right, type="parallel")
        else:
            print("No drones selected. Not moving right.")

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
        if not self.hasGeneratedGrid:
            print("Please generate grid before running commands.")
            return None
        selected_drone_indices = []
        for index, drone in enumerate(self.droneIcons):
            if drone["selected"].get():
                selected_drone_indices.append(index)

        num_selected_drones = len(selected_drone_indices)

        if num_selected_drones > 0:
            print(f"Running upward spiral for the following drones: {selected_drone_indices}")
            sync_right = Sync()  # Create a Sync object
            for index in selected_drone_indices:
                seq = Sequence(index)  # Create a Sequence for each selected drone
                seq.add("go", 0, 0, 25, 10, 5)
                sync_right.add(seq)  # Add sequence to Sync object
            self.swarm.run(sync_right, type="parallel")  # Run synchronized right movement for selected drones
        else:  # Check if NO drones are selected
            print("No drones selected. Not moving right.")  # Do nothing - no movement
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
            'cursor': "hand2"
        }

        def on_button_enter(event):
            event.widget.config(bg=self.hover_purple)

        def on_button_leave(event):
            event.widget.config(bg=self.pink)

        # Create input frame in left frame
        input_frame = tk.Frame(self.left_frame, bg=self.light_blue, borderwidth=2, relief='solid', padx=10, pady=5)
        input_frame.pack(fill='x', pady=10)

        # Grid layout for input elements
        input_grid = tk.Frame(input_frame, bg=self.light_blue)
        input_grid.pack(pady=5)

        tk.Label(input_grid, text="#:", **self.label_style).grid(row=0, column=0, padx=(0, 5), pady=5)
        self.drone_index_input = tk.Entry(input_grid, **self.entry_style, width=3)
        self.drone_index_input.grid(row=0, column=1, padx=(0, 10), pady=5)

        tk.Label(input_grid, text="X:", **self.label_style).grid(row=0, column=2, padx=(10, 5), pady=5)
        self.x_coord_input = tk.Entry(input_grid, **self.entry_style, width=3)
        self.x_coord_input.grid(row=0, column=3, padx=(0, 10), pady=5)

        tk.Label(input_grid, text="Y:", **self.label_style).grid(row=0, column=4, padx=(10, 5), pady=5)
        self.y_coord_input = tk.Entry(input_grid, **self.entry_style, width=3)
        self.y_coord_input.grid(row=0, column=5, padx=(0, 10), pady=5)

        tk.Label(input_grid, text="Z:", **self.label_style).grid(row=0, column=6, padx=(10, 5), pady=5)
        self.z_coord_input = tk.Entry(input_grid, **self.entry_style, width=3)
        self.z_coord_input.grid(row=0, column=7, padx=(0, 10), pady=5)

        self.set_coords_button = tk.Button(
            input_grid,
            text="Set Coords",
            command=lambda: self.set_drone_position(
                int(self.drone_index_input.get()),
                float(self.x_coord_input.get()),
                float(self.y_coord_input.get()),
                float(self.z_coord_input.get())
            ),
            **self.button_style
        )
        self.set_coords_button.grid(row=0, column=8, padx=(10, 0), pady=5)
        self.set_coords_button.bind("<Enter>", on_button_enter) # Hover effect for red buttons
        self.set_coords_button.bind("<Leave>", on_button_leave) # Hover effect for red buttons

    def stabilize_swarm(self):
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

        # Create Sync and Sequence objects for synchronized movement
        sync_stabilize = Sync()
        movement_commanded = False  # Flag to track if any movement commands were added

        for drone in self.droneIcons:
            if drone["selected"].get():
                current_height = height[drone["drone_index"]]
                positionZ_meters = median_height - current_height

                if drone["drone_index"] in height_indices:
                    if 0.05 <= abs(positionZ_meters):
                        seq = Sequence(drone["drone_index"])  # Create sequence for this drone
                        seq.add("move_distance", 0, 0, positionZ_meters, 0.25)  # Add move_distance command to sequence
                        sync_stabilize.add(seq)  # Add sequence to Sync object
                        movement_commanded = True  # Set flag as movement command is added
                        # Print statement showing movement for each drone
                        print(
                            f"Drone {drone['drone_index']} (color: {self.default_colors[drone['drone_index']]}) will move by {positionZ_meters:.2f} meters vertically from a height of {height[drone['drone_index']]}.")
                    else:
                        print(
                            f"Drone {drone['drone_index']} (color: {self.default_colors[drone['drone_index']]}) height difference ({positionZ_meters:.2f}m) below threshold of 0.05m. No movement commanded.")

        # Execute synchronized movement if any movement commands were added
        if movement_commanded:
            self.swarm.run(sync_stabilize, type="parallel")
        else:
            print("No drones needed to move for stabilization.")

    # not working
    # def update_timer(self):
    #     self.update_graph()
    #     self.root.after(5000, self.update_timer)
    #
    # def update_graph(self):
    #     data = self.swarm.get_position_data()
    #     for i in range(len(self.droneIcons)):
    #         pos = data[i]
    #         x_coord = pos[1]
    #         y_coord = pos[2]
    #         z_coord = pos[3]
    #         self.set_drone_position(i, x_coord, y_coord, z_coord)

    def set_drone_position(self, drone_index, x_coord, y_coord, z_coord):
        if 0 <= drone_index < len(self.droneIcons):
            drone = self.droneIcons[drone_index]
            drone["x_position"] = x_coord
            drone["y_position"] = y_coord
            drone["z_position"] = z_coord

            if drone["plot"] is not None:
                drone["plot"].set_offsets([[x_coord, y_coord]])
            else:
                drone["plot"] = self.ax.scatter(x_coord, y_coord, color=self.default_colors[drone_index], s=100)

            if drone["annotation"] is not None:
                drone["annotation"].set_position((x_coord, y_coord))
                drone["annotation"].set_text(f'Drone {drone_index}\n({x_coord:.1f}, {y_coord:.1f}, {z_coord: .1f})')
            else:
                drone["annotation"] = self.ax.annotate(
                    f'Drone {drone_index}\n({x_coord:.1f}, {y_coord:.1f}, {z_coord: .1f})',
                    (x_coord, y_coord),
                    xytext=(0, 10),
                    textcoords='offset points',
                    ha='center',
                    bbox=dict(boxstyle='round,pad=0.5', fc='white', alpha=0.7),
                    fontsize=8
                )

            self.canvas_widget.draw()
            print(f"Drone {drone_index} position set to ({x_coord:.1f}, {y_coord:.1f}, {z_coord:.1f})")
        else:
            print("Invalid drone index")

    def create_grid(self):
        global swarm_drones, num_drones, rows, cols
        self.root.geometry("1200x800")  # Increased width for better visualization
        self.hasGeneratedGrid = True

        # Connect to Swarm and Get Drone Objects
        swarm_drones = self.swarm.get_drones()
        num_drones = len(swarm_drones)

        # Clear Existing Canvas if Present
        if hasattr(self, 'canvas_widget'):
            self.canvas_widget.destroy()

        # Import required matplotlib modules
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        from matplotlib.figure import Figure

        # Create Figure and Axes
        self.fig = Figure(figsize=(6, 6))
        self.ax = self.fig.add_subplot(111)

        # Configure the plot
        self.ax.grid(True, linestyle='--', alpha=0.7)
        self.ax.set_xlim(-2, 2)
        self.ax.set_ylim(-2, 2)
        self.ax.set_xlabel('X (m)')
        self.ax.set_ylabel('Y (m)')
        self.ax.set_title('Drone Positions')

        # Make the plot background match the GUI
        self.fig.patch.set_facecolor('#05001c')
        self.ax.set_facecolor('white')

        # Add the plot to Tkinter
        self.canvas_widget = FigureCanvasTkAgg(self.fig, master=self.right_frame)
        self.canvas_widget.draw()
        self.canvas_widget.get_tk_widget().pack(expand=True, fill='both', padx=10, pady=10)

        # Store drone positions and plot elements
        self.drone_plots = []
        self.drone_annotations = []
        self.droneIcons = []

        # Place Drone Icons on the Grid
        for i in range(num_drones):
            # Default position for the first drone
            if i == 0:
                x_pos, y_pos, z_pos = 0.0, 0.0, 0.0
            else:
                # Set default position for other drones
                x_pos, y_pos, z_pos = None, None, None

            # Get color for the drone
            color_index = i % len(self.default_colors)
            color = self.default_colors[color_index]
            rgba_color = self.process_color(color)

            # Plot drone position
            if x_pos is not None and y_pos is not None:
                drone_plot = self.ax.scatter(x_pos, y_pos, color=color, s=100)
            else:
                drone_plot = None
            self.drone_plots.append(drone_plot)

            # Add drone index and position annotation
            if x_pos is not None and y_pos is not None:
                annotation = self.ax.annotate(
                    f'Drone {i}\n({x_pos:.1f}, {y_pos:.1f}, {z_pos: .1f})',
                    (x_pos, y_pos),
                    xytext=(0, 10),
                    textcoords='offset points',
                    ha='center',
                    bbox=dict(boxstyle='round,pad=0.5', fc='white', alpha=0.7),
                    fontsize=8
                )
            else:
                annotation = None
            self.drone_annotations.append(annotation)

            # Store drone information
            drone = {
                "color": rgba_color,
                "x_position": x_pos,
                "y_position": y_pos,
                "z_position": z_pos,
                "x_offset": x_pos,
                "y_offset": y_pos,
                "plot": drone_plot,
                "annotation": annotation,
                "drone_index": i,
                "drone_obj": swarm_drones[i],
                "selected": tk.BooleanVar(value=True)
            }
            self.droneIcons.append(drone)

            # Create Checkbutton frame for drone selection
            check_frame = tk.Frame(self.left_frame, bg=self.dark_blue)
            check_frame.pack(pady=2)

            drone_checkbox = tk.Checkbutton(
                check_frame,
                text=f"Drone {i}",
                variable=drone["selected"],
                bg=self.dark_blue,
                fg=color,
                selectcolor=self.dark_blue,
                activebackground=self.dark_blue,
                activeforeground=color
            )
            drone_checkbox.pack(side='left')

            # Set drone LED color
            self.swarm.one_drone(drone["drone_index"], "set_drone_LED", *rgba_color)

        # Draw the plot
        self.canvas_widget.draw()

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

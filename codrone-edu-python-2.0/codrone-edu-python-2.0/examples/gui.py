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

        self.label_style = {
            'font': ('Helvetica', 10, 'bold'),
            'bg': '#3fd4ff',  # light blue
            'fg': '#05001c'  # dark blue
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
            'bg': '#e61848',  # pink
            'fg': '#fff',
            'relief': 'solid',
            'bd': 1,
            'width': 12,
            'height': 1,
            'cursor': "hand2"
        }

        self.droneIcons = []
        self.swarm = Swarm()
        self.swarm.connect()

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
        self.default_colors = ['red', 'blue', 'orange', 'yellow', 'green', '#00ffff', 'purple', 'pink', 'white', 'black']
        # self.bind_keys()
        self.root.geometry("400x690")
        self.create_grid()
        self.is_landed = {i: True for i in range(len(self.swarm.get_drones()))}

# Helper function for clicks on the graph
    def handle_press(self, event):
        """Handle initial click for drag or color picker"""
        if event.inaxes != self.ax:
            return

        click_x, click_y = event.xdata, event.ydata

        for drone in self.droneIcons:
            if drone["plot"] is not None:
                drone_x = drone["x_position"]
                drone_y = drone["y_position"]

                distance = math.sqrt((click_x - drone_x) ** 2 + (click_y - drone_y) ** 2)

                if distance < 0.2:  # Click threshold
                    if event.button == 1:  # Left click for dragging
                        self.selected_drone = drone
                    elif event.button == 3:  # Right click for color picker
                        self.open_color_picker(drone)
                    break

# Color picker functions
    def process_color(self, color_str):
        rgba_color = list(mcolors.to_rgba(color_str))
        for i in range(4):
            rgba_color[i] = int(255 * rgba_color[i])
        return rgba_color

    def open_color_picker(self, drone):
        """Open color picker and update drone color"""
        color_code = colorchooser.askcolor(title="Choose Drone Color")
        if color_code[1]:
            new_color = color_code[1]
            rgb_value = color_code[0]
            print(f"Selected RGB color: {rgb_value}")

            # Update the stored color
            drone["color"] = new_color

            # Update the LED color on the physical drone
            rgba_color = self.process_color(drone["color"])
            self.swarm.one_drone(drone["drone_index"], "set_drone_LED", *rgba_color)
            self.swarm.one_drone(drone["drone_index"], "set_controller_LED", *rgba_color)

            # Update the plot color
            if drone["plot"] is not None:
                drone["plot"].set_color(new_color)

                # Force a redraw of the plot
                self.canvas_widget.draw()

# Drag and drop functionality
    def setup_click_handlers(self):
        """Set up click and drag handlers"""
        self.selected_drone = None
        self.canvas_widget.mpl_connect('button_press_event', self.handle_press)
        self.canvas_widget.mpl_connect('button_release_event', self.handle_release)

    def handle_release(self, event):
        """Handle drag release to set final position"""
        if self.selected_drone is None or event.inaxes != self.ax:
            self.selected_drone = None
            return

        # Send drone to the release position
        self.goto_position(
            self.selected_drone["drone_index"],
            event.xdata,
            event.ydata,
            self.selected_drone["z_position"],
            speed=0.5
        )

        # Clear selection
        self.selected_drone = None

# Helper functions for setup
    def get_indices(self):
        selected_drone_indices = []
        for index, drone in enumerate(self.droneIcons):
            if drone["selected"].get():
                selected_drone_indices.append(index)
        return selected_drone_indices

    def get_coords(self, droneidx):
        """Get the [x, y, z] coordinates of the drone at the given index"""
        return [
            self.droneIcons[droneidx]["x_position"],
            self.droneIcons[droneidx]["y_position"],
            self.droneIcons[droneidx]["z_position"]
        ]

    def create_button(self, parent, text, command, style, bind_hover=True):
        """Helper method to create buttons with consistent styling"""
        button = tk.Button(parent, text=text, command=command, **style)
        if bind_hover:
            button.bind("<Enter>", lambda e: e.widget.config(bg=self.hover_purple))
            button.bind("<Leave>", lambda e: e.widget.config(bg=self.pink))
        return button

    def create_border_frame(self, parent, style):
        """Helper method to create border frames with consistent styling"""
        return tk.Frame(parent, **style)


    def move_drones(self, direction, x=0.0, y=0.0, z=0.0, speed=0.5):
        """Generic method for drone movement"""
        selected_drone_indices = self.get_indices()
        if not selected_drone_indices:
            print(f"No drones selected. Not moving {direction}.")
            return

        print(f"Moving {direction} for selected drones: {selected_drone_indices}")
        sync_move = Sync()
        for index in selected_drone_indices:
            seq = Sequence(index)
            seq.add("move_distance", x, y, z, speed)
            sync_move.add(seq)
        self.swarm.run(sync_move, type="parallel")



    def create_control_buttons(self):
        # Define styles
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
            'bg': '#05001c',
            'fg': 'white',
            'relief': 'solid',
            'padx': 3,
            'pady': 3,
            'width': 2,
            'height': 1,
            'foreground': '#e61848',
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

        # Helper functions for button effects
        def highlight_button(border_frame, button):
            border_frame.config(highlightbackground='#3fd4ff', highlightcolor='#3fd4ff')
            button.config(bg='white', fg='#3fd4ff')

        def reset_button(border_frame, button):
            border_frame.config(highlightbackground='#e61848', highlightcolor='#e61848')
            button.config(bg='#05001c', fg='white')

        def on_arrow_button_enter(event):
            event.widget.config(bg=self.arrow_hover_blue)

        def on_arrow_button_leave(event):
            event.widget.config(bg='#05001c')

        # Create main control frame
        left_control_frame = self.create_border_frame(
            self.left_frame,
            {
                'borderwidth': 2,
                'relief': 'solid',
                'padx': 5,
                'pady': 5,
                'highlightbackground': self.light_blue,
                'highlightcolor': self.light_blue
            }
        )
        left_control_frame.pack(fill='x', pady=10)

        # Create main control buttons
        main_buttons = [
            ("Take Off", self.take_off),
            ("Land", self.land),
            ("Stabilize Swarm", self.stabilize_swarm),
            ("Auto Update", self.update_timer)
        ]

        for text, command in main_buttons:
            self.create_button(left_control_frame, text, command, button_style).pack(pady=5)

        # Create choreography section
        right_control_frame = self.create_border_frame(
            self.left_frame,
            {
                'bg': self.dark_blue,
                'relief': 'solid',
                'padx': 5,
                'pady': 5,
                'highlightbackground': self.light_blue,
                'highlightcolor': self.light_blue
            }
        )
        right_control_frame.pack(fill='x', pady=10)

        tk.Label(
            right_control_frame,
            text="Sequences:",
            font=("Helvetica", 10, "bold"),
            bg=self.dark_blue,
            fg=self.light_blue
        ).pack()

        choreo_frame = tk.Frame(right_control_frame, bg=self.dark_blue)
        choreo_frame.pack(pady=10)

        # Create choreography buttons
        choreo_buttons = [
            ("Main Choreo", self.run_main_choreo),
            ("Hexagon", self.run_hexagon),
            ("Spiral and Flip", self.run_spiral_and_flip),
            ("Upward Spiral", self.run_spiral),
            ("Wiggle", self.run_wiggle)
        ]

        for text, command in choreo_buttons:
            self.create_button(choreo_frame, text, command, button_style).pack(pady=3)

        # Create movement controls
        movement_frame = tk.Frame(self.left_frame, bg='#05001c')
        movement_frame.pack(pady=10)

        # Create movement buttons with borders
        movement_controls = [
            ('forward', '↑', (0, 1), lambda: self.forward()),
            ('backward', '↓', (1, 1), lambda: self.backward()),
            ('left', '←', (1, 0), lambda: self.left()),
            ('right', '→', (1, 2), lambda: self.right())
        ]

        for name, symbol, (row, col), command in movement_controls:
            # Create border frame
            border = self.create_border_frame(movement_frame, pink_border_style)
            setattr(self, f"{name}_border", border)

            # Create button
            button = tk.Button(
                border,
                text=symbol,
                command=lambda b=border, btn=f"{name}_button", cmd=command:
                [cmd(), highlight_button(b, getattr(self, btn)),
                 self.root.after(100, lambda: reset_button(b, getattr(self, btn)))],
                **movement_button_style
            )
            button.pack(in_=border)
            button.config(fg='white')
            button.bind("<Enter>", on_arrow_button_enter)
            button.bind("<Leave>", on_arrow_button_leave)
            setattr(self, f"{name}_button", button)

            # Position the button
            border.grid(row=row, column=col, padx=5, pady=5)

    def goto_position(self, drone_index, target_x, target_y, target_z, speed=0.5):
        """
        Move a drone to a specific position on both the graph and in the physical world.

        Parameters:
        - drone_index: Index of the drone to move
        - target_x: Target X coordinate on the graph
        - target_y: Target Y coordinate on the graph
        - target_z: Target Z coordinate (height)
        - speed: Movement speed (default 0.5 m/s)
        """
        if not (0 <= drone_index < len(self.droneIcons)):
            print(f"Invalid drone index: {drone_index}")
            return

        drone = self.droneIcons[drone_index]

        # Get current position
        current_x = drone["x_position"] if drone["x_position"] is not None else 0
        current_y = drone["y_position"] if drone["y_position"] is not None else 0
        current_z = drone["z_position"] if drone["z_position"] is not None else 0

        # Calculate relative movement needed
        # Subtract the offsets because sendControlPosition is relative to drone's own coordinate system
        final_x = target_x - (drone["x_offset"] if drone["x_offset"] is not None else 0)
        final_y = target_y - (drone["y_offset"] if drone["y_offset"] is not None else 0)
        final_z = target_z

        print(f"Moving drone {drone_index} to position ({target_x:.2f}, {target_y:.2f}, {target_z:.2f})")
        print(f"Current position: ({current_x:.2f}, {current_y:.2f}, {current_z:.2f})")

        placeholder = drone["drone_obj"]

        # Check if the platform is Emscripten or the swarm is connected
        if sys.platform != 'emscripten' and not self.swarm:
            # Synchronous call for desktop environment
            placeholder.send_absolute_position(final_x, final_y, final_z, speed, 0, 0)
        else:
            # Asynchronous call for Emscripten environment
            async def move_drone():
                await placeholder.send_absolute_position(final_x, final_y, final_z, speed, 0, 0)

            # Execute the coroutine in a blocking manner
            asyncio.run(move_drone())

    def land(self):
        selected_drone_indices = self.get_indices()
        num_selected_drones = len(selected_drone_indices)

        if num_selected_drones == num_drones:
            print("Landing ALL drones (all selected)...")
            self.swarm.all_drones("land")
            for i in range(num_drones):
                self.is_landed[i] = True
            self.reset_offsets()
        elif num_selected_drones > 0:
            print(f"Landing selected drones (synchronized): {selected_drone_indices}")
            sync_land = Sync()
            for index in selected_drone_indices:
                seq = Sequence(index)
                seq.add("land")
                sync_land.add(seq)
                self.is_landed[index] = True
            self.swarm.run(sync_land, type="parallel")
            self.reset_offsets()
        else:
            print("No drones selected. Not landing.")

    def take_off(self):
        selected_drone_indices = self.get_indices()
        num_selected_drones = len(selected_drone_indices)

        if num_selected_drones == num_drones:
            print("Taking off ALL drones (all selected)...")
            self.swarm.all_drones("takeoff")
            for i in range(num_drones):
                self.is_landed[i] = False
        elif num_selected_drones > 0:
            print(f"Taking off selected drones (synchronized): {selected_drone_indices}")
            sync_takeoff = Sync()
            for index in selected_drone_indices:
                seq = Sequence(index)
                seq.add("takeoff")
                sync_takeoff.add(seq)
                self.is_landed[index] = False
            self.swarm.run(sync_takeoff, type="parallel")
        else:
            print("No drones selected. Not taking off.")

    def forward(self):
        self.move_drones("forward", x=0.2)

    def backward(self):
        self.move_drones("backward", x=-0.2)

    def left(self):
        self.move_drones("left", y=0.2)

    def right(self):
        self.move_drones("right", y=-0.2)

    def run_main_choreo(self):
        from mainChoreography import MainChoreo
        run = MainChoreo(self)
        selected_drone_indices = self.get_indices()
        if not selected_drone_indices:
            print(f"No drones selected. Not running main choreo sequence.")
            return

        print(f"Running main choreo sequence for the following drones: {selected_drone_indices}")
        run.run_sequence(self.swarm, selected_drone_indices)

    def run_hexagon(self):
        from hexagon import Hexagon
        runHexagonChoreo = Hexagon()
        selected_drone_indices = self.get_indices()
        if not selected_drone_indices:
            print(f"No drones selected. Not running hexagon sequence.")
            return

        print(f"Running hexagon sequence for the following drones: {selected_drone_indices}")
        self.take_off()
        runHexagonChoreo.run_sequence(self.swarm, selected_drone_indices)

    def run_spiral_and_flip(self):
        print("run spiral and flip")
            #self.run_choreography("spiral and flip choreography", spiralandflip.run_sequence)

    def run_wiggle(self):
        self.take_off()
        selected_drone_indices = self.get_indices()
        test = [
            (0.5, 0.5, 1),  # Front Left
            (-0.5, -0.5, 1),  # Front Right
        ]
        for i, drone_index in enumerate(selected_drone_indices):
            pos = test[i]
            self.goto_position(drone_index, pos[0], pos[1], pos[2], 1)
    def run_spiral(self):
        selected_drone_indices = self.get_indices()
        num_selected_drones = len(selected_drone_indices)

        if num_selected_drones > 0:
            print(f"Running upward spiral for the following drones: {selected_drone_indices}")
            sync_right = Sync()  # Create a Sync object
            for index in selected_drone_indices:
                seq = Sequence(index)  # Create a Sequence for each selected drone
                seq.add("go", 0, 0, 25, 20, 5)
                sync_right.add(seq)  # Add sequence to Sync object
            self.swarm.run(sync_right, type="parallel")  # Run synchronized right movement for selected drones
        else:  # Check if NO drones are selected
            print("No drones selected. Not moving right.")  # Do nothing - no movement

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
        self.set_coords_button.bind("<Enter>", on_button_enter)  # Hover effect for red buttons
        self.set_coords_button.bind("<Leave>", on_button_leave)  # Hover effect for red buttons

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
    def update_timer(self):
        self.update_graph()
        self.root.after(100, self.update_timer)

    def update_graph(self):
        data = self.swarm.get_position_data()
        for i in range(len(self.droneIcons)):
            pos = data[i]
            drone = self.droneIcons[i]

            # Skip position updates if drone is landed
            if self.is_landed[i]:
                self.set_drone_position(i, drone["x_offset"], drone["y_offset"], 0)
                continue

            # Get raw coordinates from position data
            x_coord = pos[1]
            y_coord = pos[2]
            z_coord = pos[3]

            # Skip invalid readings
            if x_coord == 999.9 or y_coord == 999.9 or z_coord == 999.9:
                continue

            # Add the stored offsets to the coordinates
            adjusted_x = x_coord + drone["x_offset"] if drone["x_offset"] is not None else x_coord
            adjusted_y = y_coord + drone["y_offset"] if drone["y_offset"] is not None else y_coord

            # Update position with adjusted coordinates
            self.set_drone_position(i, adjusted_x, adjusted_y, z_coord)

# Should run when the drones are landed
    def reset_offsets(self):
        selected_drone_indices = self.get_indices()
        num_selected_drones = len(selected_drone_indices)

        for i in range(num_selected_drones):
            drone = self.droneIcons[i]
            drone["x_offset"] = drone["x_position"]
            drone["y_offset"] = drone["y_position"]
            # print(f"Saving offsets for drone {i}, x: {drone["x_offset"]:.1f}, y: {drone["y_offset"]:.1f}")

    def set_drone_position(self, drone_index, x_coord, y_coord, z_coord):
        if not (0 <= drone_index < len(self.droneIcons)):
            print(f"Invalid drone index: {drone_index}")
            return

        drone = self.droneIcons[drone_index]

        # If this is the first position set for this drone (initial position is None)
        if drone["x_position"] is None and drone["y_position"] is None:
            drone["x_offset"] = x_coord
            drone["y_offset"] = y_coord
            # print(f"Initial offset set for Drone {drone_index}: ({x_coord:.1f}, {y_coord:.1f})")

        # Update stored positions
        drone["x_position"] = x_coord
        drone["y_position"] = y_coord
        drone["z_position"] = z_coord

        # First remove existing annotation if it exists
        if drone["annotation"] is not None:
            drone["annotation"].remove()

        # Create new annotation
        drone["annotation"] = self.ax.annotate(
            f'Drone {drone_index}\n({x_coord:.1f}, {y_coord:.1f}, {z_coord:.1f})',
            xy=(x_coord, y_coord),  # Point to annotate
            xytext=(0, 15),  # Offset text by 15 points above
            textcoords='offset points',
            ha='center',
            va='bottom',
            bbox=dict(
                boxstyle='round,pad=0.5',
                fc='white',
                ec='gray',
                alpha=0.7
            ),
            fontsize=8,
            zorder=4
        )

        # Update scatter plot
        if drone["plot"] is not None:
            # Update existing plot
            drone["plot"].set_offsets([[x_coord, y_coord]])
            drone["plot"].set_color(self.default_colors[drone_index])
        else:
            # Create new plot if none exists
            drone["plot"] = self.ax.scatter(
                x_coord,
                y_coord,
                color=self.default_colors[drone_index],
                s=100,
                zorder=3
            )

        # Update the display
        self.ax.relim()
        self.ax.autoscale_view()

        # Force a complete redraw
        self.canvas_widget.draw()

        # print(f"Drone {drone_index} position updated to ({x_coord:.1f}, {y_coord:.1f}, {z_coord:.1f})")

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

        # Set up the handlers
        self.setup_click_handlers()

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
                "color": color,
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

    # def bind_keys(self):
    #     def key_highlight(border_frame, button):
    #         border_frame.config(highlightbackground='#3fd4ff', highlightcolor='#3fd4ff')
    #         button.config(bg='white', fg='#3fd4ff')
    #
    #     def key_reset(border_frame, button):
    #         border_frame.config(highlightbackground='#e61848', highlightcolor='#e61848')
    #         button.config(bg='#05001c', fg='white')
    #
    #     self.root.bind("<Up>", lambda event: [self.forward(), key_highlight(self.forward_border, self.forward_button), self.root.after(100, lambda: key_reset(self.forward_border, self.forward_button))])
    #     self.root.bind("<Down>", lambda event: [self.backward(), key_highlight(self.backward_border, self.backward_button), self.root.after(100, lambda: key_reset(self.backward_border, self.backward_button))])
    #     self.root.bind("<Left>", lambda event: [self.left(), key_highlight(self.left_border, self.left_button), self.root.after(100, lambda: key_reset(self.left_border, self.left_button))])
    #     self.root.bind("<Right>", lambda event: [self.right(), key_highlight(self.right_border, self.right_button), self.root.after(100, lambda: key_reset(self.right_border, self.right_button))])
    #     self.root.bind("w", lambda event: [self.forward(), key_highlight(self.forward_border, self.forward_button), self.root.after(100, lambda: key_reset(self.forward_border, self.forward_button))])
    #     self.root.bind("s", lambda event: [self.backward(), key_highlight(self.backward_border, self.backward_button), self.root.after(100, lambda: key_reset(self.backward_border, self.backward_button))])
    #     self.root.bind("a", lambda event: [self.left(), key_highlight(self.left_border, self.left_button), self.root.after(100, lambda: key_reset(self.left_border, self.left_button))])
    #     self.root.bind("d", lambda event: [self.right(), key_highlight(self.right_border, self.right_button), self.root.after(100, lambda: key_reset(self.right_border, self.right_button))])
    #     self.root.focus_set()

    def run(self):
        self.root.mainloop()

app = SwarmGUI()
app.run()

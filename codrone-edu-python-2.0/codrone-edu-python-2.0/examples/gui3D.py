import math
import csv
from tkinter import filedialog, messagebox
import tkinter as tk
from tkinter import colorchooser
import matplotlib.colors as mcolors
from codrone_edu.swarm import *
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


#pink e61848
#dark blue 05001c
#blue 242d78
#light blue 3fd4ff
#button hover purple #d098fa
#arrow button hover #7214ff

def center_window(root, width, height):
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    root.geometry(f"{width}x{height}+{x}+{y}")

class SwarmGUI:
    def __init__(self, mode="full", connected=False):
        self.mode = mode
        self.connected = connected
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
        self.swarm = Swarm(enable_pause=False)
        self.joystick_control_enabled = False
        # if not connected:
        self.swarm.connect()

        self.light_blue = '#3fd4ff'
        self.grid_line_color = '#4169E1'
        self.dark_blue = '#05001c'
        self.pink = '#e61848'
        self.hover_purple = '#d098fa'
        self.arrow_hover_blue = '#7214ff'

        self.top_frame = tk.Frame(self.root, bg='#05001c')
        self.top_frame.pack(side='top', fill='x', pady=5)

        self.add_back_button()

        # Create a main container frame to organize the layout
        self.main_container = tk.Frame(self.root, bg=self.dark_blue)
        self.main_container.pack(expand=True, fill='both')

        if self.mode == "basic":
            # For basic mode, create a centered frame for controls
            self.center_frame = tk.Frame(self.main_container, bg=self.dark_blue)
            self.center_frame.pack(fill='both')

            # Configure grid weights to center content
            self.center_frame.grid_columnconfigure(0, weight=1)
            self.center_frame.grid_columnconfigure(2, weight=1)
            self.center_frame.grid_rowconfigure(0, weight=1)
            self.center_frame.grid_rowconfigure(2, weight=1)

            # Create left frame in the center
            self.left_frame = tk.Frame(self.center_frame, bg=self.dark_blue)
            self.left_frame.grid(row=1, column=1)  # This will center it in the grid

        else:
            # Original layout for other modes
            # Create left frame for controls
            self.left_frame = tk.Frame(self.main_container, bg='#05001c')
            self.left_frame.pack(side='left', fill='y', padx=(0, 10))

            # Create right frame for the graph
            self.right_frame = tk.Frame(self.main_container, bg='#05001c')
            self.right_frame.pack(side='left', expand=True, fill='both')

        self.key_bindings_active = False
        self.create_input_section()
        self.create_control_buttons()
        self.default_colors = ['red', 'blue', 'orange', 'yellow', 'green', '#00ffff', 'purple', 'pink', 'white', 'black']
        self.joystick_control_color = 0
        if self.mode == "basic":
            center_window(self.root, 400, 450)
        elif self.mode == "choreo":
            center_window(self.root, 1200, 700)
        elif self.mode == "full":
            center_window(self.root, 1400, 850)
        elif self.mode == "3d":
            center_window(self.root, 1450, 1000)

        self.create_grid()
        self.is_landed = {i: True for i in range(len(self.swarm.get_drones()))}
        self.joystick_control_speed = 1
        self.auto_update_running = False
        self.recording = False
        self.recorded_coordinates = []
        self.record_timer = None

    # Record coordinates
    def toggle_recording(self):
        """Toggle coordinate recording on/off"""
        self.recording = not self.recording
        # Find the record button in the frame
        for frame in self.left_frame.winfo_children():
            if isinstance(frame, tk.Frame):
                for button in frame.winfo_children():
                    if isinstance(button, tk.Button) and "Record" in button['text']:
                        if self.recording:
                            # Unbind existing hover events
                            button.unbind("<Enter>")
                            button.unbind("<Leave>")

                            button.configure(
                                background='#8a0000',
                                activebackground='#8a0000',
                                text="◉ Recording...",
                                fg="white",
                            )
                            self.recorded_coordinates = []
                            self.record_coordinates()
                        else:
                            # Restore original hover bindings
                            button.configure(
                                background=self.pink,
                                activebackground=self.pink,
                                text="Record Coords"
                            )
                            button.bind("<Enter>", lambda e: e.widget.config(bg=self.hover_purple))
                            button.bind("<Leave>", lambda e: e.widget.config(bg=self.pink))

                            if self.record_timer:
                                self.root.after_cancel(self.record_timer)
                            self.save_coordinates_to_csv()
                        return

    def record_coordinates(self):
        """Record current coordinates of all drones"""
        if self.recording:
            data = self.swarm.get_position_data()
            timestamp = time.time()

            for i, pos in enumerate(data):
                if not self.is_landed[i]:  # Only record flying drones
                    x_coord = pos[1]
                    y_coord = pos[2]
                    z_coord = pos[3]

                    # Skip invalid readings
                    if x_coord != 999.9 and y_coord != 999.9 and z_coord != 999.9:
                        drone = self.droneIcons[i]
                        adjusted_x = x_coord + (drone["x_offset"] if drone["x_offset"] is not None else 0)
                        adjusted_y = y_coord + (drone["y_offset"] if drone["y_offset"] is not None else 0)

                        self.recorded_coordinates.append({
                            'timestamp': timestamp,
                            'drone_id': i,
                            'x': adjusted_x,
                            'y': adjusted_y,
                            'z': z_coord
                        })

            self.record_timer = self.root.after(500, self.record_coordinates)

    def record_action(self, action_name):
        """Record an action with timestamp"""
        if self.recording:
            self.recorded_coordinates.append({
                'timestamp': time.time(),
                'type': 'action',
                'action': action_name,
                'drone_ids': self.get_indices()  # Store which drones performed the action
            })

    def save_coordinates_to_csv(self):
        """Save recorded coordinates and actions to CSV file"""
        if not self.recorded_coordinates:
            messagebox.showerror("Error", "No data recorded")
            return

        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                title="Save Recorded Data"
            )

            if not filename:
                return

            with open(filename, 'w', newline='') as csvfile:
                fieldnames = ['timestamp', 'type', 'drone_id', 'x', 'y', 'z', 'action']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                for data in self.recorded_coordinates:
                    if data.get('type') == 'action':
                        # Write action entry
                        writer.writerow({
                            'timestamp': data['timestamp'],
                            'type': 'action',
                            'action': data['action'],
                            'drone_id': ','.join(map(str, data['drone_ids'])),
                            'x': '',
                            'y': '',
                            'z': ''
                        })
                    else:
                        # Write coordinate entry
                        writer.writerow({
                            'timestamp': data['timestamp'],
                            'type': 'coordinate',
                            'drone_id': data['drone_id'],
                            'x': data['x'],
                            'y': data['y'],
                            'z': data['z'],
                            'action': ''
                        })

            messagebox.showinfo("Info", f"Saved data to {filename}")

        except Exception as e:
            messagebox.showerror("Error", f"Error saving data: {e}")

    def visualize_flight_paths(self):
        filename = filedialog.askopenfilename(
            title="Select Flight Data CSV",
            filetypes=((("CSV files", "*.csv"), ("All files", "*.*")))
        )

        if filename:
            try:
                # Read the CSV file
                self.df = pd.read_csv(filename)

                # Convert timestamps to elapsed seconds
                start_time = self.df['timestamp'].min()
                self.df['elapsed_seconds'] = self.df['timestamp'] - start_time

                # Get time range in seconds
                self.min_time = 0
                self.max_time = self.df['elapsed_seconds'].max()
                self.current_time = self.min_time

                # Calculate fixed plot limits
                self.x_min = self.df['x'].min()
                self.x_max = self.df['x'].max()
                self.y_min = self.df['y'].min()
                self.y_max = self.df['y'].max()
                self.z_min = self.df['z'].min()
                self.z_max = self.df['z'].max()

                # Add padding to limits
                padding = 0.5
                self.x_min -= padding
                self.x_max += padding
                self.y_min -= padding
                self.y_max += padding
                self.z_min -= padding
                self.z_max += padding

                # Create slider frame
                slider_frame = tk.Frame(self.left_frame, bg=self.dark_blue)
                slider_frame.pack(fill='x', pady=10)

                # Create time slider
                tk.Label(
                    slider_frame,
                    text="Elapsed Time (seconds):",
                    bg=self.dark_blue,
                    fg=self.light_blue
                ).pack()

                self.time_slider = tk.Scale(
                    slider_frame,
                    from_=self.min_time,
                    to=self.max_time,
                    orient='horizontal',
                    bg=self.dark_blue,
                    fg=self.light_blue,
                    troughcolor=self.pink,
                    highlightbackground=self.dark_blue,
                    resolution=0.1,
                    command=self.update_time_from_slider
                )
                self.time_slider.pack(fill='x', padx=10)

                # Create time input frame
                time_input_frame = tk.Frame(slider_frame, bg=self.dark_blue)
                time_input_frame.pack(pady=5)

                # Add time entry box
                self.time_entry = tk.Entry(
                    time_input_frame,
                    width=20,
                    bg='white',
                    fg=self.dark_blue
                )
                self.time_entry.pack(side='left', padx=5)
                self.time_entry.insert(0, "0.0")

                # Add "Go" button
                tk.Button(
                    time_input_frame,
                    text="Go",
                    command=self.update_time_from_entry,
                    bg=self.pink,
                    fg='white',
                    activebackground=self.hover_purple
                ).pack(side='left')

                # Add action log frame
                self.log_frame = tk.Frame(self.left_frame, bg=self.dark_blue)
                self.log_frame.pack(pady=10)

                # Add log title
                tk.Label(
                    self.log_frame,
                    text="Action Log",
                    bg=self.dark_blue,
                    fg=self.light_blue,
                    font=('Helvetica', 10, 'bold')
                ).pack()

                # Add scrolled text widget for log
                self.log_text = tk.Text(
                    self.log_frame,
                    height=40,
                    width=30,
                    bg=self.dark_blue,
                    fg=self.light_blue,
                    font=('Courier', 9)
                )
                self.log_text.pack(padx=10, pady=10)

                # Initial plot
                self.update_plot()

            except Exception as e:
                messagebox.showerror("Error", f"Error visualizing data: {e}")

    def update_time_from_slider(self, value):
        """Update visualization based on slider position"""
        self.current_time = float(value)
        self.time_entry.delete(0, tk.END)
        self.time_entry.insert(0, f"{self.current_time:.1f}")
        self.update_plot()

    def update_time_from_entry(self):
        """Update visualization based on entered time"""
        try:
            entered_time = float(self.time_entry.get())
            if self.min_time <= entered_time <= self.max_time:
                self.current_time = entered_time
                self.time_slider.set(entered_time)
                self.update_plot()
            else:
                messagebox.showerror("Error", f"Time must be between {self.min_time:.1f} and {self.max_time:.1f} seconds")
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid number")

    def update_plot(self):
        """Update the plot for the current time"""
        self.ax.cla()

        # Clear log
        self.log_text.delete(1.0, tk.END)

        # Get data up to current time
        current_data = self.df[self.df['elapsed_seconds'] <= self.current_time]

        # Update action log
        actions = current_data[current_data['type'] == 'action']
        for _, action in actions.iterrows():
            elapsed = action['elapsed_seconds']
            self.log_text.insert(tk.END,
                                 f"[{elapsed:.1f}s] {action['action']} - Drones: {action['drone_id']}\n")

        # Plot each drone's path
        has_plots = False
        coordinate_data = current_data[current_data['type'] != 'action']  # Filter out action entries

        # Store last positions for annotations
        last_positions = {}

        for drone_id in coordinate_data['drone_id'].unique():
            # Handle comma-separated drone IDs
            if isinstance(drone_id, str) and ',' in drone_id:
                drone_ids = [int(d.strip()) for d in drone_id.split(',')]
                color_index = drone_ids[0]  # Use first drone's ID for color
            else:
                color_index = int(drone_id)

            drone_data = coordinate_data[coordinate_data['drone_id'] == drone_id]
            color = self.default_colors[color_index % len(self.default_colors)]

            # Only plot if we have x, y, z coordinates
            if not drone_data.empty and 'x' in drone_data.columns and 'y' in drone_data.columns and 'z' in drone_data.columns:
                # Plot path
                self.ax.plot3D(
                    drone_data['x'],
                    drone_data['y'],
                    drone_data['z'],
                    linestyle='-',
                    color=color,
                    label=f'Drone {drone_id}'
                )
                has_plots = True

                # Plot current position and add annotation
                latest_pos = drone_data.iloc[-1]
                self.ax.scatter3D(
                    latest_pos['x'],
                    latest_pos['y'],
                    latest_pos['z'],
                    color=color,
                    s=100
                )

                # Add annotation for current position
                self.ax.text(
                    latest_pos['x'],
                    latest_pos['y'],
                    latest_pos['z'] + 0.25,
                    f'Drone {drone_id}\n({latest_pos["x"]:.1f}, {latest_pos["y"]:.1f}, {latest_pos["z"]:.1f})',
                    color=color,
                    bbox=dict(
                        boxstyle='round,pad=0.5',
                        fc='white',
                        alpha=0.7
                    ),
                    fontsize=8
                )

        if has_plots:
            self.ax.legend(facecolor=self.dark_blue, labelcolor='white')

        self.ax.set_facecolor(self.dark_blue)
        self.ax.xaxis.pane.fill = False
        self.ax.yaxis.pane.fill = False
        self.ax.zaxis.pane.fill = False

        # Set fixed axis limits
        self.ax.set_xlim(self.x_min, self.x_max)
        self.ax.set_ylim(self.y_min, self.y_max)
        self.ax.set_zlim(self.z_min, self.z_max)

        # Update grid colors
        self.ax.xaxis._axinfo["grid"].update({"color": self.light_blue, "alpha": 0.3})
        self.ax.yaxis._axinfo["grid"].update({"color": self.light_blue, "alpha": 0.3})
        self.ax.zaxis._axinfo["grid"].update({"color": self.light_blue, "alpha": 0.3})

        # Update labels
        self.ax.set_xlabel('X Location (m)', color=self.pink, fontsize=12)
        self.ax.set_ylabel('Y Location (m)', color=self.light_blue, fontsize=12)
        self.ax.set_zlabel('Z Location (m)', color=self.hover_purple, fontsize=12)

        # Update title with elapsed time
        self.ax.set_title(f'Flight Path Visualization (t={self.current_time:.1f}s)',
                          color=self.light_blue, pad=15, fontsize=14)

        # Update canvas
        self.canvas_widget.draw()

    # Swarm joystick control
    def toggle_joystick_control(self):
        self.joystick_control_enabled = not self.joystick_control_enabled
        if self.joystick_control_enabled:
            messagebox.showinfo("Info", "Joystick control enabled for the swarm.")
            self.run_joystick_control()
        else:
            messagebox.showinfo("Info", "Joystick control disabled for the swarm.")

    def run_joystick_control(self):
        """
        Continuously reads joystick inputs and controls all drones in the swarm.
        This function runs until joystick control is toggled off.
        """
        selected_indices = self.get_indices()

        if self.joystick_control_enabled:
            l1 = self.swarm.one_drone(0, 'l1_pressed')
            l2 = self.swarm.one_drone(0, 'l2_pressed')
            r1 = self.swarm.one_drone(0, 'r1_pressed')
            r2 = self.swarm.one_drone(0, 'r2_pressed')

            joystick_data = self.swarm.one_drone(0, 'get_joystick_data')

            left_joystick_x = joystick_data[1]  # Horizontal Left
            left_joystick_y = joystick_data[2]  # Vertical Left
            right_joystick_x = joystick_data[5]  # Horizontal Right
            right_joystick_y = joystick_data[6]  # Vertical Right

            if l1:
                print(f"L1 Pressed, taking off {selected_indices}")
                if self.is_landed[selected_indices[0]]:
                    self.take_off()
                else:
                    self.land()

            if l2:
                print(f"L2 Pressed, Speed updated to {self.joystick_control_speed} for drones {selected_indices}")
                if self.joystick_control_speed >= 3:
                    self.joystick_control_speed = 1
                else:
                    self.joystick_control_speed += 1

            if r1:
                if self.joystick_control_color >= len(self.default_colors) - 1:
                    self.joystick_control_color = 0
                else:
                    self.joystick_control_color += 1

                print(f"R1 Pressed, color updated to {self.default_colors[self.joystick_control_color]} for drones {selected_indices}")
                for drone in self.droneIcons:
                    # print(f"Drone {drone['drone_index']} selected state: {drone['selected']}")
                    if drone["selected"].get():
                        self.update_drone_color(drone, self.default_colors[self.joystick_control_color])

            if r2:
                if self.recording:
                    self.record_action("flip")
                if right_joystick_x >= 25:
                    self.swarm.all_drones("flip", direction="right")
                elif right_joystick_x <= -25:
                    self.swarm.all_drones("flip", direction="left")
                elif right_joystick_y <= 25:
                    self.swarm.all_drones("flip", direction="front")
                elif right_joystick_x <= -25:
                    self.swarm.all_drones("flip", direction="back")

            threshold = 10
            throttle_input = left_joystick_y if abs(left_joystick_y) > threshold else 0
            yaw_input = -left_joystick_x if abs(left_joystick_x) > threshold else 0
            pitch_input = right_joystick_y if abs(right_joystick_y) > threshold else 0
            roll_input = right_joystick_x if abs(right_joystick_x) > threshold else 0

            scale = 1 # Used to modify how much the input matters
            throttle_power = int(throttle_input * scale)
            yaw_power = int(yaw_input * scale)
            pitch_power = int(pitch_input * scale)
            roll_power = int(roll_input * scale)

            for index in selected_indices:
                self.swarm.one_drone(index, 'sendControl', roll_power, pitch_power, yaw_power, throttle_power)

        self.root.after(50, self.run_joystick_control)


    # Import + Process CSV code

    def import_csv(self):
        filename = filedialog.askopenfilename(
            title="Select CSV File",
            filetypes=(("CSV files", "*.csv"), ("All files", "*.*"))
        )

        # Check if a file was selected (user didn't click cancel)
        if not filename:
            print("No file selected")
            return

        coordinates = []
        print(f"Attempting to open file: {filename}")  # Debug print

        # Read CSV file
        with open(filename, 'r') as file:
            reader = csv.reader(file, delimiter=',')

            for i, row in enumerate(reader):
                x, y, z = map(float, row)
                coordinates.append([x, y, z])
                print(f"Read row {i}: {x}, {y}, {z}")

            print(f"Successfully read {len(coordinates)} coordinates")  # Debug print

            if coordinates:  # Check if we got any coordinates
                self.process_csv(coordinates)
            else:
                messagebox.showerror("Error", "No coordinates were read from the file")

    def export_csv(self):
        """Export all current coordinates on the graph into a CSV file."""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                title="Save Current Coordinates"
            )

            if not filename:
                print("Save operation canceled.")
                return

            # Prepare data for export
            coordinates = []
            for drone in self.droneIcons:
                if drone["x_position"] is not None and drone["y_position"] is not None and drone["z_position"] is not None:
                    coordinates.append([
                        drone["x_position"],
                        drone["y_position"],
                        drone["z_position"]
                    ])

            # Write to CSV
            with open(filename, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                for coord in coordinates:
                    writer.writerow(coord)

            messagebox.showinfo("Info", f"Exported current coordinates to {filename}")

        except Exception as e:
            messagebox.showerror("Error", f"Error exporting data: {e}")

    def process_csv(self, input_coords):
        print(f"Processing {len(input_coords)} coordinates")  # Debug print
        print(f"Number of drone icons: {len(self.droneIcons)}")  # Debug print

        if len(input_coords) < len(self.droneIcons):
            messagebox.showwarning("Warning", f"Warning: Not enough coordinates ({len(input_coords)}) for all drones ({len(self.droneIcons)})")

        for index, drone in enumerate(self.droneIcons):
            if index >= len(input_coords):
                messagebox.showerror("Error", f"No coordinates available for drone {index}")
                break

            coords = input_coords[index]

            self.set_drone_position(index, coords[0], coords[1], coords[2])
            self.reset_offsets()
            # print(f"Set drone {index} position to {coords[0]}, {coords[1]}, {coords[2]}")


    # Add back button
    def add_back_button(self):
        # Add back button first (left side)
        back_button_border = tk.Frame(
            self.top_frame,
            highlightbackground=self.pink,
            highlightcolor=self.pink,
            highlightthickness=0,
            bd=0,
            bg=self.dark_blue
        )
        back_button_border.pack(side='left', padx=2)

        back_button_style = {
            'font': ('Helvetica', 28, 'bold'),  # Increased font size
            'bg': self.dark_blue,
            'fg': self.pink,
            'relief': 'flat',
            'bd': 0,
            'highlightthickness': 0,
            'width': 1,  # Reduced width
            'height': 1,
            'cursor': 'hand2',
            'padx': 0,  # Reduced horizontal padding
            'pady': 0  # Reduced vertical padding
        }

        # Create back button using create_button function with modified style
        back_button = self.create_button(
            back_button_border,
            "↩",
            self.return_to_launch_screen,
            back_button_style
        )
        back_button.pack(padx=0, pady=0)

        # Add hover effects
        def highlight_back_button(event):
            back_button.config(bg=self.pink, fg='#ffffff')

        def reset_back_button(event):
            back_button.config(bg=self.dark_blue, fg=self.pink)

        back_button.bind("<Enter>", highlight_back_button)
        back_button.bind("<Leave>", reset_back_button)

    def return_to_launch_screen(self):
        self.auto_update_running = False
        self.joystick_control_enabled = False
        self.recording = False
        if self.record_timer:
            self.root.after_cancel(self.record_timer)
            self.record_timer = None

        self.swarm.close()
        del self.swarm

        self.root.destroy()
        launch_screen = LaunchScreen(connected=True)
        launch_screen.run()


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
        """Open color picker dialog and return the selected color"""
        color_code = colorchooser.askcolor(title="Choose Drone Color")
        if color_code[1]:
            new_color = color_code[1]
            rgb_value = color_code[0]
            print(f"Selected RGB color: {rgb_value}")
            self.update_drone_color(drone, new_color)

    def update_drone_color(self, drone, new_color):
        """Update drone color in all necessary places"""
        # Update the stored color
        drone["color"] = new_color

        # Update the LED color on the physical drone
        rgba_color = self.process_color(drone["color"])
        self.swarm.one_drone(drone["drone_index"], "set_drone_LED", *rgba_color)
        self.swarm.one_drone(drone["drone_index"], "set_controller_LED", *rgba_color)

        # Update the plot color
        if drone["plot"] is not None:
            drone["plot"].set_color(new_color)
            self.canvas_widget.draw()

        # Update the annotation color
        if drone["annotation"] is not None:
            drone["annotation"].set_color(new_color)

        # Update the checkbox colors
        if "checkbox" in drone:
            drone["checkbox"].configure(
                fg=new_color,
                activeforeground=new_color
            )

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

        pos = self.swarm.get_position_data()
        z = pos[self.selected_drone["drone_index"]][3]
        # Send drone to the release position
        self.goto_position(
            self.selected_drone["drone_index"],
            event.xdata,
            event.ydata,
            z,
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

        if self.mode == "basic":
            fontSize = 14
        else:
            fontSize = 18

        title_label = tk.Label(
            self.top_frame,
            text="CoDrone EDU - Swarm",
            font=('Terminal', fontSize, 'bold'),
            bg=self.dark_blue,
            fg=self.light_blue,
            pady=2
        )
        title_label.pack(side='top', padx=0)

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
        left_control_frame.pack(fill='x', padx=5, pady=10)

        # Create main control buttons
        if self.mode == "basic":
            main_buttons = [
                ("Take Off", self.take_off),
                ("Land", self.land)
            ]
            self.toggle_key_bindings()
        elif self.mode == "visualize":
            main_buttons = [
                ("Load Flight Data", self.visualize_flight_paths)
            ]
        elif self.mode == "choreo":
            main_buttons = [
                ("Take Off", self.take_off),
                ("Land", self.land),
                ("Auto Update", self.toggle_auto_update),
                ("Import CSV", self.import_csv),
                ("Export CSV", self.export_csv),
                ("Record Coords", self.toggle_recording)
            ]
        else:
            main_buttons = [
                ("Take Off", self.take_off),
                ("Land", self.land),
                ("Auto Update", self.toggle_auto_update),
                ("Import CSV", self.import_csv),
                ("Export CSV", self.export_csv),
                ("Bind Keys", self.toggle_key_bindings),
                ("Stabilize Swarm", self.stabilize_swarm),
                ("Joystick Control", self.toggle_joystick_control),
                ("Record Coords", self.toggle_recording)
            ]

        for text, command in main_buttons:
            self.create_button(left_control_frame, text, command, button_style).pack(padx=5, pady=5)

        if self.mode == "visualize":
            return
        # Create choreography section
        if self.mode != "basic":
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

            if self.mode == "choreo" or self.mode == "basic":
                choreo_buttons = [
                    ("Main Choreo", self.run_main_choreo)
                ]
            else:
                choreo_buttons = [
                    ("Main Choreo", self.run_main_choreo),
                    ("Pyramid", self.run_pyra),
                    ("Flip", self.flipall),
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
            messagebox.showerror("Error", f"Invalid drone index: {drone_index}")
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
        if self.recording:
            self.record_action("land")
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
            messagebox.showwarning("Warning", "No drones selected. Not landing.")

    def take_off(self):
        selected_drone_indices = self.get_indices()
        num_selected_drones = len(selected_drone_indices)
        if self.recording:
            self.record_action("take_off")
        if num_selected_drones == num_drones:
            print("Taking off ALL drones (all selected)...")
            self.swarm.all_drones("takeoff")
            for i in range(num_drones):
                self.is_landed[i] = False
        elif num_selected_drones > 0:
            # print(f"Taking off selected drones (synchronized): {selected_drone_indices}")
            sync_takeoff = Sync()
            for index in selected_drone_indices:
                seq = Sequence(index)
                seq.add("takeoff")
                sync_takeoff.add(seq)
                self.is_landed[index] = False
            self.swarm.run(sync_takeoff, type="parallel")
        else:
            messagebox.showwarning("Warning", "No drones selected. Not taking off.")

    def forward(self):
        if self.recording:
            self.record_action("forward")
        self.move_drones("forward", x=0.5)

    def backward(self):
        if self.recording:
            self.record_action("backward")
        self.move_drones("backward", x=-0.5)

    def left(self):
        if self.recording:
            self.record_action("left")
        self.move_drones("left", y=0.5)

    def right(self):
        if self.recording:
            self.record_action("right")
        self.move_drones("right", y=-0.5)

    def run_main_choreo(self):
        if self.recording:
            self.record_action("run_main_choreo")
        from mainChoreography import MainChoreo
        run = MainChoreo(self)
        selected_drone_indices = self.get_indices()
        if not selected_drone_indices:
            messagebox.showwarning("Warning", f"No drones selected. Not running main choreo sequence.")
            return

        print(f"Running main choreo sequence for the following drones: {selected_drone_indices}")
        run.run_sequence(self.swarm, selected_drone_indices)

    def run_pyra(self):
        from pyramid import Pyramid
        if self.recording:
            self.record_action("run_pyra")
        runPyra = Pyramid(self)
        selected_drone_indices = self.get_indices()
        if not selected_drone_indices:
            messagebox.showwarning("Warning", f"No drones selected. Not running pyra sequence.")
            return
        # add specifics per num drones

        print(f"Running pyramid sequence for the following drones: {selected_drone_indices}")
        self.take_off()
        runPyra.run_sequence(self.swarm, selected_drone_indices)

    def flipall(self):
        if self.recording:
            self.record_action("flipall")
        print("flipping all of themmmmmmmmmmmmmmmmmmm")
        selected_drone_indices = self.get_indices()
        num_selected_drones = len(selected_drone_indices)

        if num_selected_drones > 0:
            print(f"Running flipp for the following drones: {selected_drone_indices}")
            sync_right = Sync()  # Create a Sync object
            for index in selected_drone_indices:
                seq = Sequence(index)  # Create a Sequence for each selected drone
                seq.add("flip", "back")
                sync_right.add(seq)  # Add sequence to Sync object
            self.swarm.run(sync_right, type="parallel")  # Run synchronized right movement for selected drones

    def run_wiggle(self):
        if self.recording:
            self.record_action("run_wiggle")
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
        if self.recording:
            self.record_action("run_spiral")
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
            messagebox.showwarning("Warning", "No drones selected. Not moving right.")  # Do nothing - no movement

    def create_input_section(self):
        if self.mode == "basic":
            return
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

        if self.mode == "visualize":
            return
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
            command=lambda: [
                self.set_drone_position(
                    int(self.drone_index_input.get()),
                    float(self.x_coord_input.get()),
                    float(self.y_coord_input.get()),
                    float(self.z_coord_input.get())
                ),
                self.reset_offsets()
            ],
            **self.button_style
        )
        self.set_coords_button.grid(row=0, column=8, padx=(10, 0), pady=5)
        self.set_coords_button.bind("<Enter>", on_button_enter)  # Hover effect for red buttons
        self.set_coords_button.bind("<Leave>", on_button_leave)  # Hover effect for red buttons

    def stabilize_swarm(self):
        if self.recording:
            self.record_action("stabilize_swarm")
        if not self.hasGeneratedGrid:
            messagebox.showerror("Error", "Grid not generated, cannot auto-stabilize.")
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
            messagebox.showwarning("Warning", "No valid height data received from selected drones to calculate median.")
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

    def update_timer(self):
        if hasattr(self, 'auto_update_running') and self.auto_update_running:
            self.update_graph()
            self.root.after(500, self.update_timer)

    def toggle_auto_update(self):
        """Toggle the auto-update functionality"""
        if not hasattr(self, 'auto_update_running') or not self.auto_update_running:
            messagebox.showinfo("Info", "Starting auto-update")
            self.auto_update_running = True
            self.update_timer()  # Start the update loop
        else:
            messagebox.showinfo("Info", "Stopping auto-update")
            self.auto_update_running = False

    def update_graph(self):
        data = self.swarm.get_position_data()
        max_distance = 2

        for i in range(len(self.droneIcons)):
            pos = data[i]
            drone = self.droneIcons[i]

            # Get raw coordinates from position data
            x_coord = pos[1]
            y_coord = pos[2]
            z_coord = pos[3]

            # Skip invalid readings
            if x_coord == 999.9 or y_coord == 999.9 or z_coord == 999.9:
                continue

            if z_coord >= 0.5:
                self.is_landed[i] = False

            # Skip position updates if drone is landed
            if self.is_landed[i]:
                self.set_drone_position(i, drone["x_offset"], drone["y_offset"], 0)
                continue

            # Add the stored offsets to the coordinates
            adjusted_x = x_coord + drone["x_offset"] if drone["x_offset"] is not None else x_coord
            adjusted_y = y_coord + drone["y_offset"] if drone["y_offset"] is not None else y_coord

            # Update position with adjusted coordinates
            self.set_drone_position(i, adjusted_x, adjusted_y, z_coord)

            max_distance = max(max_distance, abs(adjusted_x), abs(adjusted_y), abs(z_coord))

        # Automatically resize the boundaries of the graph
        padding = 1
        range_limit = max_distance + padding

        self.ax.set_xlim(-range_limit, range_limit)
        self.ax.set_ylim(-range_limit, range_limit)

        if self.mode == "3d":
            # Update grid properties
            self.ax.set_zlim(0, range_limit)
            self.ax.xaxis._axinfo["grid"].update({"color": "#3fd4ff", "alpha": 0.3})
            self.ax.yaxis._axinfo["grid"].update({"color": "#3fd4ff", "alpha": 0.3})
            self.ax.zaxis._axinfo["grid"].update({"color": "#3fd4ff", "alpha": 0.3})
        else:
            self.ax.grid(True, linestyle='--', alpha=0.7)

        self.canvas_widget.draw()

# Should run when the drones are landed
    def reset_offsets(self):
        selected_drone_indices = self.get_indices()
        num_selected_drones = len(selected_drone_indices)

        for i in range(num_selected_drones):
            if self.is_landed[i]:
                drone = self.droneIcons[i]
                drone["x_offset"] = drone["x_position"]
                drone["y_offset"] = drone["y_position"]
                # print(f"Saving offsets for drone {i}, x: {drone["x_offset"]:.1f}, y: {drone["y_offset"]:.1f}")

    def set_drone_position(self, drone_index, x_coord, y_coord, z_coord):
        if not (0 <= drone_index < len(self.droneIcons)):
            messagebox.showerror("Error", f"Invalid drone index: {drone_index}")
            return

        drone = self.droneIcons[drone_index]

        # If this is the first position set for this drone (initial position is None)
        if drone["x_position"] is None and drone["y_position"] is None:
            drone["x_offset"] = x_coord
            drone["y_offset"] = y_coord

        # Update stored positions
        drone["x_position"] = x_coord
        drone["y_position"] = y_coord
        drone["z_position"] = z_coord

        # Update visualization based on mode
        if self.mode != "basic":
            # First remove existing annotation if it exists
            if drone["annotation"] is not None:
                if self.mode == "3d":
                    drone["annotation"].remove()
                else:
                    drone["annotation"].remove()

            # Create new annotation
            if self.mode == "3d":
                # 3D text annotation
                drone["annotation"] = self.ax.text(
                    x_coord, y_coord, z_coord + 0.25,
                    f'Drone {drone_index}\n({x_coord:.1f}, {y_coord:.1f}, {z_coord:.1f})',
                    color=drone["color"],
                    bbox=dict(boxstyle='round,pad=0.5', fc='white'),
                    fontsize=8
                )
            else:
                # 2D annotation
                drone["annotation"] = self.ax.annotate(
                    f'Drone {drone_index}\n({x_coord:.1f}, {y_coord:.1f}, {z_coord:.1f})',
                    xy=(x_coord, y_coord),
                    xytext=(0, 15),
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
                if self.mode == "3d":
                    drone["plot"]._offsets3d = ([x_coord], [y_coord], [z_coord])
                else:
                    drone["plot"].set_offsets([[x_coord, y_coord]])
                drone["plot"].set_color(drone["color"])
            else:
                # Create new plot if none exists
                if self.mode == "3d":
                    drone["plot"] = self.ax.scatter(
                        x_coord,
                        y_coord,
                        z_coord,
                        color=self.default_colors[drone_index],
                        s=100
                    )
                else:
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

    def create_grid(self):
        global swarm_drones, num_drones

        self.hasGeneratedGrid = True
        swarm_drones = self.swarm.get_drones()
        num_drones = len(swarm_drones)

        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        from matplotlib.figure import Figure

        if self.mode != "basic":
            # Create either 2D or 3D axes based on mode
            if self.mode == "3d" or self.mode == "visualize":
                self.fig = Figure(figsize=(12, 12))
                self.ax = self.fig.add_subplot(111, projection='3d')

                # Set background colors
                self.fig.patch.set_facecolor('#05001c')  # Figure background
                self.ax.set_facecolor('#05001c')  # Axes background

                # Make panes transparent
                self.ax.xaxis.pane.fill = False
                self.ax.yaxis.pane.fill = False
                self.ax.zaxis.pane.fill = False

                # Remove pane edges
                self.ax.xaxis.pane.set_edgecolor('none')
                self.ax.yaxis.pane.set_edgecolor('none')
                self.ax.zaxis.pane.set_edgecolor('none')

                # Set grid colors for each axis explicitly
                self.ax.xaxis._axinfo["grid"].update({"color": "#3fd4ff", "alpha": 0.3})
                self.ax.yaxis._axinfo["grid"].update({"color": "#3fd4ff", "alpha": 0.3})
                self.ax.zaxis._axinfo["grid"].update({"color": "#3fd4ff", "alpha": 0.3})

                # Color code the axes
                self.ax.xaxis.line.set_color('#850f2a')  # Pink
                self.ax.yaxis.line.set_color('#1d6275')  # Light blue
                self.ax.zaxis.line.set_color('#694d7d')  # Purple

                # Color the labels
                self.ax.set_xlabel('X (m)', color='#e61848', fontsize=12)  # Pink
                self.ax.set_ylabel('Y (m)', color='#3fd4ff', fontsize=12)  # Light blue
                self.ax.set_zlabel('Z (m)', color='#d098fa', fontsize=12)  # Purple

                # Color the tick labels
                self.ax.tick_params(axis='x', colors='#e61848')  # Pink
                self.ax.tick_params(axis='y', colors='#3fd4ff')  # Light blue
                self.ax.tick_params(axis='z', colors='#d098fa')  # Purple

                # Set axis limits with more visible color
                self.ax.set_xlim(-2, 2)
                self.ax.set_ylim(-2, 2)
                self.ax.set_zlim(0, 4)

                self.ax.set_title('Drone Positions (3D)', color='#3fd4ff', pad=15, fontsize=14)

                # Create and pack canvas with dark background
                self.canvas_widget = FigureCanvasTkAgg(self.fig, master=self.right_frame)
                self.canvas_widget.draw()
                self.canvas_widget.get_tk_widget().configure(bg='#05001c')
                self.canvas_widget.get_tk_widget().pack(expand=True, fill='both')
            else:
                self.fig = Figure(figsize=(6, 6))
                self.ax = self.fig.add_subplot(111)

                # Set background colors
                self.fig.patch.set_facecolor('#05001c')  # Figure background
                self.ax.set_facecolor('#05001c')  # Axes background

                # Configure the grid
                self.ax.grid(True, linestyle='--', alpha=0.3, color='#3fd4ff')

                # Set axis limits
                self.ax.set_xlim(-2, 2)
                self.ax.set_ylim(-2, 2)

                # Color code the axes
                self.ax.spines['bottom'].set_color('#850f2a')  # Pink
                self.ax.spines['left'].set_color('#1d6275')  # Light blue
                self.ax.spines['top'].set_color('#850f2a')  # Pink
                self.ax.spines['right'].set_color('#1d6275')  # Light blue

                # Color the labels
                self.ax.set_xlabel('X (m)', color='#e61848', fontsize=12)  # Pink
                self.ax.set_ylabel('Y (m)', color='#3fd4ff', fontsize=12)  # Light blue

                # Color the tick labels
                self.ax.tick_params(axis='x', colors='#e61848')  # Pink
                self.ax.tick_params(axis='y', colors='#3fd4ff')  # Light blue

                self.ax.set_title('Drone Positions (2D)', color='#3fd4ff', pad=15, fontsize=14)

                # Add the plot to Tkinter
                self.canvas_widget = FigureCanvasTkAgg(self.fig, master=self.right_frame)
                self.canvas_widget.draw()
                self.canvas_widget.get_tk_widget().configure(bg='#05001c')
                self.canvas_widget.get_tk_widget().pack(expand=True, fill='both', padx=10, pady=10)
                self.setup_click_handlers()

        self.drone_plots = []
        self.drone_annotations = []
        self.droneIcons = []

        # Place Drone Icons
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

            # Create plot elements only in full mode
            if self.mode != "basic":
                if x_pos is not None and y_pos is not None:
                    if self.mode == "3d":
                        drone_plot = self.ax.scatter(x_pos, y_pos, z_pos, color=color, s=100)
                        annotation = self.ax.text(
                            x_pos, y_pos, z_pos+0.25,
                            f'Drone {i}\n({x_pos:.1f}, {y_pos:.1f}, {z_pos:.1f})',
                            color=color,
                            bbox=dict(boxstyle='round,pad=0.5', fc='white'),
                            fontsize=8
                        )
                    else:
                        drone_plot = self.ax.scatter(x_pos, y_pos, color=color, s=100)
                        annotation = self.ax.annotate(
                            f'Drone {i}\n({x_pos:.1f}, {y_pos:.1f}, {z_pos:.1f})',
                            (x_pos, y_pos),
                            xytext=(0, 10),
                            textcoords='offset points',
                            ha='center',
                            bbox=dict(boxstyle='round,pad=0.5', fc='white', alpha=0.7),
                            fontsize=8
                        )
                else:
                    drone_plot = None
                    annotation = None
            else:
                drone_plot = None
                annotation = None

            if self.mode == "visualize":
                return
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
            drone_checkbox.bind("<Button-3>", lambda e, d=drone: self.open_color_picker(d))

            # Store the checkbox reference in the drone dictionary
            drone["checkbox"] = drone_checkbox

            # Set drone LED color
            self.swarm.one_drone(drone["drone_index"], "set_drone_LED", *rgba_color)
            self.swarm.one_drone(drone["drone_index"], "set_controller_LED", *rgba_color)

        # Update the display for full mode
        if self.mode != "basic":
            self.canvas_widget.draw()

    def click_checkbox(self, index):
        if index < len(self.droneIcons):
            current_value = self.droneIcons[index]["selected"].get()
            self.droneIcons[index]["selected"].set(not current_value)

    def toggle_key_bindings(self):
        """Toggle keyboard controls on/off"""
        if self.key_bindings_active:
            # Unbind all keys
            for key in ["<Up>", "<Down>", "<Left>", "<Right>", "w", "s", "a", "d", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]:
                self.root.unbind(key)
            self.key_bindings_active = False
            messagebox.showinfo("Info", "Keybinds disabled")
        else:
            # Bind all keys
            self.bind_keys()
            self.key_bindings_active = True
            messagebox.showinfo("Info", "Keybinds enabled")

    def bind_keys(self):
        """Set up keyboard bindings"""

        def key_highlight(border_frame, button):
            border_frame.config(highlightbackground='#3fd4ff', highlightcolor='#3fd4ff')
            button.config(bg='white', fg='#3fd4ff')

        def key_reset(border_frame, button):
            border_frame.config(highlightbackground='#e61848', highlightcolor='#e61848')
            button.config(bg='#05001c', fg='white')

        self.root.bind("<Up>", lambda event: [self.forward(), key_highlight(self.forward_border, self.forward_button), self.root.after(100, lambda: key_reset(self.forward_border, self.forward_button))])
        self.root.bind("<Down>", lambda event: [self.backward(), key_highlight(self.backward_border, self.backward_button), self.root.after(100,lambda: key_reset(self.backward_border, self.backward_button))])
        self.root.bind("<Left>", lambda event: [self.left(), key_highlight(self.left_border, self.left_button), self.root.after(100, lambda: key_reset(self.left_border, self.left_button))])
        self.root.bind("<Right>", lambda event: [self.right(), key_highlight(self.right_border, self.right_button), self.root.after(100, lambda: key_reset(self.right_border, self.right_button))])
        self.root.bind("w", lambda event: [self.forward(), key_highlight(self.forward_border, self.forward_button), self.root.after(100, lambda: key_reset(self.forward_border, self.forward_button))])
        self.root.bind("s", lambda event: [self.backward(), key_highlight(self.backward_border, self.backward_button), self.root.after(100, lambda: key_reset(self.backward_border, self.backward_button))])
        self.root.bind("a", lambda event: [self.left(), key_highlight(self.left_border, self.left_button), self.root.after(100, lambda: key_reset(self.left_border, self.left_button))])
        self.root.bind("d", lambda event: [self.right(), key_highlight(self.right_border, self.right_button), self.root.after(100, lambda: key_reset(self.right_border, self.right_button))])

        for i in range(len(self.droneIcons)):
            self.root.bind(str(i), lambda e, x=i: self.click_checkbox(x))

        self.root.focus_set()

    def run(self):
        self.root.mainloop()

class LaunchScreen:
    def __init__(self, connected=False):
        self.root = tk.Tk()
        self.connected = connected
        self.root.title("CoDrone EDU - Launch Options")
        self.root.configure(bg='#05001c')
        self.selected_mode = None

        center_window(self.root, 350, 650)


        # Title
        title_label = tk.Label(
            self.root,
            text="Select Operation Mode",
            font=('Terminal', 12, 'bold'),
            bg='#05001c',
            fg='#3fd4ff',
            pady=20
        )
        title_label.pack()

        # Button styles
        button_style = {
            'font': ('Helvetica', 10, 'bold'),
            'bg': '#e61848',
            'fg': 'white',
            'relief': 'flat',
            'width': 20,
            'height': 2,
            'cursor': 'hand2',
            'pady': 2
        }

        # Create frame for buttons
        button_frame = tk.Frame(self.root, bg='#05001c')
        button_frame.pack(expand=True)

        # Mode buttons with descriptions
        modes = [
            ("3D Demo", "Prototype version of GUI with 3D graph", self.launch_3d_demo),
            ("Full Demo", "Full version of GUI with full features", self.launch_full_demo),
            ("Choreography", "Optimized for running Choreography", self.launch_choreography),
            ("Basic", "Simple demonstration, minimal features", self.launch_basic_controls),
            ("CSV Visualizer", "View recorded flight data", self.launch_visualizer)
        ]

        for text, description, command in modes:
            btn_frame = tk.Frame(button_frame, bg='#05001c')
            btn_frame.pack(pady=10)

            btn = tk.Button(btn_frame, text=text, command=command, **button_style)
            btn.pack()
            # Hover effects
            btn.bind("<Enter>", lambda e: e.widget.config(bg='#d098fa'))
            btn.bind("<Leave>", lambda e: e.widget.config(bg='#e61848'))

            desc_label = tk.Label(
                btn_frame,
                text=description,
                font=('Helvetica', 8),
                bg='#05001c',
                fg='#3fd4ff',
                pady=5
            )
            desc_label.pack()

    def launch_3d_demo(self):
        self.root.destroy()
        print("Running 3D demo")
        app = SwarmGUI(mode="3d", connected=self.connected)
        app.run()

    def launch_full_demo(self):
        self.root.destroy()
        print("Running full demo")
        app = SwarmGUI(mode="full", connected=self.connected)
        app.run()

    def launch_choreography(self):
        self.root.destroy()
        print("Running choreography demo")
        app = SwarmGUI(mode="choreo", connected=self.connected)
        app.run()

    def launch_basic_controls(self):
        self.root.destroy()
        print("Running basic demo")
        app = SwarmGUI(mode="basic", connected=self.connected)
        app.run()

    def launch_visualizer(self):
        self.root.destroy()
        app = SwarmGUI(mode="visualize", connected=self.connected)
        app.run()

    def run(self):
        self.root.mainloop()

app = LaunchScreen()
app.run()

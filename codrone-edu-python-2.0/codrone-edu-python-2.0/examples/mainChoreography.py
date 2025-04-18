from codrone_edu.swarm import *
import sys
import time
import math
import asyncio


class MainChoreo:
    def __init__(self, gui_instance):
        self.gui = gui_instance
        self.speed = 0.75
        self.base_height = 0.8  # Height for square formation
        self.pyramid_base_height = 0.3  # Height for bottom layer of pyramid
        self.pyramid_top_height = 1.0  # Height for top of pyramid
        self.square_sides = 1.4
        self.pyramid_side = 1.4
        self.space_apart = 0.4


    '''
    Starting position
    - - B
    - R - 
    Y - G
    '''
    def square_takeoff(self, drones, selected_drone_indices):
        """
        Takes off and holds position in a square formation
        Square is 1m x 1m with drones at the corners
        """
        print("Taking off into square formation...")
        s = self.square_sides / 2
        self.gui.take_off()
        # Square corner positions (x, y, z) in meters
        '''
        R - B
        -   -
        Y - G
        '''
        square_positions = [
            (s, s, self.base_height),  # Front left, 0: red
            (s, -s, self.base_height),  # Front Right, 1: blue
            (-s, -s, self.base_height),  # Back Right, 2: green
            (-s, s, self.base_height),  # Back left, 3: yellow
        ]

        if len(selected_drone_indices) != 4:
            print("This choreography requires exactly 4 drones")
            return

        # Move each drone to its corner position
        for i, drone_index in enumerate(selected_drone_indices):
            pos = square_positions[i]
            self.gui.goto_position(drone_index, pos[0], pos[1], pos[2], self.speed)
            time.sleep(0.5)  # Wait between each drone's movement
        # self.gui.stabilize_swarm()
        time.sleep(3)  # Hold square formation
        print("Square formation complete")

    def form_pyramid(self, drones, selected_drone_indices):
        """
        Rearranges drones from square into a tetrahedral pyramid
        Three drones form the base triangle, one drone at the top
        """
        print("Transforming into pyramid formation...")

        p = self.pyramid_side
        # Pyramid positions (x, y, z) in meters
        '''
        R - B
        - Y -
        - G -
        '''
        pyramid_positions = [
            (p/2, p * math.sqrt(3)/2, self.pyramid_base_height),  # Upper left triangle
            (p/2, -p * math.sqrt(3)/2, self.pyramid_base_height),  # Upper right triangle
            (-p, 0, self.pyramid_base_height),  # Lower tip triangle
            (0, 0, self.pyramid_top_height)  # Top of pyramid
        ]

        # Move drones to pyramid positions simultaneously
        for i, drone_index in enumerate(selected_drone_indices):
            pos = pyramid_positions[i]
            self.gui.goto_position(drone_index, pos[0], pos[1], pos[2], self.speed)

        time.sleep(5)  # Hold pyramid formation
        print("Pyramid formation complete")

    def move_into_place(self, drones, selected_drone_indices):
        print("moving into a line")
        # order: 1, 3, 2
        b = self.pyramid_base_height
        '''
        R - Y - G - B
        '''
        drone_positions = [
            (0, self.space_apart, b),  # Red
            (0, 2 * self.space_apart, b),  # Blue
            (0, -self.space_apart, b),  # Green
            (0, 0, b)  # Yellow
        ]

        for i, drone_index in enumerate(selected_drone_indices):
            pos = drone_positions[i]
            self.gui.goto_position(drone_index, pos[0], pos[1], pos[2], self.speed)

    def standing_wave(self, swarm, selected_drone_indices):
        sync = Sync()

        for i in selected_drone_indices:
            seq = Sequence(i)
            drone = self.gui.droneIcons[i]
            seq.add('send_absolute_position', drone["x_position"], drone["y_position"], 0.6, 1, 0, 0)
            if i % 2 == 1:
                for j in range(3):
                    seq.add('send_absolute_position', drone["x_position"], drone["y_position"], 0.8, 1, 0, 0)
                    seq.add('send_absolute_position', drone["x_position"], drone["y_position"], 0.4, 1, 0, 0)
            else:
                for j in range(3):
                    seq.add('send_absolute_position', drone["x_position"], drone["y_position"], 0.4, 1, 0, 0)
                    seq.add('send_absolute_position', drone["x_position"], drone["y_position"], 0.8, 1, 0, 0)
            sync.add(seq)

        swarm.run(sync)

        # Prints all the steps in the sequence for drone 0
        for i in sync.get_sync()[0]:
            print(i)

    def spiral_down(self, swarm, selected_drone_indices):
        sync = Sync()
        for i in selected_drone_indices:
            seq = Sequence(i)
            seq.add('set_throttle', -20)
            seq.add('set_pitch', 40)
            seq.add('set_yaw', 80)
            seq.add('move', 4)
            seq.add('land')
            sync.add(seq)
        swarm.run(sync)

    def run_sequence(self, swarm, selected_drone_indices):
        """Entry point for the choreography"""
        try:
            # Store swarm reference
            self.swarm = swarm

            # Get only the selected drones
            drones = [swarm.get_drones()[i] for i in selected_drone_indices]

            if len(drones) != 4:
                print("Please select exactly 4 drones for this choreography")
                return
            self.gui.update_timer()
            print(f"Starting choreography with {len(drones)} drones...")

            self.square_takeoff(drones, selected_drone_indices)
            time.sleep(1)  # Pause between formations
            self.form_pyramid(drones, selected_drone_indices)
            swarm.land()
            # time.sleep(1)  # Pause between formations
            # self.move_into_place(drones, selected_drone_indices)
            # time.sleep(1)  # Pause between formations
            # self.standing_wave(swarm, selected_drone_indices)
            # time.sleep(1)  # Pause between formations
            # self.spiral_down(swarm, selected_drone_indices)

        except Exception as e:
            print(f"Failed to run choreography: {str(e)}")

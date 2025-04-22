from codrone_edu.swarm import *
import sys
import time
import math
import asyncio

class Pyramid:
    def __init__(self, gui_instance):
        self.gui = gui_instance
        self.speed = 0.75
        self.pyramid_base_height = 0.3  # Height for bottom layer of pyramid
        self.pyramid_top_height = 1.0  # Height for top of pyramid
        self.square_sides = 1.4
        self.pyramid_side = 1.4

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
        print("Pyramid formation complete")

    def run_sequence(self, swarm, selected_drone_indices):
        try:
            self.swarm = swarm

            # Get only the selected drones
            drones = [swarm.get_drones()[i] for i in selected_drone_indices]

            if len(drones) != 4:
                print("Please select exactly 4 drones for this choreography")
                return
            self.gui.update_timer()
            print(f"Starting choreography with {len(drones)} drones...")
            self.form_pyramid(drones, selected_drone_indices)

        except Exception as e:
            print(f"Failed to run choreography: {str(e)}")

from codrone_edu.swarm import *
import sys
import time
import asyncio

class MainChoreo:
    def __init__(self, gui_instance):
        self.gui = gui_instance
        self.speed = 0.75
        self.base_height = 0.75  # Height for square formation
        self.pyramid_base_height = 0.5  # Height for bottom layer of pyramid
        self.pyramid_top_height = 1.5  # Height for top of pyramid
        self.square_sides = 0.5
        self.pyramid_side = 0.5

    def square_takeoff(self, drones, selected_drone_indices):
        """
        Takes off and holds position in a square formation
        Square is 1m x 1m with drones at the corners
        """
        print("Taking off into square formation...")
        s = self.square_sides / 2
        self.gui.take_off()
        # Square corner positions (x, y, z) in meters
        square_positions = [
            (-s, s, self.base_height),  # Front Left
            (s, s, self.base_height),  # Front Right
            (s, -s, self.base_height),  # Back Right
            (-s, -s, self.base_height),  # Back Left
        ]

        if len(selected_drone_indices) != 4:
            print("This choreography requires exactly 4 drones")
            return

        # Move each drone to its corner position
        for i, drone_index in enumerate(selected_drone_indices):
            pos = square_positions[i]
            self.gui.goto_position(drone_index, pos[0], pos[1], pos[2], self.speed)
            time.sleep(0.5)  # Wait between each drone's movement

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
        pyramid_positions = [
            (p / 2, p / 2, self.pyramid_base_height),  # Upper right triangle
            (0, 0, self.pyramid_top_height),  # Top of pyramid
            (0, p / 2 - (0.866025405 * p), self.pyramid_base_height),  # Lower tip triangle
            (-p / 2, p / 2, self.pyramid_base_height),  # Upper left triangle
        ]

        # Move drones to pyramid positions simultaneously
        for i, drone_index in enumerate(selected_drone_indices):
            pos = pyramid_positions[i]
            self.gui.goto_position(drone_index, pos[0], pos[1], pos[2], self.speed)

        time.sleep(5)  # Hold pyramid formation
        print("Pyramid formation complete")

    def move_into_place(self, drones, selected_drone_indices):
        print("moving into a line")
    
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
            print("Choreography completed successfully!")

        except Exception as e:
            print(f"Failed to run choreography: {str(e)}")

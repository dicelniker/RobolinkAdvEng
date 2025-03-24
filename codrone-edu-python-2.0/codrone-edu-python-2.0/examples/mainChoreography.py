from codrone_edu.swarm import *


class MainChoreo:
    def __init__(self, gui_instance):
        self.gui = gui_instance
        self.speed = 0.75
        self.base_height = 0.75  # Height for square formation
        self.pyramid_base_height = 0.5  # Height for bottom layer of pyramid
        self.pyramid_top_height = 1.5  # Height for top of pyramid

    async def square_takeoff(self, drones, selected_drone_indices):
        """
        Takes off and holds position in a square formation
        Square is 1m x 1m with drones at the corners
        """
        print("Taking off into square formation...")

        # Square corner positions (x, y, z) in meters
        square_positions = [
            (-0.5, 0.5, self.base_height),  # Front Left
            (0.5, 0.5, self.base_height),  # Front Right
            (0.5, -0.5, self.base_height),  # Back Right
            (-0.5, -0.5, self.base_height),  # Back Left
        ]

        if len(selected_drone_indices) != 4:
            print("This choreography requires exactly 4 drones")
            return

        # Move each drone to its corner position
        for i, drone_index in enumerate(selected_drone_indices):
            pos = square_positions[i]
            self.gui.goto_position(drone_index, pos[0], pos[1], pos[2], self.speed)
            await asyncio.sleep(1)  # Wait between each drone's movement

        await asyncio.sleep(3)  # Hold square formation
        print("Square formation complete")

    async def form_pyramid(self, drones, selected_drone_indices):
        """
        Rearranges drones from square into a tetrahedral pyramid
        Three drones form the base triangle, one drone at the top
        """
        print("Transforming into pyramid formation...")

        # Pyramid positions (x, y, z) in meters
        pyramid_positions = [
            (0.5, 0.5, self.pyramid_base_height), # Upper right base
            (0, 0, self.pyramid_top_height),  # Top middle
            (0, -0.37, self.pyramid_base_height),  # Bottom base
            (-0.5, 0.5, self.pyramid_base_height),  # Base Back
        ]

        # Move drones to pyramid positions simultaneously
        for i, drone_index in enumerate(selected_drone_indices):
            pos = pyramid_positions[i]
            self.gui.goto_position(drone_index, pos[0], pos[1], pos[2], self.speed)

        await asyncio.sleep(5)  # Hold pyramid formation
        print("Pyramid formation complete")

    async def async_run_sequence(self, swarm, selected_drone_indices):
        """Main choreography sequence"""
        drones = swarm.get_drones()
        if len(selected_drone_indices) != 4:
            print("Please select exactly 4 drones for this choreography")
            return

        print(f"Starting choreography with {len(selected_drone_indices)} drones...")

        try:
            # Execute the sequence
            await self.square_takeoff(drones, selected_drone_indices)
            await asyncio.sleep(1)  # Pause between formations
            await self.form_pyramid(drones, selected_drone_indices)
            print("Choreography completed successfully!")

        except Exception as e:
            print(f"Error during choreography: {str(e)}")

    def run_sequence(self, swarm, selected_drone_indices):
        """Entry point for the choreography"""
        asyncio.run(self.async_run_sequence(swarm, selected_drone_indices))

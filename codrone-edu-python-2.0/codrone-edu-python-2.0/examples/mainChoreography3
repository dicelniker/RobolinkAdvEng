from codrone_edu.swarm import *
import sys
import time
import math
import asyncio


class MainChoreo:
    def __init__(self, gui_instance):
        self.gui = gui_instance


    '''
    Starting position
    B - G
    - R -
    
    R (0, 0, 0)
    B (1/2, math.sqrt(3)/2, 0)
    G (1/2, -1 * math.sqrt(3)/2, 0)
    '''

    def form_triangle(self):
        self.gui.take_off()
        '''
        B - G
        - - -
        - R -
        '''
        print("Forming a triangle...")
        self.gui.goto_position(0, -1, 0, 0.8)
        print("Line formation complete")
    def form_line(self):
        '''
        B R G
        '''
        print("Forming a line...")
        self.gui.goto_position(0, 0, 1/2, 0.8)
        print("Line formation complete")

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

    def run_sequence(self, swarm, selected_drone_indices):
        """Entry point for the choreography"""
        try:
            # Store swarm reference
            self.swarm = swarm

            # Get only the selected drones
            drones = [swarm.get_drones()[i] for i in selected_drone_indices]

            self.gui.update_timer()
            print(f"Starting choreography with {len(drones)} drones...")

            self.form_triangle()
            time.sleep(1)
            self.form_line()
            time.sleep(1)
            self.standing_wave(swarm, selected_drone_indices)
            swarm.land()

        except Exception as e:
            print(f"Failed to run choreography: {str(e)}")

from codrone_edu.drone import *
drone = Drone()
drone.pair()

notes = [Note.B3, Note.C4, Note.E3, Note.G3,
         Note.B3, Note.C4, Note.E3, Note.G3, Note.F3,
         Note.B3, Note.C4, Note.E3, Note.G3,
         Note.B3, Note.C4, Note.E3, Note.G3, Note.F3,
         Note.D3, Note.E3, Note.F3, Note.F3, Note.E3]

durations = [417, 417, 417, 417*4,
             417, 417, 417, 417*2, 417*3,
             417, 417, 417, 417*4,
             417, 417, 417, 417*2, 417*3,
             417, 417, 417, 417 * 2, 417 * 6]

for i in range(len(notes)):
    drone.drone_buzzer(notes[i], durations[i])


drone.close()
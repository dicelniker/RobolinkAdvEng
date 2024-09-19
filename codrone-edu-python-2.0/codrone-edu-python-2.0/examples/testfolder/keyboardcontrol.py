import keyboard
from codrone_edu.drone import *
import time

drone = Drone()
drone.pair()

def noMove():
	drone.set_throttle(0)
	drone.set_roll(0)
	drone.set_yaw(0)
	drone.set_pitch(0)

def right(degrees):
    z_angle = drone.get_z_angle()
    while z_angle > -90:
        drone.set_yaw(20)
        drone.move()
        z_angle = drone.get_z_angle()

def left(degrees):
    z_angle = drone.get_z_angle()
    while z_angle < 90:
        drone.set_yaw(-20)
        drone.move()
        z_angle = drone.get_z_angle()

while True:

	print(str(drone.get_angular_speed_z()) + " " + str(drone.get_z_angle()))

	if keyboard.read_key() == "1":
		drone.takeoff()
	if keyboard.read_key() == "0":
		drone.land()

	drone.move(0.005)

	if keyboard.read_key() == "backspace":
		break
	elif keyboard.read_key() == "w":
		drone.set_pitch(20)
	elif keyboard.read_key() == "a":
		drone.set_roll(-20)
	elif keyboard.read_key() == "s":
		drone.set_roll(20)
	elif keyboard.read_key() == "d":
		drone.set_pitch(-20)
	elif keyboard.read_key() == "q":
		left(2)
	elif keyboard.read_key() == "e":
		right(2)
	elif keyboard.read_key() == "z":
		drone.set_throttle(20)
	elif keyboard.read_key() == "x":
		drone.set_throttle(-20)
	elif keyboard.read_key() == "i":
		drone.flip("front")
		sleep(3)
	elif keyboard.read_key() == "j":
		drone.flip("left")
	elif keyboard.read_key() == "k":
		drone.flip("back")
	elif keyboard.read_key() == "l":
		drone.flip("right")
	else:
		if(drone.get_angular_speed_z() > 0):
			drone.set_yaw(5)
		if (drone.get_angular_speed_z() < 0):
			drone.set_yaw(-5)
		noMove()

drone.land()
drone.close()
from serial.tools import list_ports
from codrone_edu.drone import *
from time import sleep
from threading import Thread, Lock

class Swarm2():

    count = 0

    def __init__(self):
        self.drone_objects = []
        self.num_drones = 0
        self.print_lock = Lock()

    def connect(self):
        x = list(list_ports.comports(include_links=True))
        portnames = []

        def check_port(element):
            if element.vid == 1155 or element.vid == 6790:
                portname = element.device
                with self.print_lock:
                    print("Detected: ", portname)
                portnames.append(str(portname))

        threads = []
        for element in x:
            thread = Thread(target=check_port, args=(element,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        self.num_drones = len(portnames)

        count = self.num_drones

        def create_drone(index):
            self.drone_objects.append(Drone())

        threads = []
        for i in range(self.num_drones):
            thread = Thread(target=create_drone, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        threads = []
        for i in range(self.num_drones):
            thread = Thread(target=self._connect_drone, args=(i, portnames[i]))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        return count

    def _connect_drone(self, index, portname):
        self.drone_objects[index].pair(portname)
        # with self.print_lock:
        #     print("Connected to CoDrone EDU at port ", portname)

    def all_drones(self, method_name, *args, **kwargs):
        def call_method(drone):
            method = getattr(drone, method_name, None)
            if callable(method):
                method(*args, **kwargs)
            else:
                with self.print_lock:
                    print("Method ", method_name, " not found")

        threads = []
        for drone in self.drone_objects:
            thread = Thread(target=call_method, args=(drone,))
            thread.start()
            threads.append(thread)


        for thread in threads:
            thread.join()

    def drone_positions(self, positions, velocity):

        def runposition(drone,*args):

            method = getattr(drone, "send_absolute_position", None)
            if callable(method):
                method(*args)

        threads = []
        for drone, i in zip(self.drone_objects, positions):
            thread = Thread(target=runposition, args=(drone, i[0], i[1], i[2], velocity, 0, 0))
            thread.start()
            threads.append(thread)
            print("Command Sent!")
            timer = time.time()

        sleep(0.2)

        for thread in threads:
            thread.join()
            print("Execution Time: ", time.time()-timer)

    def drone_color(self,index,r,g,b):
        self.drone_objects[index].set_drone_LED(r, g, b, 100)
        return

    def swarm_size(self):
        return self.count

    def close(self):
        for drone in self.drone_objects:
            drone.close()

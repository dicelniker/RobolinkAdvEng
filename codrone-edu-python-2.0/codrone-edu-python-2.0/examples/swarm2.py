from serial.tools import list_ports
from codrone_edu.drone import *
from time import sleep
from threading import Thread, Lock

# The CustomThread class inherits from Thread class to include the ability to return a value from thread
class CustomThread(Thread):
    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs=None):

        if kwargs is None:
            self._kwargs = None
        else:
            self._kwargs = kwargs

        # execute the base constructor
        Thread.__init__(self, group, target, name, args, kwargs)
        # set default values
        self._return = None
        self._target = target
        self._args = args

    # This function will override run() method from Thread class, which is called by start()
    def run(self):
        if self._target is not None:
            self._return = self._target(*self._args,
                                        **self._kwargs)

    # This function will override join() method from Thread class
    def join(self, timeout = None):
        Thread.join(self, timeout = None)
        return self._return

class Swarm2:

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

    def _connect_drone(self, index, portname):
        self.drone_objects[index].pair(portname)
        # with self.print_lock:
        #     print("Connected to CoDrone EDU at port ", portname)

    def all_drones(self, method_name, *args, **kwargs):
        results = []

        def call_method(drone):
            method = getattr(drone, method_name, None)
            if callable(method):
                value = method(*args, **kwargs)
                # if method is a return function
                if value is not None:
                    return value
            else:
                with self.print_lock:
                    print("Method ", method_name, " not found")

        threads = []
        for drone in self.drone_objects:
            # This CustomThread object will be able to return a value from 'call_method' once .join() is called
            thread = CustomThread(target=call_method, args=(drone,))
            thread.start()
            threads.append(thread)


        for thread in threads:
            result = thread.join() # ignore PyCharm warning about 'join' not returning anything

            # This will apply to functions like '.get_position_data()', '.get_battery()' and appends result from each Drone object
            if result is not None:
                results.append(result)


        # Essentially, return None if the method_name is a void function
        if len(results) == 0:
            return None

        # Return list of drone data if the method_name is a return function
        return results

    # This function will call Drone method for only one Drone object
    def one_drone(self, drone, method_name, *args, **kwargs):
        def call_method(drone):
            method = getattr(drone, method_name, None)
            if callable(method):
                value = method(*args, **kwargs)
                if value is not None:
                    return value
                return None
            else:
                with self.print_lock:
                    print("Method ", method_name, " not found")

        return call_method(drone)

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

    def get_drone_objects(self):
        return self.drone_objects

    def drone_color(self):
        return

    def swarm_size(self):
        return Swarm2.count

    def close(self):
        for drone in self.drone_objects:
            drone.close()
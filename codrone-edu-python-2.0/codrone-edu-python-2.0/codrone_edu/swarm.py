import importlib.metadata
from serial.tools import list_ports
from colorama import Fore, Back, Style
from codrone_edu.drone import *
from time import sleep
import asyncio

class Swarm:
    def __init__(self, enable_color=True, enable_print=True, enable_pause=True):
        self._enable_color = enable_color
        self._enable_print = enable_print
        self._enable_pause = enable_pause
        self._drone_objects = []
        self._num_drones = 0
        self._print_lock = asyncio.Lock()
        self._portnames = []
        self._led_colors = ['red', 'blue', 'orange', 'yellow', 'green', 'light blue', 'purple', 'pink', 'white', 'black']
        self._rgb_colors = [[255, 0, 0, 255],[25, 116, 210, 255],[255, 140, 0, 255],[255, 255, 0, 255],[0, 255, 0, 255],[172, 229, 238, 255],
                        [255, 0, 255, 255],[255, 255, 255, 255],[0, 0, 0, 255]]

    def __getattr__(self, item, *args, **kwargs):

        def call_method(*args, **kwargs):
            return self.all_drones(item, *args, **kwargs)

        return call_method

    ## Swarm Connect Start ##
    async def _connect(self):
        x = list(list_ports.comports(include_links=True))

        async def check_port(element):
            async with self._print_lock:
                if element.vid == 1155 or element.vid == 6790:
                    portname = element.device
                    self._portnames.append(str(portname))

        await asyncio.gather(*(check_port(element) for element in x))

        self._num_drones = len(self._portnames)

        async def create_drone():
            self._drone_objects.append(Drone(swarm=True))

        await asyncio.gather(*(create_drone() for _ in range(self._num_drones)))

        colorama.init()
        library_name = "codrone-edu"
        library = importlib.metadata.distribution(library_name).version
        print(Fore.GREEN + f"Running {library_name} library version {library}" + Style.RESET_ALL)

        await asyncio.gather(*(self._initialize_drone(i) for i in range(self._num_drones)))

        await asyncio.gather(*(self._connect_drone(i, self._portnames[i]) for i in range(self._num_drones)))

    def connect(self):
        asyncio.run(self._connect())
        if self._enable_print and self._enable_color:
            print()
            for i in range(self._num_drones):
                print(Fore.GREEN + f"Drone {i} at port {self._portnames[i]}: {self._led_colors[i]}" + Style.RESET_ALL)
        if self._enable_pause:
            input("Press Enter to start swarm...")


    async def _connect_drone(self, index, portname):
        await self._drone_objects[index].pair(portname)
        if self._enable_color:
            await self._drone_objects[index].set_drone_LED(*self._rgb_colors[index])
            await self._drone_objects[index].set_controller_LED(*self._rgb_colors[index])

    async def _initialize_drone(self, index):
        await self._drone_objects[index].initialize_data()

    ## Swarm Connect End ##

    async def __call_method(self, index, commands):
        drone = self._drone_objects[index]
        method_name = commands[0]
        args = commands[1]
        kwargs = commands[2]
        method = getattr(drone, method_name, None)
        if callable(method):
            try:
                return await method(*args, **kwargs)
            except TypeError:
                return method(*args, **kwargs)  # this is the case for non-async functions like set_yaw
        else:
            async with self._print_lock:
                print("Method ", method_name, " not found")
                return

    ## Basic Swarm Start ##
    async def _all_drones(self, method_name, *args, **kwargs):
        commands = [method_name, args, kwargs]

        results = await asyncio.gather(*(self.__call_method(i, commands) for i in range(self._num_drones)))

        return results

    def all_drones(self, method_name, *args, **kwargs):
        return asyncio.run(self._all_drones(method_name, *args, **kwargs))

    async def _one_drone(self, index, method_name, *args, **kwargs):
        commands = [method_name, args, kwargs]

        # without subscript, returns a list of actual value, which we don't need since it's only one drone
        # with subscript, just returns the actual value from drone function
        return (await asyncio.gather(self.__call_method(index, commands)))[0]

    def one_drone(self, index, method_name, *args, **kwargs):
        return asyncio.run(self._one_drone(index, method_name, *args, **kwargs))

    # wrapper function for one_drone()
    def run_drone(self, index, method_name, *args, **kwargs):
        return self.one_drone(index, method_name, *args, **kwargs)

    ## Basic Swarm End ##


    ## Run Sync Start ##
    # Slightly different functionality than _one_drone, this runs multiple commands for one drone
    async def _run_one_drone(self, index, commands, max_num_commands):
        return_values = []
        for com in commands:
            return_value = await self.__call_method(index, com)
            return_values.append(return_value)

        reset_command = ['reset_move_values', (), {}]
        await self.__call_method(index, reset_command)

        # number of None values to append to make list for each drone the same length, necessary to transpose 2D list in _run()
        n_blank = abs(len(commands) - max_num_commands)

        for _ in range(n_blank):
            return_values.append(None)

        return return_values

    async def _run(self, sync_obj, type="parallel", delay=None, order=None):

        sync_tasks = sync_obj.get_sync()
        num_synced = len(sync_tasks)  # number of drones involved in sync
        max_steps = sync_obj.get_max_num_steps()  # gets max number of tasks to perform out of all the synced drones

        if num_synced > self._num_drones:
            await self._all_drones('land')
            await self._disconnect()
            raise Exception('Number of drones required for sync is higher than number of drones connected!')


        if order is not None:
            if len(order) > max_steps:
                await self._all_drones('land')
                await self._disconnect()
                raise Exception('len(order) is greater than the max number of tasks in sync')

        if (type == "sequential") and (num_synced > 1):
            if delay is None:
                delay = 0

            if order is None:
                # if no order is specified, the order will go by increasing drone index
                # order = [
                # [0,1,2,...,n-1], method_name1
                # [0,1,2,...,n-1], method_name2
                # ...,
                # [0,1,2,...,n-1] method_namei
                # ]
                order = [[i for i in range(num_synced)] for _ in range(max_steps)]

            return_values = []

            for i in range(max_steps):

                temp_return_values = []

                for index in order[i]:

                    if i <= len(sync_tasks[index]) - 1:
                        method_name = sync_tasks[index][i][0]
                        args = sync_tasks[index][i][1]
                        kwargs = sync_tasks[index][i][2]

                    # if drone doesn't have any more scheduled tasks, it will just hover
                    else:
                        method_name = 'reset_move_values'
                        args = []
                        kwargs = {}

                    return_value = await self._one_drone(index, method_name, *args, **kwargs)
                    temp_return_values.append(return_value)
                    time.sleep(delay)

                return_values.append(temp_return_values)

            return return_values
        # run if type="parallel", each drone will perform their sequence individually
        else:
            tasks = []

            for index, commands in sync_tasks.items():
                task = asyncio.create_task(self._run_one_drone(index, commands, max_steps))
                tasks.append(task)

            return_values = await asyncio.gather(*tasks)

            transposed_return_values = [list(row) for row in zip(*return_values)]
            return transposed_return_values

    def run(self, sync_obj, type="parallel", delay=None, order=None):
        return asyncio.run(self._run(sync_obj, type, delay, order))

    ## Run Sync End ##

    def get_drones(self):
        return self._drone_objects

    async def _disconnect_drone(self, index):
        await self._drone_objects[index].disconnect()

    async def _disconnect(self):
        await asyncio.gather(*(self._disconnect_drone(i) for i in range(self._num_drones)))

    def close(self):
        asyncio.run(self._disconnect())

    def disconnect(self):
        asyncio.run(self._disconnect())


## Sync Class Start ##
class Sync:
    def __init__(self, *args):
        self._sync = {}
        # should look like this:
        # {0: [[method_name1,args1,kwargs1], [method_name2,args2,kwargs2]],
        #  1: [[method_name1,args1,kwargs1]],
        #  2: [[method_name1,args1,kwargs1], [method_name2,args2,kwargs2], [method_name3,args3,kwargs3]]}

        # process variable number of sequences and store into self._sync
        for sequence_obj in args:
            sequence_dict = sequence_obj.get_sequence()
            sequence = list(sequence_dict.items()) # convert dictionary iterable into list of key-val tuples
            index, method_list = sequence[0][0], sequence[0][1]
            for method in method_list:
                if index not in self._sync:
                    self._sync[index] = [method]
                else:
                    self._sync[index].append(method)

    def add(self, sequence_obj):
        sequence_dict = sequence_obj.get_sequence()
        sequence = list(sequence_dict.items())  # convert dictionary iterable into list of key-val tuples
        index, method_list = sequence[0][0], sequence[0][1]
        for method in method_list:
            if index not in self._sync:
                self._sync[index] = [method]
            else:
                self._sync[index].append(method)

    def get_sync(self):
        return self._sync

    def get_size(self):
        return len(self._sync)

    def get_max_num_steps(self):
        max_steps = 0
        if len(self._sync) > 0:
            for k,v in self._sync.items():
                curr_steps = len(v)
                if curr_steps > max_steps:
                    max_steps = curr_steps
            return max_steps
        else:
            return 0

## Sync Class End ##

## Sequence Class Start ##
class Sequence:
    def __init__(self, index):
        self.index = index
        self._sequence = {index: []}
        # should look like this:
        # {0: [[method_name1,args1,kwargs1], [method_name2,args2,kwargs2]]}

    def add(self, method_name, *args, **kwargs):
        self._sequence[self.index].append([method_name, args, kwargs])

    def get_sequence(self):
        return self._sequence

## Sequence Class End ##

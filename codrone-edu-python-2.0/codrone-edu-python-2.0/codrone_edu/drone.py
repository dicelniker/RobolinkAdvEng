
import importlib.metadata
# import queue

import sys
import os
import asyncio
import warnings
import base64

import time
from time import sleep

from struct import *
from queue import Queue

import colorama
from colorama import Fore, Back, Style
import PIL.Image
import PIL.ImageDraw
import numpy as np

if sys.platform != 'emscripten': # Desktop environment
    import serial
    import threading
    from threading import Thread
    import binascii
    import random
    import queue
    from serial.tools.list_ports import comports
    from operator import eq
    # from pynput import keyboard
    import signal
else: # Web environment
    import js
    from js import navigator, Uint8Array
    from pyodide.ffi import to_js
    from io import BytesIO
    from codrone_edu.tools.interrupter import *

from codrone_edu.protocol import *
from codrone_edu.storage import *
from codrone_edu.receiver import *
from codrone_edu.system import *
from codrone_edu.crc import *
# from pynput import keyboard
import signal

def convertByteArrayToString(dataArray):
    if dataArray == None:
        return ""

    string = ""

    if (isinstance(dataArray, bytes)) or (isinstance(dataArray, bytearray)) or (not isinstance(dataArray, list)):
        for data in dataArray:
            string += "{0:02X} ".format(data)

    return string

def format_firmware_version(version):
    if (version is None) or (version.major is None or version.minor is None or version.build is None):
        return ""
    
    return "{0}.{1}.{2} ".format(
        version.major,
        version.minor,
        version.build)

def temperature_convert(temp, conversion="F"):
    """
    Converts the given temperature to Fahrenheit or Celsius
    :param temp:current temperature
    :param conversion: (C) Celcius or (F) Fahrenheit
    :return: converted temperature
    """
    if conversion == "F":
        return round((temp * 9 / 5) + 32, 3)
    elif conversion == "C":
        return round((temp - 32) * 5 / 9, 3)
    else:
        print("Conversion must be (F) or (C).")

def j(obj):
    return to_js(obj, dict_converter=js.Object.fromEntries)

original_asyncio_sleep = asyncio.sleep

async def interruptible_sleep(duration):
    interval = 0.1
    elapsed = 0.0

    while elapsed < duration:
        await original_asyncio_sleep(min(interval, duration - elapsed))
        checkInterrupt()
        elapsed += interval

# Overwrite asyncio.sleep with the custom function
asyncio.sleep = interruptible_sleep

class Drone:

    # def __on_press(self, key):
    #     """
    #     checks for key press on keyboard
    #     :param key: the key that is pressed
    #     :return: False to stop listener if esc pressed
    #     """
    #     if key == keyboard.Key.esc:
    #         try:
    #             self.emergency_stop()
    #         finally:
    #             os.kill(os.getpid(), signal.SIGTERM)
    #             # stop listener
    #             return False

    # def __listen(self):
    #     """
    #     starts the keyboard listener
    #     :return: None
    #     """
    #     listener = keyboard.Listener(on_press=self.__on_press)
    #     listener.start()

    def __button_event(self, button):
        """
        Stores any button press event with a time stamp
        :param button:
        :return: N/A
        """
        self.button_data[0] = time.time() - self.timeStartProgram
        self.button_data[1] = button.button
        self.button_data[2] = button.event.name

    # BaseFunctions Start

    def __init__(self, flagCheckBackground=True, flagShowErrorMessage=False, flagShowLogMessage=False,
                 flagShowTransferData=False, flagShowReceiveData=False, swarm=False):

        self._serialport = None
        self._bufferQueue = Queue(4096)
        self._bufferHandler = bytearray()
        self._index = 0

        if sys.platform != 'emscripten':
            self._thread = None
        else:
            self._writer = None
            self._reader = None
            self.roll_pitch_callback = None
            self.speed_callback = None

        if swarm:
            self._swarm = True
            asyncio.sleep = original_asyncio_sleep
        else:
            self._swarm = False

        self._flagThreadRun = False

        self._receiver = Receiver()

        self._flagCheckBackground = flagCheckBackground

        self._flagShowErrorMessage = flagShowErrorMessage
        self._flagShowLogMessage = flagShowLogMessage
        self._flagShowTransferData = flagShowTransferData
        self._flagShowReceiveData = flagShowReceiveData

        self._eventHandler = EventHandler()
        self._storageHeader = StorageHeader()
        self._storage = Storage()
        self._storageCount = StorageCount()
        self._parser = Parser()

        self._devices = []  # Save a list of discovered devices when you autoconnect
        self._flagDiscover = False  # Indicate if the device is being scanned for autoconnect
        self._flagConnected = False  # Lets you know if you're connected to a device when you connect automatically
        self._address = []
        self._cpuId = []
        self._battery = 0

        self.timeStartProgram = time.time()  # Program Start Time Recording

        self.systemTimeMonitorData = 0
        self.monitorData = []
        self.information_data = [0.0, 0, "", 0,""]  # timestamp, Drone model, drone firmware, controller model, controller firmware
        self.address_data = [0.0, 0, 0]  # timestamp, Drone address, controller address
        self.altitude_data = [0, 0, 0, 0, 0]
        self.motion_data = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        self.raw_motion_data = [0, 0, 0, 0, 0, 0, 0]  # timestamp, rawAccelX, rawAccelY, rawAccelZ, rawGyroRoll, rawGyroPitch, rawGyroYaw
        self.state_data = [0, 0, 0, 0, 0, 0, 0, 0, 0]
        self.position_data = [0, 0, 0, 0]
        self.flow_data = [0, 0, 0]
        self.range_data = [0, 0, 0]
        self.joystick_data = [0, 0, 0, 0, 0, 0, 0, 0, 0]
        self.color_data = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        self.trim_data = [0, 0, 0, 0, 0]
        self.waypoint_data = []
        self.previous_land = [0, 0]
        self.button_data = [0, 0, 0]
        self.init_press = 0
        self.error_data = [0.0, 0, 0]
        self.count_data = [0.0, 0, 0, 0, 0]  # timestamp, time of flight, takeoff count, landing count, accident count
        self.cpu_id_data = [0.0, 0, 0]  # timestamp, CPU ID
        self.lostconnection_data = [0, 0]

        # set the event handlers for the sensor requests
        self.setEventHandler(DataType.Altitude, self.update_altitude_data)
        self.setEventHandler(DataType.State, self.update_state_data)
        self.setEventHandler(DataType.Motion, self.update_motion_data)
        self.setEventHandler(DataType.RawMotion, self.update_raw_motion_data)
        self.setEventHandler(DataType.Position, self.update_position_data)
        self.setEventHandler(DataType.RawFlow, self.update_flow_data)
        self.setEventHandler(DataType.Range, self.update_range_data)
        self.setEventHandler(DataType.Joystick, self.update_joystick_data)
        self.setEventHandler(DataType.CardColor, self.update_color_data)
        self.setEventHandler(DataType.Trim, self.update_trim_data)
        self.setEventHandler(DataType.Button, self.__button_event)
        self.setEventHandler(DataType.Error, self.update_error_data)
        self.setEventHandler(DataType.Information, self.update_information)
        self.setEventHandler(DataType.Address, self.receive_address_data)
        self.setEventHandler(DataType.Count, self.update_count_data)
        self.setEventHandler(DataType.CpuID, self.receive_cpu_id_data)
        self.setEventHandler(DataType.LostConnection, self.update_lostconnection_data)

        # fill values for the lists
        if not self._swarm:
            self.get_altitude_data()
            self.get_range_data()
            self.get_position_data()
            self.get_flow_data()
            self.get_state_data()
            self.get_motion_data()
            self.get_trim_data()
            self.get_color_data()
            self.get_address_data()
            self.get_information_data()
            self.get_count_data()
            self.get_cpu_id_data()
            self.get_lostconnection_data()

        # Canvas Preview
        self._canvas = None

        self.knn = ColorClassifier(n_neighbors=9)
        self.labels = []
        self.parent_dir = os.getcwd() if sys.platform != 'emscripten' else '/home/web_user/data/'

        # Threaded keyboard listener
        # self.__listen()

        for i in range(0, 36):
            self.monitorData.append(i)

        self._control = ControlQuad8()

        library_name = "codrone-edu"
        library = importlib.metadata.distribution(library_name)
        if sys.platform != 'emscripten' and not self._swarm:
            colorama.init()
            print(Fore.GREEN + f"Running {library_name} library version {library.version}" + Style.RESET_ALL)
        elif sys.platform == 'emscripten':
            print("Running {0} library version {1}".format(library_name, library.version), color="green")
        # this only works when using the release version of the library

    def __del__(self):
        if self._swarm:
            self._swarm = False
            self.disconnect()

        else:
            self.disconnect()

    def sequence_sleep(self, time):
        time.sleep(time)

    # Swarm only
    async def _initialize_data(self):
        await self.get_altitude_data()
        await self.get_range_data()
        await self.get_position_data()
        await self.get_flow_data()
        await self.get_state_data()
        await self.get_motion_data()
        await self.get_trim_data()
        await self.get_color_data()
        await self.get_address_data()
        await self.get_information_data()
        await self.get_count_data()
        await self.get_cpu_id_data()

    def initialize_data(self):
        return asyncio.create_task(self._initialize_data())
    # Swarm only end

    # Emscripten platform only
    def add_callback(self, name, callback):
        if sys.platform != 'emscripten':
            return
        if name == "roll_pitch":
            self.roll_pitch_callback = callback
        elif name == "speed":
            self.speed_callback = callback

    def _trigger_callback(self, name="roll_pitch"):
        if name == "roll_pitch" and self.roll_pitch_callback != None:
            self.roll_pitch_callback(self._control.roll, self._control.pitch)

    async def _trigger_speed_callback(self):
        self.speed_callback(await self.get_control_speed())

    def dummy_function(self):
        print("")
        return
    # Emscripten platform only End

    def get_sensor_data(self, delay=0.01):
        if sys.platform != 'emscripten' and not self._swarm:
            return self._get_sensor_data_desktop(delay)
        else:
            return asyncio.create_task(self._get_sensor_data_emscripten(delay))

    def _get_sensor_data_desktop(self, delay=0.01):
        self.sendRequest(DeviceType.Drone, DataType.Altitude)
        time.sleep(delay)
        self.sendRequest(DeviceType.Drone, DataType.Motion)
        time.sleep(delay)
        self.sendRequest(DeviceType.Drone, DataType.Position)
        time.sleep(delay)
        self.sendRequest(DeviceType.Drone, DataType.Range)
        time.sleep(delay)
        self.sendRequest(DeviceType.Drone, DataType.State)
        time.sleep(delay)

        sensor_data_list = []
        sensor_data_list = self.altitude_data + self.motion_data \
                           + self.position_data + self.range_data + self.state_data

        return sensor_data_list

    async def _get_sensor_data_emscripten(self, delay=0.01):
        await self.sendRequest(DeviceType.Drone, DataType.Altitude)
        await asyncio.sleep(delay)
        await self.sendRequest(DeviceType.Drone, DataType.Motion)
        await asyncio.sleep(delay)
        await self.sendRequest(DeviceType.Drone, DataType.Position)
        await asyncio.sleep(delay)
        await self.sendRequest(DeviceType.Drone, DataType.Range)
        await asyncio.sleep(delay)
        await self.sendRequest(DeviceType.Drone, DataType.State)
        await asyncio.sleep(delay)

        sensor_data_list = []
        sensor_data_list = self.altitude_data + self.motion_data \
                           + self.position_data + self.range_data + self.state_data
        
        return sensor_data_list

    def update_error_data(self, drone_type):
        """
        ErrorFlagsForSensor -----------------------------------------------------------

        None_                                   = 0x00000000

        Motion_NoAnswer                         = 0x00000001    # Motion 센서 응답 없음
        Motion_WrongValue                       = 0x00000002    # Motion 센서 잘못된 값
        Motion_NotCalibrated                    = 0x00000004    # Gyro Bias 보정이 완료되지 않음
        Motion_Calibrating                      = 0x00000008    # Gyro Bias 보정 중

        Pressure_NoAnswer                       = 0x00000010    # 압력 센서 응답 없음
        Pressure_WrongValue                     = 0x00000020    # 압력 센서 잘못된 값

        RangeGround_NoAnswer                    = 0x00000100    # 바닥 거리 센서 응답 없음
        RangeGround_WrongValue                  = 0x00000200    # 바닥 거리 센서 잘못된 값

        Flow_NoAnswer                           = 0x00001000    # Flow 센서 응답 없음
        Flow_WrongValue                         = 0x00002000    # Flow 잘못된 값
        Flow_CannotRecognizeGroundImage         = 0x00004000    # 바닥 이미지를 인식할 수 없음


        ErrorFlagsForState -------------------------------------------------------------

        None_                                   = 0x00000000

        NotRegistered                           = 0x00000001    # 장치 등록이 안됨
        FlashReadLock_UnLocked                  = 0x00000002    # 플래시 메모리 읽기 Lock이 안 걸림
        BootloaderWriteLock_UnLocked            = 0x00000004    # 부트로더 영역 쓰기 Lock이 안 걸림
        LowBattery                              = 0x00000008    # Low Battery

        TakeoffFailure_CheckPropellerAndMotor   = 0x00000010    # 이륙 실패
        CheckPropellerVibration                 = 0x00000020    # 프로펠러 진동발생
        Attitude_NotStable                      = 0x00000040    # 자세가 많이 기울어져 있거나 뒤집어져 있을때

        CanNotFlip_LowBattery                   = 0x00000100    # 배터리가 30이하
        CanNotFlip_TooHeavy                     = 0x00000200    # 기체가 무거움

        :param drone_type:
        :return:
        """

        self.error_data[0] = time.time() - self.timeStartProgram
        self.error_data[1] = drone_type.errorFlagsForSensor
        self.error_data[2] = drone_type.errorFlagsForState

    def update_altitude_data(self, drone_type):
        """
        temperature	Float32	4 Byte	-	temp.(℃) Celsius
        pressure	Float32	4 Byte	-	pressure (Pascals)
        altitude	Float32	4 Byte	-	Converting pressure to elevation above sea level(meters)
        rangeHeight	Float32	4 Byte	-	Height value output from distance sensor (meters)
        """

        self.altitude_data[0] = time.time() - self.timeStartProgram
        self.altitude_data[1] = drone_type.temperature
        self.altitude_data[2] = drone_type.pressure
        self.altitude_data[3] = drone_type.altitude
        self.altitude_data[4] = drone_type.rangeHeight

    def get_altitude_data(self, delay=0.01):
        if sys.platform != 'emscripten' and not self._swarm:
            return self._get_altitude_data_desktop(delay)
        else:
            return asyncio.create_task(self._get_altitude_data_emscripten(delay))

    def _get_altitude_data_desktop(self, delay=0.01):
        self.sendRequest(DeviceType.Drone, DataType.Altitude)
        time.sleep(delay)
        return self.altitude_data
    
    async def _get_altitude_data_emscripten(self, delay=0.01):
        await self.sendRequest(DeviceType.Drone, DataType.Altitude)
        await asyncio.sleep(delay)
        return self.altitude_data
    

    def get_error_data(self, delay=0.2, print_error=True):
        """
        Will get and print the current error state
        :param delay:
        :return:
        """
        if sys.platform != 'emscripten' and not self._swarm:
            return self._get_error_data_desktop(delay, print_error)
        else:
            return asyncio.create_task(self._get_error_data_emscripten(delay, print_error))

    def _get_error_data_desktop(self, delay=0.2, print_error=True):
        self.sendRequest(DeviceType.Drone, DataType.Error)
        time.sleep(delay)
        self._print_error_data(print_error)
        return self.error_data
    
    async def _get_error_data_emscripten(self, delay=0.2, print_error=True):
        await self.sendRequest(DeviceType.Drone, DataType.Error)
        await asyncio.sleep(delay)
        self._print_error_data(print_error)

        return self.error_data

    def _print_error_data(self, print_error=True):
        sensor_error_flag = self.error_data[1]
        state_error_flag = self.error_data[2]
        if print_error:
            if sensor_error_flag & ErrorFlagsForSensor.Motion_Calibrating.value:
                print("Motion_Calibrating")
            elif sensor_error_flag & ErrorFlagsForSensor.Motion_NoAnswer.value:
                print("Motion_NoAnswer")
            elif sensor_error_flag & ErrorFlagsForSensor.Motion_WrongValue.value:
                print("Motion_WrongValue")
            elif sensor_error_flag & ErrorFlagsForSensor.Motion_NotCalibrated.value:
                print("Motion_NotCalibrated")
            elif sensor_error_flag & ErrorFlagsForSensor.Pressure_NoAnswer.value:
                print("Pressure_NoAnswer")
            elif sensor_error_flag & ErrorFlagsForSensor.Pressure_WrongValue.value:
                print("Pressure_WrongValue")
            elif sensor_error_flag & ErrorFlagsForSensor.RangeGround_NoAnswer.value:
                print("RangeGround_NoAnswer")
            elif sensor_error_flag & ErrorFlagsForSensor.RangeGround_WrongValue.value:
                print("RangeGround_WrongValue")
            elif sensor_error_flag & ErrorFlagsForSensor.Flow_NoAnswer.value:
                print("Flow_NoAnswer")
            elif sensor_error_flag & ErrorFlagsForSensor.Flow_CannotRecognizeGroundImage.value:
                print("Flow_CannotRecognizeGroundImage")
            else:
                print("No sensor errors.")

            if state_error_flag & ErrorFlagsForState.NotRegistered.value:
                print("Device not registered.")
            elif state_error_flag & ErrorFlagsForState.FlashReadLock_UnLocked.value:
                print("Flash memory read lock not engaged.")
            elif state_error_flag & ErrorFlagsForState.BootloaderWriteLock_UnLocked.value:
                print("Bootloader write lock not engaged.")
            elif state_error_flag & ErrorFlagsForState.LowBattery.value:
                print("Low battery.")
            elif state_error_flag & ErrorFlagsForState.TakeoffFailure_CheckPropellerAndMotor.value:
                print("Takeoff failure. Check propeller and motor.")
            elif state_error_flag & ErrorFlagsForState.CheckPropellerVibration.value:
                print("Propeller vibration detected.")
            elif state_error_flag & ErrorFlagsForState.Attitude_NotStable.value:
                print("Attitude not stable.")
            elif state_error_flag & ErrorFlagsForState.CanNotFlip_LowBattery.value:
                print("Cannot flip. Battery below 50%.")
            elif state_error_flag & ErrorFlagsForState.CanNotFlip_TooHeavy.value:
                print("Cannot flip. Drone too heavy.")
            else:
                print("No state errors.")

    def get_pressure(self, unit="Pa"):
        '''
        requests from the drone the pressure in pascals
        parameters unit can be either
        Pascals
        Kilopascals
        milliBars
        inches per mercury
        torriceli
        atm
        :return: Returns pressure reading in set unit rounded by 2 decimal places
        '''
        if sys.platform != 'emscripten' and not self._swarm:
            return self._get_pressure_desktop(unit)
        else:
            return asyncio.create_task(self._get_pressure_emscripten(unit))

    def _get_pressure_desktop(self, unit="Pa"):
        pascals = self.get_altitude_data()[2]
        for i in range(3):
            if pascals == 0:  # check if the value is an error which would be 0
                pascals = self.get_altitude_data()[2]
            else:  # if not 0 then it is an ok value
                break
        return self._calculate_value_from_pressure(unit, pascals)

    async def _get_pressure_emscripten(self, unit="Pa"):
        pascals = (await self.get_altitude_data())[2]
        for i in range(3):
            if pascals == 0:  # check if the value is an error which would be 0
                pascals = (await self.get_altitude_data())[2]
            else:  # if not 0 then it is an ok value
                break
        return self._calculate_value_from_pressure(unit, pascals)
    
    def _calculate_value_from_pressure(self, unit, pascals):
        if unit == "Pa":
            value = pascals
        elif unit == "KPa" or unit == "kPa" or unit == "kpa":
            kiloPascals = pascals / 1000
            value = kiloPascals
        elif unit == "mB":
            milliBars = pascals / 100
            value = milliBars
        elif unit == "inHg":
            inches_per_mercury = pascals / 3386.39
            value = inches_per_mercury
        elif unit == "torr":
            torr = pascals / 133.322
            value = torr
        elif unit == "atm":
            atm = pascals / 101325
            value = atm
        else:
            if sys.platform != 'emscripten':
                print(Fore.RED+"Error: Not a valid unit." + Style.RESET_ALL)
            else:
                print("Error: Not a valid unit.", color="error")
            value = pascals
        value = round(value, 2)
        return value

    def get_elevation(self, unit="m"):
        if sys.platform != 'emscripten' and not self._swarm:
            return self._get_elevation_desktop(unit)
        else:
            return asyncio.create_task(self._get_elevation_emscripten(unit))
    
    def _get_elevation_desktop(self, unit="m"):
        value = self.get_altitude_data()[3]
        return self._calculate_value_from_elevation(unit, value)

    async def _get_elevation_emscripten(self, unit="m"):
        value = (await self.get_altitude_data())[3]
        return self._calculate_value_from_elevation(unit, value)

    def _calculate_value_from_elevation(self, unit, value):
        if unit == "m":
            meters = round(value, 2)
            value = meters
        elif unit == "km":
            kilometers = value / 1000
            value = kilometers
        elif unit == "ft":
            feet = value * 3.28084
            value = feet
        elif unit == "mi":
            miles = value / 1609.34
            value = miles
        else:
            if sys.platform != 'emscripten':
                print(Fore.RED + "Error: Not a valid unit." + Style.RESET_ALL)
            else:
                print("Error: Not a valid unit.", color="error")
            return round(value, 2)
        return value

    def set_initial_pressure(self):
        if sys.platform != 'emscripten' and not self._swarm:
            return self._set_initial_pressure_desktop()
        else:
            return asyncio.create_task(self._set_initial_pressure_emscripten())
    
    def _set_initial_pressure_desktop(self):
        self.init_press = 0
        while self.init_press < 1:
            self.init_press = self.get_pressure()

    async def _set_initial_pressure_emscripten(self):
        self.init_press = 0
        while self.init_press < 1:
            self.init_press = await self.get_pressure()

    def height_from_pressure(self, b=0, m=9.34):
        """
        initial_pressure: the initial pressure taken at the "floor level"
        the drone must start as close to the "ground" as possible
        otherwise the height will be offset this method will
        have lots of variance as the barometer is not
        precise enough for millimeter accuracy.

        :param b: slope intercept in PASCALS
        :param m: slope in millimeters/pascals
        :return: the height in millimeters
        """
        if sys.platform != 'emscripten' and not self._swarm:
            return self._height_from_pressure_desktop(b, m)
        else:
            return asyncio.create_task(self._height_from_pressure_emscripten(b, m))
    
    def _height_from_pressure_desktop(self, b=0, m=9.34):
        current_pressure = self.get_pressure()
        height_pressure = (self.init_press - current_pressure + b) * m
        height_pressure = round(height_pressure, 2)
        return height_pressure
    
    async def _height_from_pressure_emscripten(self, b=0, m=9.34):
        current_pressure = await self.get_pressure()
        height_pressure = (self.init_press - current_pressure + b) * m
        height_pressure = round(height_pressure, 2)
        return height_pressure

    def get_temperature(self, unit="C"):
        """
        Deprecated function of get_drone_temperature()
        """
        if sys.platform != 'emscripten':
            print(Fore.YELLOW + "Warning: The 'drone.get_temperature()' function is deprecated and will be removed in a future release.\nPlease use 'drone.get_drone_temperature()'" + Style.RESET_ALL)
        else:
            print("Warning: The 'drone.get_temperature()' function is deprecated and will be removed in a future release.\nPlease use 'drone.get_drone_temperature()'", color="warning")
        return self.get_drone_temperature(unit=unit)

    def get_drone_temperature(self, unit="C"):
        """
        In celsius by default
        unit == "C" or unit == "c" or unit == "Celsius"
        unit == "F" or unit == "f" or unit == "Fahrenheit"
        unit == "K" or unit == "k" or unit == "Kelvin"
        :return: the temperature in the desired units rounded 2 decimal places
        """
        if sys.platform != 'emscripten' and not self._swarm:
            return self._get_drone_temperature_desktop(unit)
        else:
            return asyncio.create_task(self._get_drone_temperature_emscripten(unit))
    
    def _get_drone_temperature_desktop(self, unit="C"):
        data = self.get_altitude_data()[1]
        return self._calculate_value_from_temperature(unit, data)
    
    async def _get_drone_temperature_emscripten(self, unit="C"):
        data = (await self.get_altitude_data())[1]
        return self._calculate_value_from_temperature(unit, data)
    
    def _calculate_value_from_temperature(self, unit, data):
        if unit == "C" or unit == "c" or unit == "Celsius":
            data = data
        elif unit == "F" or unit == "f" or unit == "Fahrenheit":
            data = 9 / 5 * data + 32
        elif unit == "K" or unit == "k" or unit == "Kelvin":
            data = data + 273.15
        else:
            data = data
        return round(data, 2)

    def update_range_data(self, drone_type):
        '''
        Uses the time of flight sensor to detect the distance to an object
        Bottom range sensor will not update unless flying.
        Will display -1000 by default

        Front:  millimeters
        Bottom: millimeters
        '''
        self.range_data[0] = time.time() - self.timeStartProgram
        self.range_data[1] = drone_type.front
        self.range_data[2] = drone_type.bottom

    def get_range_data(self, delay=0.01):
        """
        Sends a request for updating the range data then the range data should update and the list will be returned
        does not check if the data has been updated just returns whatever is in the list
        [] Front millimeters
        bottom millimeters
        :param delay:
        :return:
        """
        if sys.platform != 'emscripten' and not self._swarm:
            return self._get_range_data_desktop(delay)
        else:
            return asyncio.create_task(self._get_range_data_emscripten(delay))

    def _get_range_data_desktop(self, delay=0.01):
        self.sendRequest(DeviceType.Drone, DataType.Range)
        time.sleep(delay)
        return self.range_data    

    async def _get_range_data_emscripten(self, delay=0.01):
        await self.sendRequest(DeviceType.Drone, DataType.Range)
        await asyncio.sleep(delay)
        return self.range_data

    def convert_meter(self, meter, conversion="cm"):
        """
        Converts meters to centimeters (cm), millimeters (mm), or inches (in).
        Will return meters if given (m)
        :param meter: The distance in meters
        :param conversion: Conversion handles cm, mm, in, or m
        :return: The distance in unit converted to
        """
        if conversion == "cm":
            return round(meter * 100, 3)

        elif conversion == "in":
            return round(meter * 39.37, 3)

        elif conversion == "mm":
            return round(meter * 1000, 3)

        elif conversion == "m":
            return round(meter, 3)

        else:
            if sys.platform != 'emscripten':
                print(Fore.RED + "Error: Not a valid unit." + Style.RESET_ALL)
            else:
                print("Error: Not a valid unit.", color="error")
            return round(meter, 3)


    def convert_millimeter(self, millimeter, conversion="cm"):
        """
            Converts millimeters to centimeters (cm), meters (m), or inches (in).
            Will return millimeters if given (mm)
            :param millimeter: The distance in millimeters
            :param conversion: Conversion handles cm, mm, in, or m
            :return: The distance in unit converted to
            """
        if conversion == "cm":
            return round(millimeter * 0.1, 3)

        elif conversion == "in":
            return round(millimeter * 0.03937, 3)

        elif conversion == "mm":
            return round(millimeter, 3)

        elif conversion == "m":
            return round(millimeter * 0.001, 3)

        else:
            if sys.platform != 'emscripten':
                print(Fore.RED + "Error: Not a valid unit." + Style.RESET_ALL)
            else:
                print("Error: Not a valid unit.", color="error")
            return round(millimeter, 3)


    def get_front_range(self, unit="cm"):
        """
        :param unit: the unit that the distance will be in "cm"
        :return:
        """
        if sys.platform != 'emscripten' and not self._swarm:
            return self._get_front_range_desktop(unit)
        else:
            return asyncio.create_task(self._get_front_range_emscripten(unit))
    
    def _get_front_range_desktop(self, unit="cm"):
        return self.convert_millimeter(self.get_range_data()[1], unit)
    
    async def _get_front_range_emscripten(self, unit="cm"):
        return self.convert_millimeter((await self.get_range_data())[1], unit)

    def get_bottom_range(self, unit="cm"):
        """
        :param unit: the unit that the distance will be in "cm"
        :return:
        """
        if sys.platform != 'emscripten' and not self._swarm:
            return self._get_bottom_range_desktop(unit)
        else:
            return asyncio.create_task(self._get_bottom_range_emscripten(unit))
    
    def _get_bottom_range_desktop(self, unit="cm"):
        return self.convert_millimeter(self.get_range_data()[2], unit)
    
    async def _get_bottom_range_emscripten(self, unit="cm"):
        return self.convert_millimeter((await self.get_range_data())[2], unit)

    def update_color_data(self, drone_type):
        '''
        Reads the current sent over Hue, Saturation, Value, Luminosity
        values from the color sensors.
        There are 2 color sensors one in the front and one in the rear.
        Both positioned at the bottom of the drone

        front sensor: H,S,V,L
        read sensor : H,S,V,L
        Color       : color1, color2
        Card        : color_card
        '''

        self.color_data[0] = time.time() - self.timeStartProgram
        self.color_data[1] = drone_type.hsvl[0][0]
        self.color_data[2] = drone_type.hsvl[0][1]
        self.color_data[3] = drone_type.hsvl[0][2]
        self.color_data[4] = drone_type.hsvl[0][3]
        self.color_data[5] = drone_type.hsvl[1][0]
        self.color_data[6] = drone_type.hsvl[1][1]
        self.color_data[7] = drone_type.hsvl[1][2]
        self.color_data[8] = drone_type.hsvl[1][3]
        self.color_data[9] = drone_type.color[0]
        self.color_data[10] = drone_type.color[1]
        self.color_data[11] = drone_type.card

    def get_color_data(self, delay=0.01):
        if sys.platform != 'emscripten' and not self._swarm:
            return self._get_color_data_desktop(delay)
        else:
            return asyncio.create_task(self._get_color_data_emscripten(delay))

    def _get_color_data_desktop(self, delay=0.01):
        self.sendRequest(DeviceType.Drone, DataType.CardColor)
        time.sleep(delay)
        return self.color_data
    
    async def _get_color_data_emscripten(self, delay=0.01):
        await self.sendRequest(DeviceType.Drone, DataType.CardColor)
        await asyncio.sleep(delay)
        return self.color_data

    def update_position_data(self, drone_type):
        """
        location of the drone
        x	Float32	4 Byte	-	X axis in meters
        y	Float32	4 Byte	-	Y axis in meters
        z	Float32	4 Byte	-	z axis in meters
        """
        self.position_data[0] = time.time() - self.timeStartProgram
        self.position_data[1] = drone_type.x
        self.position_data[2] = drone_type.y
        self.position_data[3] = drone_type.z

    def get_position_data(self, delay=0.01):
        """
        position_data[0] = time.time() - self.timeStartProgram
        position_data[1] = X axis in meters
        position_data[2] = Y axis in meters
        position_data[3] = z axis in meters
        :param delay:
        :return:
        """
        if sys.platform != 'emscripten' and not self._swarm:
            return self._get_position_data_desktop(delay)
        else:
            return asyncio.create_task(self._get_position_data_emscripten(delay))
    
    def _get_position_data_desktop(self, delay=0.01):
        self.sendRequest(DeviceType.Drone, DataType.Position)
        time.sleep(delay)
        return self.position_data
    
    async def _get_position_data_emscripten(self, delay=0.01):
        await self.sendRequest(DeviceType.Drone, DataType.Position)
        await asyncio.sleep(delay)
        return self.position_data

    def get_pos_x(self, unit="cm"):
        """
        x position in centimeters
        :param unit: "cm", "in", "mm", or "m"
        :return: x position in chosen unit (centimeter by default).
        """
        if sys.platform != 'emscripten' and not self._swarm:
            return self._get_pos_x_desktop(unit)
        else:
            return asyncio.create_task(self._get_pos_x_emscripten(unit))
    
    def _get_pos_x_desktop(self, unit="cm"):
        return self.convert_meter(self.get_position_data()[1], unit)
    
    async def _get_pos_x_emscripten(self, unit="cm"):
        return self.convert_meter((await self.get_position_data())[1], unit)

    def get_pos_y(self, unit="cm"):
        """
        y position in centimeters
        :param unit: "cm", "in", "mm", or "m"
        :return: y position in chosen unit (centimeter by default).
        """
        if sys.platform != 'emscripten' and not self._swarm:
            return self._get_pos_y_desktop(unit)
        else:
            return asyncio.create_task(self._get_pos_y_emscripten(unit))
    
    def _get_pos_y_desktop(self, unit="cm"):
        return self.convert_meter(self.get_position_data()[2], unit)
    
    async def _get_pos_y_emscripten(self, unit="cm"):
        return self.convert_meter((await self.get_position_data())[2], unit)

    def get_pos_z(self, unit="cm"):
        """
        z position in centimeters
        :param unit: "cm", "in", "mm", or "m"
        :return: z position in chosen unit (centimeter by default).
        """
        if sys.platform != 'emscripten' and not self._swarm:
            return self._get_pos_z_desktop(unit)
        else:
            return asyncio.create_task(self._get_pos_z_emscripten(unit))
    
    def _get_pos_z_desktop(self, unit="cm"):
        return self.convert_meter(self.get_position_data()[3], unit)
    
    async def _get_pos_z_emscripten(self, unit="cm"):
        return self.convert_meter((await self.get_position_data())[3], unit)

    def get_height(self, unit="cm"):
        """
        height in centimeters
        :param unit: "cm", "in", "mm", or "m"
        :return: height in chosen unit (centimeter by default).
        """
        return self.get_bottom_range(unit)

    def update_flow_data(self, drone_type):
        """
        Relative position value calculated by optical flow sensor
        x	Float32	4 Byte	-	X axis(m)
        y	Float32	4 Byte	-	Y axis(m)
        will be in meters
        """
        self.flow_data[0] = time.time() - self.timeStartProgram
        self.flow_data[1] = drone_type.x
        self.flow_data[2] = drone_type.y

    def get_flow_data(self, delay=0.01):
        if sys.platform != 'emscripten' and not self._swarm:
            return self._get_flow_data_desktop(delay)
        else:
            return asyncio.create_task(self._get_flow_data_emscripten(delay))
    
    def _get_flow_data_desktop(self, delay=0.01):
        self.sendRequest(DeviceType.Drone, DataType.RawFlow)
        time.sleep(delay)
        return self.flow_data
    
    async def _get_flow_data_emscripten(self, delay=0.01):
        await self.sendRequest(DeviceType.Drone, DataType.RawFlow)
        await asyncio.sleep(delay)
        return self.flow_data

    def get_flow_velocity_x(self, unit="cm"):
        """
        Retrieve raw optical flow velocity value measured by optical flow sensor
        from the x direction (forward and reverse)
        in centimeters
        :param unit: "cm", "in", "mm", or "m"
        :return: distance in cm
        """
        
        if sys.platform != 'emscripten' and not self._swarm:
            return self._get_flow_velocity_x_desktop(unit)
        else:
            return asyncio.create_task(self._get_flow_velocity_x_emscripten(unit))
    
    def _get_flow_velocity_x_desktop(self, unit="cm"):
        return self.convert_meter(self.get_flow_data()[1], unit)
    
    async def _get_flow_velocity_x_emscripten(self, unit="cm"):
        return self.convert_meter((await self.get_flow_data())[1], unit)

    def get_flow_x(self,unit="cm"):
        if sys.platform != 'emscripten':
            print(Fore.YELLOW + "Warning: The 'drone.get_flow_x()' function is deprecated and will be removed in a future release.\nPlease use 'drone.get_flow_velocity_x()'" + Style.RESET_ALL)
        else:
            print("Warning: The 'drone.get_flow_x()' function is deprecated and will be removed in a future release.\nPlease use 'drone.get_flow_velocity_x()'", color="warning")
        return self.get_flow_velocity_x(unit=unit)

    def get_flow_velocity_y(self, unit="cm"):
        """
        Retrieve raw optical flow velocity value measured by optical flow sensor
        from the y direction (left and right)
        in centimeters
        :param unit: "cm", "in", "mm", or "m"
        :return: distance in cm
        """
        if sys.platform != 'emscripten' and not self._swarm:
            return self._get_flow_velocity_y_desktop(unit)
        else:
            return asyncio.create_task(self._get_flow_velocity_y_emscripten(unit))
    
    def _get_flow_velocity_y_desktop(self, unit="cm"):
        return self.convert_meter(self.get_flow_data()[2], unit)
    
    async def _get_flow_velocity_y_emscripten(self, unit="cm"):
        return self.convert_meter((await self.get_flow_data())[2], unit)

    def get_flow_y(self,unit="cm"):
        if sys.platform != 'emscripten':
            print(Fore.YELLOW + "Warning: The 'drone.get_flow_y()' function is deprecated and will be removed in a future release.\nPlease use 'drone.get_flow_velocity_y()'" + Style.RESET_ALL)
        else:
            print("Warning: The 'drone.get_flow_y()' function is deprecated and will be removed in a future release.\nPlease use 'drone.get_flow_velocity_y()'", color="warning")
        return self.get_flow_velocity_y(unit=unit)

    def update_state_data(self, drone_type):

        """
        variable name	    form	          size	    range	Explanation
        modeSystem	        ModeSystem	      1 Byte	-	    System operating mode
        modeFlight	        ModeFlight	      1 Byte	-	    Flight controller operating mode
        modeControlFlight	ModeControlFlight 1 Byte	-	    flight control mode
        modeMovement	    ModeMovement	  1 Byte	-	    Moving state
        headless	        Headless	      1 Byte	-	    Headless setting status
        sensorOrientation	SensorOrientation 1 Byte	-	    Sensor orientation
        battery	            UInt8	          1 Byte	0~100	Drone battery level
        """
        self.state_data[0] = time.time() - self.timeStartProgram
        self.state_data[1] = drone_type.modeSystem
        self.state_data[2] = drone_type.modeFlight
        self.state_data[3] = drone_type.modeControlFlight
        self.state_data[4] = drone_type.headless
        self.state_data[5] = drone_type.sensorOrientation
        self.state_data[6] = drone_type.battery
        self.state_data[7] = drone_type.modeMovement
        self.state_data[8] = drone_type.controlSpeed

    def get_state_data(self, delay=0.01):
        if sys.platform != 'emscripten' and not self._swarm:
            return self._get_state_data_desktop(delay)
        elif sys.platform != 'emscripten' and self._swarm:
            return self._get_state_data_swarm(delay)
        else:
            return asyncio.create_task(self._get_state_data_emscripten(delay))
    
    def _get_state_data_desktop(self, delay=0.01):
        self.sendRequest(DeviceType.Drone, DataType.State)
        time.sleep(delay)
        return self.state_data

    async def _get_state_data_swarm(self, delay=0.01):
        await self.sendRequest(DeviceType.Drone, DataType.State)
        await asyncio.sleep(delay)
        return self.state_data
    
    async def _get_state_data_emscripten(self, delay=0.01):
        await self.sendRequest(DeviceType.Drone, DataType.State)
        await asyncio.sleep(delay)
        self._battery = self.state_data[6]
        self.state_data[6] = 0
        return self.state_data

    def get_battery(self):
        """
        Battery level a value from 0 - 100 %
        Based on the battery voltage a guess
        of the battery level is determined.
        :return:
        """
        if sys.platform != 'emscripten' and not self._swarm:
            return self._get_battery_desktop()
        elif sys.platform != 'emscripten' and self._swarm:
            return self._get_battery_swarm()
        else:
            return asyncio.create_task(self._get_battery_emscripten())
    
    def _get_battery_desktop(self):
        return self.get_state_data()[6]

    async def _get_battery_swarm(self):
        return (await self.get_state_data())[6]

    async def _get_battery_emscripten(self):
        await self.get_state_data()
        battery = self._battery
        self._battery = 0
        return battery

    def get_flight_state(self):
        if sys.platform != 'emscripten' and not self._swarm:
            return self._get_flight_state_desktop()
        else:
            return asyncio.create_task(self._get_flight_state_emscripten())
    
    def _get_flight_state_desktop(self):
        return self.get_state_data()[2]
    
    async def _get_flight_state_emscripten(self):
        return (await self.get_state_data())[2]

    def get_movement_state(self):
        if sys.platform != 'emscripten' and not self._swarm:
            return self._get_movement_state_desktop()
        else:
            return asyncio.create_task(self._get_movement_state_emscripten())

    def _get_movement_state_desktop(self):
        return self.get_state_data()[7]

    async def _get_movement_state_emscripten(self):
        return (await self.get_state_data())[7]
    
    def get_control_speed(self):
        """
        :return: control speed of drone
        """
        if sys.platform != 'emscripten' and not self._swarm:
            return self._get_control_speed_desktop()
        else:
            return asyncio.create_task(self._get_control_speed_emscripten())
    
    def _get_control_speed_desktop(self):
        control_speed = self.get_state_data()[8]
        # retry to ensure control speed is properly updated
        for _ in range(2):
            control_speed = self.get_state_data()[8]
        return control_speed
    
    async def _get_control_speed_emscripten(self):
        return (await self.get_state_data())[8]

    def speed_change(self, speed_level=1):
        """
        Controls the speed of the drone
        default is set to 1
        max is level 3 which makes the drone go very fast.
        :param speed_level: integer from 1-3
        :return: N/A
        """
        if sys.platform != 'emscripten' and not self._swarm:
            return self._speed_change_desktop(speed_level)
        if sys.platform != 'emscripten' and self._swarm:
            return asyncio.create_task(self._speed_change_swarm(speed_level))
        else:
            return asyncio.create_task(self._speed_change_emscripten(speed_level))
    
    def _speed_change_desktop(self, speed_level=1):
        if speed_level > 3:
            speed_level = 3
        elif speed_level < 1:
            speed_level = 1

        self.sendCommand(CommandType.ControlSpeed, int(speed_level))
        if self.information_data[1] == ModelNumber.Drone_12_Drone_P1:
            time.sleep(0.03)
        else:
            time.sleep(0.01)

    async def _speed_change_swarm(self, speed_level=1):
        if speed_level > 3:
            speed_level = 3
        elif speed_level < 1:
            speed_level = 1

        await self.sendCommand(CommandType.ControlSpeed, int(speed_level))
        await asyncio.sleep(0.01)

    async def _speed_change_emscripten(self, speed_level=1):
        if speed_level > 3:
            speed_level = 3
        elif speed_level < 1:
            speed_level = 1

        await self.sendCommand(CommandType.ControlSpeed, int(speed_level))
        await asyncio.sleep(0.01)
        await self._trigger_speed_callback()

    def update_motion_data(self, drone_type):

        """
            Variable    Name    Type        Size          Range Unit     Description
        [0] time_elapsed          float                                 seconds
        [1] accelX	    Int16	2 Byte	-1568 ~ 1568 (-156.8 ~ 156.8)	m/s2 x 10	 X
        [2] accelY	    Int16	2 Byte	-1568 ~ 1568 (-156.8 ~ 156.8)	m/s2 x 10	 Y
        [3] accelZ	    Int16	2 Byte	-1568 ~ 1568 (-156.8 ~ 156.8)	m/s2 x 10	 Z
        [4] gyroRoll	Int16	2 Byte	-2000 ~ 2000	degree/second Roll
        [5] gyroPitch	Int16	2 Byte	-2000 ~ 2000	degree/second Pitch
        [6] gyroYaw  	Int16	2 Byte	-2000 ~ 2000	degree/second Yaw
        [7] angleRoll	Int16	2 Byte	-180 ~ 180	degree Roll
        [8] anglePitch	Int16	2 Byte	-180 ~ 180	degree Pitch
        [9] angleYaw	Int16	2 Byte	-180 ~ 180	degree Yaw
        """
        self.motion_data[0] = time.time() - self.timeStartProgram
        self.motion_data[1] = drone_type.accelX
        self.motion_data[2] = drone_type.accelY
        self.motion_data[3] = drone_type.accelZ
        self.motion_data[4] = drone_type.gyroRoll
        self.motion_data[5] = drone_type.gyroPitch
        self.motion_data[6] = drone_type.gyroYaw
        self.motion_data[7] = drone_type.angleRoll
        self.motion_data[8] = drone_type.anglePitch
        self.motion_data[9] = drone_type.angleYaw

    def get_motion_data(self, delay=0.01):
        if sys.platform != 'emscripten' and not self._swarm:
            return self._get_motion_data_desktop(delay)
        else:
            return asyncio.create_task(self._get_motion_data_emscripten(delay))
    
    def _get_motion_data_desktop(self, delay=0.01):
        self.sendRequest(DeviceType.Drone, DataType.Motion)
        time.sleep(delay)
        return self.motion_data
    
    async def _get_motion_data_emscripten(self, delay=0.01):
        await self.sendRequest(DeviceType.Drone, DataType.Motion)
        await asyncio.sleep(delay)
        return self.motion_data

    def update_raw_motion_data(self, drone_type):
        self.raw_motion_data[0] = time.time() - self.timeStartProgram
        self.raw_motion_data[1] = drone_type.accelX
        self.raw_motion_data[2] = drone_type.accelY
        self.raw_motion_data[3] = drone_type.accelZ
        self.raw_motion_data[4] = drone_type.gyroRoll
        self.raw_motion_data[5] = drone_type.gyroPitch
        self.raw_motion_data[6] = drone_type.gyroYaw

    def get_raw_motion_data(self, delay=0.01):
        if sys.platform != 'emscripten':
            return self._get_raw_motion_data_desktop(delay)
        else:
            return asyncio.create_task(self._get_raw_motion_data_emscripten(delay))

    def _get_raw_motion_data_desktop(self, delay=0.01):
        self.sendRequest(DeviceType.Drone, DataType.RawMotion)
        time.sleep(delay)
        return self.raw_motion_data

    async def _get_raw_motion_data_emscripten(self, delay=0.01):
        await self.sendRequest(DeviceType.Drone, DataType.RawMotion)
        await asyncio.sleep(delay)
        return self.raw_motion_data

    def get_accel_x(self):
        if sys.platform != 'emscripten' and not self._swarm:
            return self._get_accel_x_desktop()
        else:
            return asyncio.create_task(self._get_accel_x_emscripten())
    
    def _get_accel_x_desktop(self):
        return self.get_motion_data()[1]
    
    async def _get_accel_x_emscripten(self):
        return (await self.get_motion_data())[1]

    def get_x_accel(self):
        if sys.platform != 'emscripten':
            print(Fore.YELLOW + "Warning: The 'drone.get_x_accel()' function is deprecated and will be removed in a future release.\nPlease use 'drone.get_accel_x()'" + Style.RESET_ALL)
        else:
            print("Warning: The 'drone.get_x_accel()' function is deprecated and will be removed in a future release.\nPlease use 'drone.get_accel_x()'", color="warning")
        return self.get_accel_x()

    def get_accel_y(self):
        if sys.platform != 'emscripten' and not self._swarm:
            return self._get_accel_y_desktop()
        else:
            return asyncio.create_task(self._get_accel_y_emscripten())
    
    def _get_accel_y_desktop(self):
        return self.get_motion_data()[2]
    
    async def _get_accel_y_emscripten(self):
        return (await self.get_motion_data())[2]

    def get_y_accel(self):
        if sys.platform != 'emscripten':
            print(Fore.YELLOW + "Warning: The 'drone.get_y_accel()' function is deprecated and will be removed in a future release.\nPlease use 'drone.get_accel_y()'" + Style.RESET_ALL)
        else:
            print("Warning: The 'drone.get_y_accel()' function is deprecated and will be removed in a future release.\nPlease use 'drone.get_accel_y()'", color="warning")
        return self.get_accel_y()

    def get_accel_z(self):
        if sys.platform != 'emscripten' and not self._swarm:
            return self._get_accel_z_desktop()
        else:
            return asyncio.create_task(self._get_accel_z_emscripten())
    
    def _get_accel_z_desktop(self):
        return self.get_motion_data()[3]
    
    async def _get_accel_z_emscripten(self):
        return (await self.get_motion_data())[3]

    def get_z_accel(self):
        if sys.platform != 'emscripten':
            print(Fore.YELLOW + "Warning: The 'drone.get_z_accel()' function is deprecated and will be removed in a future release.\nPlease use 'drone.get_accel_z()'" + Style.RESET_ALL)
        else:
            print("Warning: The 'drone.get_z_accel()' function is deprecated and will be removed in a future release.\nPlease use 'drone.get_accel_z()'", color="warning")
        return self.get_accel_z()

    def get_x_gyro(self):
        if sys.platform != 'emscripten':
            print(Fore.YELLOW + "Warning: The 'drone.get_x_gyro()' function is deprecated and will be removed in a future release.\nPlease use 'drone.get_angular_speed_x()'" + Style.RESET_ALL)
        else:
            print("Warning: The 'drone.get_x_gyro()' function is deprecated and will be removed in a future release.\nPlease use 'drone.get_angular_speed_x()'", color="warning")
        return self.get_angular_speed_x()
    
    def _get_x_gyro_desktop(self):
        return self.get_motion_data()[4]
    
    async def _get_x_gyro_emscripten(self):
        return (await self.get_motion_data())[4]

    def get_angular_speed_x(self):
        if sys.platform != 'emscripten' and not self._swarm:
            return self._get_x_gyro_desktop()
        else:
            return asyncio.create_task(self._get_x_gyro_emscripten())

    def get_y_gyro(self):
        if sys.platform != 'emscripten':
            print(Fore.YELLOW + "Warning: The 'drone.get_y_gyro()' function is deprecated and will be removed in a future release.\nPlease use 'drone.get_angular_speed_y()'" + Style.RESET_ALL)
        else:
            print("Warning: The 'drone.get_y_gyro()' function is deprecated and will be removed in a future release.\nPlease use 'drone.get_angular_speed_y()'", color="warning")
        return self.get_angular_speed_y()
    
    def _get_y_gyro_desktop(self):
        return self.get_motion_data()[5]
    
    async def _get_y_gyro_emscripten(self):
        return (await self.get_motion_data())[5]

    def get_angular_speed_y(self):
        if sys.platform != 'emscripten' and not self._swarm:
            return self._get_y_gyro_desktop()
        else:
            return asyncio.create_task(self._get_y_gyro_emscripten())

    def get_z_gyro(self):
        if sys.platform != 'emscripten':
            print(Fore.YELLOW + "Warning: The 'drone.get_z_gyro()' function is deprecated and will be removed in a future release.\nPlease use 'drone.get_angular_speed_z()'" + Style.RESET_ALL)
        else:
            print("Warning: The 'drone.get_z_gyro()' function is deprecated and will be removed in a future release.\nPlease use 'drone.get_angular_speed_z()'", color="warning")
        return self.get_angular_speed_z()
       
    def _get_z_gyro_desktop(self):
        return self.get_motion_data()[6]
    
    async def _get_z_gyro_emscripten(self):
        return (await self.get_motion_data())[6]

    def get_angular_speed_z(self):
        if sys.platform != 'emscripten' and not self._swarm:
            return self._get_z_gyro_desktop()
        else:
            return asyncio.create_task(self._get_z_gyro_emscripten())

    def get_angle_x(self):
        if sys.platform != 'emscripten' and not self._swarm:
            return self._get_angle_x_desktop()
        else:
            return asyncio.create_task(self._get_angle_x_emscripten())
    
    def _get_angle_x_desktop(self):
        return self.get_motion_data()[7]
    
    async def _get_angle_x_emscripten(self):
        return (await self.get_motion_data())[7]

    def get_x_angle(self):
        if sys.platform != 'emscripten':
            print(Fore.YELLOW + "Warning: The 'drone.get_x_angle()' function is deprecated and will be removed in a future release.\nPlease use 'drone.get_angle_x()'" + Style.RESET_ALL)
        else:
            print("Warning: The 'drone.get_x_angle()' function is deprecated and will be removed in a future release.\nPlease use 'drone.get_angle_x()'", color="warning")
        return self.get_angle_x()

    def get_angle_y(self):
        if sys.platform != 'emscripten' and not self._swarm:
            return self._get_angle_y_desktop()
        else:
            return asyncio.create_task(self._get_angle_y_emscripten())
    
    def _get_angle_y_desktop(self):
        return self.get_motion_data()[8]
    
    async def _get_angle_y_emscripten(self):
        return (await self.get_motion_data())[8]

    def get_y_angle(self):
        if sys.platform != 'emscripten':
            print(Fore.YELLOW + "Warning: The 'drone.get_y_angle()' function is deprecated and will be removed in a future release.\nPlease use 'drone.get_angle_y()'" + Style.RESET_ALL)
        else:
            print("Warning: The 'drone.get_y_angle()' function is deprecated and will be removed in a future release.\nPlease use 'drone.get_angle_y()'", color="warning")
        return self.get_angle_y()

    def get_angle_z(self):
        if sys.platform != 'emscripten' and not self._swarm:
            return self._get_angle_z_desktop()
        else:
            return asyncio.create_task(self._get_angle_z_emscripten())
    
    def _get_angle_z_desktop(self):
        return self.get_motion_data()[9]
    
    async def _get_angle_z_emscripten(self):
        return (await self.get_motion_data())[9]

    def get_z_angle(self):
        if sys.platform != 'emscripten':
            print(Fore.YELLOW + "Warning: The 'drone.get_z_angle()' function is deprecated and will be removed in a future release.\nPlease use 'drone.get_angle_z()'" + Style.RESET_ALL)
        else:
            print("Warning: The 'drone.get_z_angle()' function is deprecated and will be removed in a future release.\nPlease use 'drone.get_angle_z()'", color="warning")
        return self.get_angle_z()

    def update_joystick_data(self, drone_type):
        """
        variable  form	              size	    Range	    Explanation
        x	      Int8	              1 Byte	-100~100	X-axis value
        y	      Int8	              1 Byte	-100~100	Y-axis value
        direction Joystick Direction  1 Byte	-	        joystick direction
        event	  JoystickEvent	      1 Byte	-	        Event
        """
        self.joystick_data[0] = time.time() - self.timeStartProgram
        self.joystick_data[1] = drone_type.left.x
        self.joystick_data[2] = drone_type.left.y
        self.joystick_data[3] = drone_type.left.direction.name
        self.joystick_data[4] = drone_type.left.event.name
        self.joystick_data[5] = drone_type.right.x
        self.joystick_data[6] = drone_type.right.y
        self.joystick_data[7] = drone_type.right.direction.name
        self.joystick_data[8] = drone_type.right.event.name

    def get_joystick_data(self, delay=0.01):
        if sys.platform != 'emscripten' and not self._swarm:
            return self._get_joystick_data_desktop(delay)
        else:
            return asyncio.create_task(self._get_joystick_data_emscripten(delay))
    
    def _get_joystick_data_desktop(self, delay=0.01):
        self.sendRequest(DeviceType.Drone, DataType.Joystick)
        time.sleep(delay)
        return self.joystick_data
    
    async def _get_joystick_data_emscripten(self, delay=0.01):
        await self.sendRequest(DeviceType.Drone, DataType.Joystick)
        await asyncio.sleep(delay)
        return self.joystick_data

    def get_left_joystick_y(self):
        """
        Getter for left joystick Y (vertical) value.
        Range: -100~100   0 is neutral.
        """
        return self.joystick_data[2]

    def get_left_joystick_x(self):
        """
        Getter for left joystick X (horizontal) value.
        Range: -100~100   0 is neutral.
        """
        return self.joystick_data[1]

    def get_right_joystick_y(self):
        """
        Getter for right joystick Y (vertical) value.
        Range: -100~100   0 is neutral.
        """
        return self.joystick_data[6]

    def get_right_joystick_x(self):
        """
        Getter for right joystick X (horizontal) value.
        Range: -100~100   0 is neutral.
        """
        return self.joystick_data[5]

    def get_button_data(self):
        return self.button_data

    def l1_pressed(self):
        """
        Returns true if L1 button is pressed or held
        """
        if self.button_data[1] == 1 and (self.button_data[2] == 'Press' or self.button_data[2] == 'Down'):
            return True
        return False

    def l2_pressed(self):
        """
        Returns true if L2 button is pressed or held
        """
        if self.button_data[1] == 2 and (self.button_data[2] == 'Press' or self.button_data[2] == 'Down'):
            return True
        return False

    def r1_pressed(self):
        """
        Returns true if R1 button is pressed or held
        """
        if self.button_data[1] == 4 and (self.button_data[2] == 'Press' or self.button_data[2] == 'Down'):
            return True
        return False

    def r2_pressed(self):
        """
        Returns true if L1 button is pressed or held
        """
        if self.button_data[1] == 8 and (self.button_data[2] == 'Press' or self.button_data[2] == 'Down'):
            return True
        return False

    def h_pressed(self):
        """
        Returns true if H button is pressed or held
        """
        if self.button_data[1] == 16 and (self.button_data[2] == 'Press' or self.button_data[2] == 'Down'):
            return True
        return False

    def power_pressed(self):
        """
        Returns true if power button is pressed or held
        """
        if self.button_data[1] == 32 and (self.button_data[2] == 'Press' or self.button_data[2] == 'Down'):
            return True
        return False

    def up_arrow_pressed(self):
        """
        Returns true if up arrow button is pressed or held
        """
        if self.button_data[1] == 64 and (self.button_data[2] == 'Press' or self.button_data[2] == 'Down'):
            return True
        return False

    def left_arrow_pressed(self):
        """
        Returns true if left arrow button is pressed or held
        """
        if self.button_data[1] == 128 and (self.button_data[2] == 'Press' or self.button_data[2] == 'Down'):
            return True
        return False

    def right_arrow_pressed(self):
        """
        Returns true if right arrow button is pressed or held
        """
        if self.button_data[1] == 256 and (self.button_data[2] == 'Press' or self.button_data[2] == 'Down'):
            return True
        return False

    def down_arrow_pressed(self):
        """
        Returns true if down arrow button is pressed or held
        """
        if self.button_data[1] == 512 and (self.button_data[2] == 'Press' or self.button_data[2] == 'Down'):
            return True
        return False

    def s_pressed(self):
        """
        Returns true if S button is pressed or held
        """
        if self.button_data[1] == 1024 and (self.button_data[2] == 'Press' or self.button_data[2] == 'Down'):
            return True
        return False

    def p_pressed(self):
        """
        Returns true if P button is pressed or held
        """
        if self.button_data[1] == 2048 and (self.button_data[2] == 'Press' or self.button_data[2] == 'Down'):
            return True
        return False

    def update_trim_data(self, drone_type):
        """
        Updates and reads the trim values for
        roll, pitch, yaw, and throttle
        that are set on the drones internal memory.
        :param drone_type:
        :return: N/A
        """
        self.trim_data[0] = time.time() - self.timeStartProgram
        self.trim_data[1] = drone_type.roll
        self.trim_data[2] = drone_type.pitch
        self.trim_data[3] = drone_type.yaw
        self.trim_data[4] = drone_type.throttle

    def get_trim_data(self, delay=0.08):
        if sys.platform != 'emscripten' and not self._swarm:
            return self._get_trim_data_desktop(delay)
        else:
            return asyncio.create_task(self._get_trim_data_emscripten(delay))
    
    def _get_trim_data_desktop(self, delay=0.08):
        self.sendRequest(DeviceType.Drone, DataType.Trim)
        time.sleep(delay)
        return self.trim_data
    
    async def _get_trim_data_emscripten(self, delay=0.08):
        await self.sendRequest(DeviceType.Drone, DataType.Trim)
        await asyncio.sleep(delay)
        return self.trim_data

    # def go(self, direction, duration=1, power=50):
    #     """
    #     Fly in a given direction for the given duration and power.
    #     :param direction: string which can be one of the following: FORWARD, BACKWARD, LEFT, RIGHT, UP, and DOWN
    #     :param duration: int duration of the flight motion in seconds. If undefined, defaults to 1 seconds.
    #     :param power: int the power at which the drone flies forward. Takes a value from 0 to 100. Defaults to 50 if not defined.
    #     """
    #     try:
    #         self.set_roll(0)
    #         self.set_pitch(0)
    #         self.set_throttle(0)
    #
    #         direction = direction.upper()
    #         if power > 100:
    #             power = 100
    #         elif power < 0:
    #             power = 0
    #
    #         if direction == "FORWARD":
    #             self.set_pitch(power)
    #             self.move(duration)
    #         elif direction == "BACKWARD":
    #             self.set_pitch(power * -1)
    #             self.move(duration)
    #         elif direction == "LEFT":
    #             self.set_roll(power)
    #             self.move(duration)
    #         elif direction == "RIGHT":
    #             self.set_roll(power * -1)
    #             self.move(duration)
    #         elif direction == "UP":
    #             self.set_throttle(power)
    #             self.move(duration)
    #         elif direction == "DOWN":
    #             self.set_throttle(power * -1)
    #             self.move(duration)
    #     except:
    #         print("Incorrect arguments. Please check you parameters.")
    #         return

    def go(self, roll, pitch, yaw, throttle, duration):
        """
                Sends roll, pitch, yaw, throttle values continuously to the drone for duration (seconds)

                :param roll: int from -100-100
                :param pitch: int from -100-100
                :param yaw: int from -100-100
                :param throttle: int from -100-100
                :param timeMs: int from -100-1000000 in milliseconds
                :return: sendControl()
                """
        return self.sendControlWhile(roll, pitch, yaw, throttle, duration * 1000)

    def _receiving(self):
        while self._flagThreadRun:

            self._bufferQueue.put(self._serialport.read())

            # Automatic update of data when incoming data background check is enabled
            if self._flagCheckBackground:
                while self.check() != DataType.None_:
                    pass

            # sleep(0.001)


    async def _receiving_emscripten(self):
        while self._flagThreadRun:
            response = await self._reader.read()
            value, done = response.value, response.done

            if value:
                py_memoryview = value.to_py()
                py_bytes = py_memoryview.tobytes()
                self._bufferQueue.put(py_bytes)

                # Automatic update of data when incoming data background check is enabled
                if self._flagCheckBackground:
                    while self.check() != DataType.None_:
                        pass


    def isOpen(self):
        if sys.platform != 'emscripten' and not self._swarm:
            return self._isOpen_desktop()
        elif sys.platform != 'emscripten' and self._swarm:
            return asyncio.create_task(self._isOpen_swarm())
        else:
            self._flagThreadRun = True
            return asyncio.create_task(self._isOpen_emscripten())

    def _isOpen_desktop(self):
        if self._serialport is not None:
            return self._serialport.isOpen()
        else:
            return False
        
    async def _isOpen_swarm(self):
        await asyncio.sleep(0)
        if self._serialport is not None:
            return self._serialport.isOpen()
        else:
            return False

    async def _isOpen_emscripten(self):
        if self._serialport is not None:
            try:
                await self._serialport.getSignals()
                return True
            except:
                return False
        else:
            return False

    def isConnected(self):
        if sys.platform != 'emscripten' and not self._swarm:
            return self._isConnected_desktop()
        if sys.platform != 'emscripten' and self._swarm:
            return asyncio.create_task(self._isConnected_swarm())
        else:
            return asyncio.create_task(self._isConnected_emscripten())
    
    def _isConnected_desktop(self):
        if not self.isOpen():
            return False
        else:
            return self._flagConnected

    async def _isConnected_swarm(self):
        await asyncio.sleep(0)
        if not self.isOpen():
            return False
        else:
            return self._flagConnected

    async def _isConnected_emscripten(self):
        if not await self.isOpen():
            return False
        else:
            return self._flagConnected

    def update_count_data(self, count):
        self.count_data[0] = time.time() - self.timeStartProgram
        self.count_data[1] = count.timeFlight
        self.count_data[2] = count.countTakeOff
        self.count_data[3] = count.countLanding
        self.count_data[4] = count.countAccident

    def get_count_data(self, delay=0.05):
        if sys.platform != 'emscripten' and not self._swarm:
            return self._get_count_desktop(delay)
        else:
            return asyncio.create_task(self._get_count_emscripten(delay))

    def _get_count_desktop(self, delay=0.05):
        self.sendRequest(DeviceType.Drone, DataType.Count)
        sleep(delay)
        return self.count_data

    async def _get_count_emscripten(self, delay=0.05):
        await self.sendRequest(DeviceType.Drone, DataType.Count)
        await asyncio.sleep(delay)
        return self.count_data

    def get_flight_time(self):
        if sys.platform != 'emscripten':
            return self._get_flight_time_desktop()
        else:
            return asyncio.create_task(self._get_flight_time_emscripten())

    def _get_flight_time_desktop(self):
        return self.get_count_data()[1]

    async def _get_flight_time_emscripten(self):
        return (await self.get_count_data())[1]

    def get_takeoff_count(self):
        if sys.platform != 'emscripten':
            return self._get_takeoff_count_desktop()
        else:
            return asyncio.create_task(self._get_takeoff_count_emscripten())

    def _get_takeoff_count_desktop(self):
        return self.get_count_data()[2]

    async def _get_takeoff_count_emscripten(self):
        return (await self.get_count_data())[2]

    def get_landing_count(self):
        if sys.platform != 'emscripten':
            return self._get_landing_count_desktop()
        else:
            return asyncio.create_task(self._get_landing_count_emscripten())

    def _get_landing_count_desktop(self):
        return self.get_count_data()[3]

    async def _get_landing_count_emscripten(self):
        return (await self.get_count_data())[3]

    def get_accident_count(self):
        if sys.platform != 'emscripten':
            return self._get_accident_count_desktop()
        else:
            return asyncio.create_task(self._get_accident_count_emscripten())

    def _get_accident_count_desktop(self):
        return self.get_count_data()[4]

    async def _get_accident_count_emscripten(self):
        return (await self.get_count_data())[4]
    
    def update_cpu_id_data(self, source, cpu_id_string):
        self.cpu_id_data[0] = time.time() - self.timeStartProgram
        if source == DeviceType.Drone:
            self.cpu_id_data[1] = cpu_id_string
        elif source == DeviceType.Controller:
            self.cpu_id_data[2] = cpu_id_string
        else:
            raise ValueError("Unknown source.")

    def receive_cpu_id_data(self, device_cpu_id):
        device_cpu_id_array = device_cpu_id.cpu_id
        device_cpu_id_string = base64.b64encode(device_cpu_id_array).decode('utf-8')
        self._cpuId = device_cpu_id_string
    
    def get_cpu_id_data(self, delay=0.05):
        if sys.platform != 'emscripten' and not self._swarm:
            return self._get_cpu_id_data_desktop(delay)
        else:
            return asyncio.create_task(self._get_cpu_id_data_emscripten(delay))

    def _get_cpu_id_data_desktop(self, delay):
        self.sendRequest(DeviceType.Drone, DataType.CpuID)
        sleep(delay)
        self.update_cpu_id_data(DeviceType.Drone, self._cpuId)
        self._cpuId = []

        self.sendRequest(DeviceType.Controller, DataType.CpuID)
        sleep(delay)
        self.update_cpu_id_data(DeviceType.Controller, self._cpuId)
        self._cpuId = []

        return self.cpu_id_data

    async def _get_cpu_id_data_emscripten(self, delay):
        await self.sendRequest(DeviceType.Drone, DataType.CpuID)
        await asyncio.sleep(delay)
        self.update_cpu_id_data(DeviceType.Drone, self._cpuId)
        self._cpuId = []

        await self.sendRequest(DeviceType.Controller, DataType.CpuID)
        await asyncio.sleep(delay)
        self.update_cpu_id_data(DeviceType.Controller, self._cpuId)
        self._cpuId = []

        return self.cpu_id_data

    def update_information(self, information):
        self.information_data[0] = time.time() - self.timeStartProgram
        deviceType = DeviceType(((information.modelNumber.value >> 8) & 0xFF))

        if deviceType == DeviceType.Drone:
            self.information_data[1] = information.modelNumber
            self.information_data[2] = format_firmware_version(information.version)
        elif deviceType == DeviceType.Controller:
            self.information_data[3] = information.modelNumber
            self.information_data[4] = format_firmware_version(information.version)
        else:
            if sys.platform != 'emscripten':
                print(Fore.RED + "Error: Not a valid device type." + Style.RESET_ALL)
            else:
                print("Error: Not a valid device type.", color="error")

    def get_information_data(self, delay=0.05):
        if sys.platform != 'emscripten' and not self._swarm:
            return self._get_information_data_desktop(delay)
        else:
            return asyncio.create_task(self._get_information_data_emscripten(delay))
    
    def _get_information_data_desktop(self, delay=0.05):
        self.sendRequest(DeviceType.Drone, DataType.Information)
        sleep(delay)
        self.sendRequest(DeviceType.Controller, DataType.Information)
        sleep(delay)
        return self.information_data
      
    async def _get_information_data_emscripten(self, delay=0.05):
        await self.sendRequest(DeviceType.Drone, DataType.Information)
        await asyncio.sleep(delay)
        await self.sendRequest(DeviceType.Controller, DataType.Information)
        await asyncio.sleep(delay)
        return self.information_data

    def update_address(self, source, device_address_string):
        self.address_data[0] = time.time() - self.timeStartProgram
        if source == DeviceType.Drone:
            self.address_data[1] = device_address_string
        elif source == DeviceType.Controller:
            self.address_data[2] = device_address_string
        else:
            raise ValueError("Unknown source.")

    def receive_address_data(self,device_address):
        device_address_array = device_address.address
        device_address_string = base64.b64encode(device_address_array).decode('utf-8')
        self._address =  device_address_string

    def get_address_data(self, delay=0.05):
        if sys.platform != 'emscripten' and not self._swarm:
            return self._get_address_data_desktop(delay)
        else:
            return asyncio.create_task(self._get_address_data_emscripten(delay))

    def _get_address_data_desktop(self, delay=0.05):
        self.sendRequest(DeviceType.Drone, DataType.Address)
        sleep(delay)
        self.update_address(DeviceType.Drone, self._address)

        self.sendRequest(DeviceType.Controller, DataType.Address)
        sleep(delay)
        self.update_address(DeviceType.Controller, self._address)

        return self.address_data
    
    async def _get_address_data_emscripten(self, delay=0.05):
        await self.sendRequest(DeviceType.Drone, DataType.Address)
        await asyncio.sleep(delay)
        self.update_address(DeviceType.Drone, self._address)

        await self.sendRequest(DeviceType.Controller, DataType.Address)
        await asyncio.sleep(delay)
        self.update_address(DeviceType.Controller, self._address)

        return self.address_data

    def update_lostconnection_data(self, lostconnection):
        self.lostconnection_data[0] = time.time() - self.timeStartProgram
        self.lostconnection_data[1] = lostconnection

    def get_lostconnection_data(self, delay=0.05):
        if sys.platform != 'emscripten':
            return self._get_lostconnection_data_desktop(delay)
        else:
            return asyncio.create_task(self._get_lostconnection_data_emscripten(delay))

    def _get_lostconnection_data_desktop(self, delay=0.05):
        self.sendRequest(DeviceType.Controller, DataType.LostConnection)
        sleep(delay)
        return self.lostconnection_data

    async def _get_lostconnection_data_emscripten(self, delay=0.05):
        await self.sendRequest(DeviceType.Controller, DataType.LostConnection)
        await asyncio.sleep(delay)
        return self.lostconnection_data

    def open(self, portName=None):
        """
        Open a serial port to the controller on a baud rate of 57600
        Checks the VID vendor ID 1155 for the CoDrone EDU controller
        in order to verify the correct device.

        Sends a battery request in order to verify a
        connection to the drone and displays the battery level

        :param portname: usb port path
        :return: Boolean (True if successful connection and false if not)
        """
        if sys.platform != 'emscripten' and not self._swarm:
            return self._open_desktop(portName)
        elif sys.platform != 'emscripten' and self._swarm:
            return asyncio.create_task(self._open_swarm(portName))
        else:
            return asyncio.create_task(self._open_emscripten(portName))

    def _open_desktop(self, portname=None, updater=False):
        cde_controller_vid = 1155

        try:
            ser = serial.Serial()  # open first serial port
            ser.close()
        except:
            print("Serial library not installed")
            self.disconnect()
            exit()

        if portname is None:
            nodes = comports()
            size = len(nodes)

            for item in nodes:
                if item.vid == cde_controller_vid:
                    portname = item.device
                    print(Fore.GREEN + "Detected CoDrone EDU controller at port {0}".format(portname)+ Style.RESET_ALL)
                    break
        try:
            self._serialport = serial.Serial(
                port=portname,
                baudrate=57600)

            if self.isOpen():

                self._flagThreadRun = True
                self._thread = Thread(target=self._receiving, args=(), daemon=True)
                self._thread.start()
                self._printLog("Connected.({0})".format(portname))

            else:

                self._printError("Could not connect to device.")
                print(Fore.RED + "Serial device not available. Check the USB cable or USB port. . " + Style.RESET_ALL)
                self.disconnect()
                exit()

        # TODO: Fix this bare except
        except:
            self._printError("Could not connect to device.")
            print(Fore.RED + "Could not connect to CoDrone EDU controller." + Style.RESET_ALL)
            self.disconnect()
            exit()
        # check about 10 times
        for i in range(10):
            state = self.get_state_data()
            state_flight = state[2]
            if state_flight is ModeFlight.Ready:
                break
            else:
                time.sleep(0.1)

        if state_flight is ModeFlight.Ready:
            device_info = self.get_information_data()

            if self.information_data[1] == ModelNumber.Drone_12_Drone_P1:
                print(Fore.GREEN + "Connected to CoDrone EDU (JROTC ed.)." + Style.RESET_ALL)
            else:
                print(Fore.GREEN + "Connected to CoDrone EDU." + Style.RESET_ALL)

            battery = state[6]
            print(Fore.GREEN + "Battery = {0}%".format(battery) + Style.RESET_ALL)
            # set the speed to medium level
            self.speed_change(speed_level=2)
            time.sleep(0.2)
            
            # disable the previous YPRT commands
            self.sendControl(0, 0, 0, 0)
            time.sleep(0.2)

        else:
            print(Fore.RED + "Could not connect to CoDrone EDU. "
                             "Check that the drone is on and paired to the controller." + Style.RESET_ALL)
            print(Fore.YELLOW + "How to pair: https://youtu.be/kMJhf5ykLSo " + Style.RESET_ALL)
            # print("Exiting program")
            # self.close()
            # exit()

        return True

    async def _open_swarm(self, portname=None, updater=False):
        cde_controller_vid = 1155

        try:
            ser = serial.Serial()  # open first serial port
            ser.close()
        except:
            print("Serial library not installed")
            await self.disconnect()
            exit()

        if portname is None:
            nodes = comports()
            size = len(nodes)

            for item in nodes:
                if item.vid == cde_controller_vid:
                    portname = item.device
                    print(Fore.GREEN + "Detected CoDrone EDU controller at port {0}".format(portname) + Style.RESET_ALL)
                    break
        try:
            self._serialport = serial.Serial(
                port=portname,
                baudrate=57600)

            if await self.isOpen():

                self._flagThreadRun = True
                self._thread = Thread(target=self._receiving, args=(), daemon=True)
                self._thread.start()
                self._printLog("Connected.({0})".format(portname))

            else:

                self._printError("Could not connect to device.")
                print(Fore.RED + "Serial device not available. Check the USB cable or USB port. . " + Style.RESET_ALL)
                await self.disconnect()
                exit()

        # TODO: Fix this bare except
        except:
            self._printError("Could not connect to device.")
            print(Fore.RED + "Could not connect to CoDrone EDU controller." + Style.RESET_ALL)
            await self.disconnect()
            exit()
        # check about 10 times
        for i in range(10):
            state = await self.get_state_data()
            state_flight = state[2]
            if state_flight is ModeFlight.Ready:
                break
            else:
                await asyncio.sleep(0.1)

        if state_flight is ModeFlight.Ready:
            device_info = await self.get_information_data()

            if self.information_data[1] == ModelNumber.Drone_12_Drone_P1:
                print(Fore.GREEN + "Connected to CoDrone EDU (JROTC ed.)." + Style.RESET_ALL)
            else:
                print(Fore.GREEN + "Connected to CoDrone EDU." + Style.RESET_ALL)

            battery = state[6]
            print(Fore.GREEN + "Battery = {0}%".format(battery) + Style.RESET_ALL)
            # set the speed to medium level
            await self.speed_change(speed_level=2)
            await asyncio.sleep(0.2)

            # disable the previous YPRT commands
            await self.sendControl(0, 0, 0, 0)
            await asyncio.sleep(0.2)

        else:
            print(Fore.RED + "Could not connect to CoDrone EDU. "
                             "Check that the drone is on and paired to the controller." + Style.RESET_ALL)
            print(Fore.YELLOW + "How to pair: https://youtu.be/kMJhf5ykLSo " + Style.RESET_ALL)
            # print("Exiting program")
            # self.close()
            # exit()

        return True

    async def _open_emscripten(self, portname=None):
        if await self.isOpen():
            print(f"\033[93mWarning: Serial port already open.\033[0m")
            return

        self._serialport = await navigator.serial.requestPort(j({
          "filters": [{ "usbVendorId": 1155 }],
        }))
        await self._serialport.open(j({"baudRate": 57600, "baudrate": 57600}))

        if self._serialport:
            self._writer = self._serialport.writable.getWriter()
            self._reader = self._serialport.readable.getReader()
            await self._receiving_emscripten()

    async def _open_success_emscripten(self):
        # Force link mode
        await self.sendControlleLinkMode()
        await asyncio.sleep(0.1)

        device_info = await self.get_information_data()

        if device_info[0] == ModelNumber.Drone_12_Drone_P1:
            print("Connected to CoDrone EDU (JROTC ed.).", color="green")
        else:
            print("Connected to CoDrone EDU.", color="green")

        await self.get_state_data()
        battery = self._battery
        print("Battery = {0}%".format(battery), color="green")
        # set the speed to medium level
        await self.speed_change(speed_level=2)
        await asyncio.sleep(0.2)

        # disable the previous YPRT commands
        await self.sendControl(0, 0, 0, 0)
        await asyncio.sleep(0.2)

    def close(self):
        return self.disconnect()

    def makeTransferDataArray(self, header, data):
        if (header is None) or (data is None):
            return None

        if not isinstance(header, Header):
            return None

        if isinstance(data, ISerializable):
            data = data.toArray()

        crc16 = CRC16.calc(header.toArray(), 0)
        crc16 = CRC16.calc(data, crc16)

        dataArray = bytearray()
        dataArray.extend((0x0A, 0x55))
        dataArray.extend(header.toArray())
        dataArray.extend(data)
        dataArray.extend(pack('H', crc16))

        return dataArray
    

    def transfer(self, header, data):
        if sys.platform != 'emscripten' and not self._swarm:
            return self._transfer_desktop(header, data)
        elif sys.platform != 'emscripten' and self._swarm:
            return asyncio.create_task(self._transfer_swarm(header, data))
        else:
            return asyncio.create_task(self._transfer_emscripten(header, data))

    def _transfer_desktop(self, header, data):
        if not self.isOpen():
            return

        dataArray = self.makeTransferDataArray(header, data)

        self._serialport.write(dataArray)

        # send data output
        self._printTransferData(dataArray)

        return dataArray
    
    async def _transfer_swarm(self, header, data):
        if not await self.isOpen():
            return

        dataArray = self.makeTransferDataArray(header, data)

        self._serialport.write(dataArray)

        # send data output
        self._printTransferData(dataArray)

        await asyncio.sleep(0)

        return dataArray

    async def _transfer_emscripten(self, header, data):
        if not await self.isOpen():
            return
        
        dataArray = self.makeTransferDataArray(header, data)

        self._writer.write(j(dataArray))

        self._printTransferData(dataArray)

        return dataArray

    def check(self):
        while not self._bufferQueue.empty():
            dataArray = self._bufferQueue.get_nowait()
            self._bufferQueue.task_done()

            if (dataArray is not None) and (len(dataArray) > 0):
                # receive data output
                self._printReceiveData(dataArray)

                self._bufferHandler.extend(dataArray)

        while len(self._bufferHandler) > 0:
            stateLoading = self._receiver.call(self._bufferHandler.pop(0))

            # error output
            if stateLoading == StateLoading.Failure:
                # Incoming data output (skipped)
                self._printReceiveDataEnd()

                # Error message output
                self._printError(self._receiver.message)

            # log output
            if stateLoading == StateLoading.Loaded:
                # Incoming data output (skipped)
                self._printReceiveDataEnd()

                # Log output
                self._printLog(self._receiver.message)

            if self._receiver.state == StateLoading.Loaded:
                self._handler(self._receiver.header, self._receiver.data)
                return self._receiver.header.dataType

        return DataType.None_

    def checkDetail(self):
        while not self._bufferQueue.empty():
            dataArray = self._bufferQueue.get_nowait()
            self._bufferQueue.task_done()

            if (dataArray is not None) and (len(dataArray) > 0):
                # Receive data output
                self._printReceiveData(dataArray)

                self._bufferHandler.extend(dataArray)

        while len(self._bufferHandler) > 0:
            stateLoading = self._receiver.call(self._bufferHandler.pop(0))

            # Error output
            if stateLoading == StateLoading.Failure:
                # Incoming data output (skipped)
                self._printReceiveDataEnd()

                # Error message output
                self._printError(self._receiver.message)

            # Log output
            if stateLoading == StateLoading.Loaded:
                # Incoming data output (skipped)
                self._printReceiveDataEnd()

                # Log output
                self._printLog(self._receiver.message)

            if self._receiver.state == StateLoading.Loaded:
                self._handler(self._receiver.header, self._receiver.data)
                return self._receiver.header, self._receiver.data

        return None, None

    def _handler(self, header, dataArray):

        # Save incoming data
        self._runHandler(header, dataArray)

        # Run a callback event
        self._runEventHandler(header.dataType)

        # Monitor data processing
        self._runHandlerForMonitor(header, dataArray)

        # Verify data processing complete
        self._receiver.checked()

        return header.dataType

    def _runHandler(self, header, dataArray):

        # General data processing
        if self._parser.d[header.dataType] is not None:
            self._storageHeader.d[header.dataType] = header
            self._storage.d[header.dataType] = self._parser.d[header.dataType](dataArray)
            self._storageCount.d[header.dataType] += 1

    def _runEventHandler(self, dataType):
        if (isinstance(dataType, DataType)) and (self._eventHandler.d[dataType] is not None) and (
                self._storage.d[dataType] is not None):
            return self._eventHandler.d[dataType](self._storage.d[dataType])
        else:
            return None

    def _runHandlerForMonitor(self, header, dataArray):

        # Monitor data processing
        # Parse the received data self.monitorData[] Putting data in an array
        if header.dataType == DataType.Monitor:

            monitorHeaderType = MonitorHeaderType(dataArray[0])

            if monitorHeaderType == MonitorHeaderType.Monitor0:

                monitor0 = Monitor0.parse(dataArray[1:1 + Monitor0.getSize()])

                if monitor0.monitorDataType == MonitorDataType.F32:

                    dataCount = (dataArray.len() - 1 - Monitor0.getSize()) / 4

                    for i in range(0, dataCount):

                        if monitor0.index + i < len(self.monitorData):
                            index = 1 + Monitor0.getSize() + (i * 4)
                            self.monitorData[monitor0.index + i], = unpack('<f', dataArray[index:index + 4])

            elif monitorHeaderType == MonitorHeaderType.Monitor4:

                monitor4 = Monitor4.parse(dataArray[1:1 + Monitor4.getSize()])

                if monitor4.monitorDataType == MonitorDataType.F32:

                    self.systemTimeMonitorData = monitor4.systemTime

                    dataCount = (dataArray.len() - 1 - Monitor4.getSize()) / 4

                    for i in range(0, dataCount):

                        if monitor4.index + i < len(self.monitorData):
                            index = 1 + Monitor4.getSize() + (i * 4)
                            self.monitorData[monitor4.index + i], = unpack('<f', dataArray[index:index + 4])

            elif monitorHeaderType == MonitorHeaderType.Monitor8:

                monitor8 = Monitor8.parse(dataArray[1:1 + Monitor8.getSize()])

                if monitor8.monitorDataType == MonitorDataType.F32:

                    self.systemTimeMonitorData = monitor8.systemTime

                    dataCount = (dataArray.len() - 1 - Monitor8.getSize()) / 4

                    for i in range(0, dataCount):

                        if monitor8.index + i < len(self.monitorData):
                            index = 1 + Monitor8.getSize() + (i * 4)
                            self.monitorData[monitor8.index + i], = unpack('<f', dataArray[index:index + 4])

    def setEventHandler(self, dataType, eventHandler):

        if not isinstance(dataType, DataType):
            return
        self._eventHandler.d[dataType] = eventHandler

    def getHeader(self, dataType):

        if not isinstance(dataType, DataType):
            return None

        return self._storageHeader.d[dataType]

    def getData(self, dataType):

        if not isinstance(dataType, DataType):
            return None

        return self._storage.d[dataType]

    def getCount(self, dataType):

        if not isinstance(dataType, DataType):
            return None

        return self._storageCount.d[dataType]

    def _printLog(self, message):

        # Log output
        if self._flagShowLogMessage and message is not None:
            if sys.platform != 'emscripten':
                print(Fore.GREEN + "[{0:10.03f}] {1}".format((time.time() - self.timeStartProgram),
                                                         message) + Style.RESET_ALL)
            else:
                print("[{0:10.03f}] {1}".format((time.time() - self.timeStartProgram), message), color="green")

    def _printError(self, message):

        # Error message output
        if self._flagShowErrorMessage and message is not None:
            if sys.platform != 'emscripten':
                print(
                    Fore.RED + "[{0:10.03f}] {1}".format((time.time() - self.timeStartProgram), message) + Style.RESET_ALL)
            else:
                print("[{0:10.03f}] {1}".format((time.time() - self.timeStartProgram), message), color="error")

    def _printTransferData(self, dataArray):

        # Send data output
        if self._flagShowTransferData and (dataArray is not None) and (len(dataArray) > 0):
            print(Back.YELLOW + Fore.BLACK + convertByteArrayToString(dataArray) + Style.RESET_ALL)

    def _printReceiveData(self, dataArray):

        # Receive data output
        if self._flagShowReceiveData and (dataArray is not None) and (len(dataArray) > 0):
            print(Back.CYAN + Fore.BLACK + convertByteArrayToString(dataArray) + Style.RESET_ALL, end='')

    def _printReceiveDataEnd(self):

        # Incoming data output (skipped)
        if self._flagShowReceiveData:
            print("")

    # BaseFunctions End

    # Common Start

    def sendPing(self, deviceType):

        if not isinstance(deviceType, DeviceType):
            return None

        header = Header()

        header.dataType = DataType.Ping
        header.length = Ping.getSize()
        header.from_ = DeviceType.Base
        header.to_ = deviceType

        data = Ping()

        data.systemTime = 0

        return self.transfer(header, data)

    def sendRequest(self, deviceType, dataType):

        if (not isinstance(deviceType, DeviceType)) or (not isinstance(dataType, DataType)):
            return None

        header = Header()

        header.dataType = DataType.Request
        header.length = Request.getSize()
        header.from_ = DeviceType.Base
        header.to_ = deviceType

        data = Request()

        data.dataType = dataType
        return self.transfer(header, data)

    def sendPairing(self, deviceType, address0, address1, address2, scramble, channel0, channel1, channel2, channel3):

        if ((not isinstance(deviceType, DeviceType)) or
                (not isinstance(address0, int)) or
                (not isinstance(address1, int)) or
                (not isinstance(address2, int)) or
                (not isinstance(scramble, int)) or
                (not isinstance(channel0, int)) or
                (not isinstance(channel1, int)) or
                (not isinstance(channel2, int)) or
                (not isinstance(channel3, int))):
            return None

        header = Header()

        header.dataType = DataType.Pairing
        header.length = Pairing.getSize()
        header.from_ = DeviceType.Base
        header.to_ = deviceType

        data = Pairing()

        data.address0 = address0
        data.address1 = address1
        data.address2 = address2
        data.scramble = scramble
        data.channel0 = channel0
        data.channel1 = channel1
        data.channel2 = channel2
        data.channel3 = channel3

        return self.transfer(header, data)

    # Common Start

    # Control Start
    def pair(self, portname=None):
        return self.open(portname)
        #print(Fore.YELLOW + "Warning: The 'drone.pair()' function is deprecated and will be removed in a future release. "
        #"Please use 'drone.connect()' instead for establishing a connection to the drone." + Style.RESET_ALL)

    def connect(self, portname=None):
        return self.open(portname)

    def disconnect(self):
        if sys.platform != 'emscripten' and not self._swarm:
            return self._disconnect_desktop()
        elif sys.platform != 'emscripten' and self._swarm:
            return asyncio.create_task(self._disconnect_swarm())
        else:
            return asyncio.create_task(self._disconnect_emscripten())

    def _disconnect_desktop(self):
        # log output
        if self.isOpen():
            self._printLog("Closing serial port.")

        self._printLog("Thread Flag False.")

        if self._flagThreadRun:
            self._flagThreadRun = False
            sleep(0.1)

        self._printLog("Thread Join.")

        if self._thread is not None:
            self._thread.join(timeout=1)

        self._printLog("Port Close.")

        if self.isOpen():
            self._serialport.close()
            sleep(0.2)

    async def _disconnect_swarm(self):
        # log output
        if await self.isOpen():
            self._printLog("Closing serial port.")

        self._printLog("Thread Flag False.")

        if self._flagThreadRun:
            self._flagThreadRun = False
            sleep(0.1)

        self._printLog("Thread Join.")

        if self._thread is not None:
            self._thread.join(timeout=1)

        self._printLog("Port Close.")

        if await self.isOpen():
            self._serialport.close()
            sleep(0.2)

    async def _disconnect_emscripten(self):
        # log output
        if await self.isOpen():
            self._printLog("Closing serial port.")

        self._printLog("Thread Flag False.")

        if self._flagThreadRun:
            self._flagThreadRun = False
            await asyncio.sleep(0.1)

        self._printLog("Thread Join.")

        if self._writer is not None and self._reader is not None:
            self._writer.releaseLock()
            self._reader.releaseLock()

        self._printLog("Port Close.")

        if await self.isOpen():
            self._serialport.close()
            await asyncio.sleep(0.2)

    def takeoff(self):
        if sys.platform != 'emscripten' and not self._swarm:
            return self._takeoff_desktop()
        else:
            return asyncio.create_task(self._takeoff_emscripten())

    def _takeoff_desktop(self):

        self.reset_move_values()
        self.sendTakeOff()

        timeout = 4
        init_time = time.time()
        time_elapsed = time.time() - init_time
        while time_elapsed < timeout:
            time_elapsed = time.time() - init_time
            state = self.get_state_data()
            state_flight = state[2]
            if state_flight is ModeFlight.TakeOff:
                break
            else:
                self.sendTakeOff()
                time.sleep(0.01)

        time.sleep(4)

    async def _takeoff_emscripten(self):
        await self.reset_move_values()
        await self.sendTakeOff()

        timeout = 4
        init_time = time.time()
        time_elapsed = time.time() - init_time
        while time_elapsed < timeout:
            time_elapsed = time.time() - init_time
            state = await self.get_state_data()
            state_flight = state[2]
            if ModeFlight(state_flight) is ModeFlight.TakeOff:
                break
            else:
                await self.sendTakeOff()
                await asyncio.sleep(0.01)

        await asyncio.sleep(4)

    def land(self):
        """
        Sends a command to land the drone gently.

        :return: None
        """
        
        if sys.platform != 'emscripten' and not self._swarm:
            return self._land_desktop()
        else:
            return asyncio.create_task(self._land_emscripten())

    def _land_desktop(self):
        self.reset_move_values()
        # reset the land coordinate back to zero
        self.previous_land[0] = self.previous_land[0] + self.get_position_data()[1]
        self.previous_land[1] = self.previous_land[1] + self.get_position_data()[2]
        self.sendLanding()

        timeout = 4
        init_time = time.time()
        time_elapsed = time.time() - init_time
        while time_elapsed < timeout:
            time_elapsed = time.time() - init_time
            state = self.get_state_data()
            state_flight = state[2]
            if state_flight is ModeFlight.Landing:
                break
            else:
                self.sendLanding()
                time.sleep(0.01)

        time.sleep(4)

    async def _land_emscripten(self):
        await self.reset_move_values()
        # reset the land coordinate back to zero
        self.previous_land[0] = self.previous_land[0] + (await self.get_position_data())[1]
        self.previous_land[1] = self.previous_land[1] + (await self.get_position_data())[2]
        await self.sendLanding()

        timeout = 4
        init_time = time.time()
        time_elapsed = time.time() - init_time
        while time_elapsed < timeout:
            time_elapsed = time.time() - init_time
            state = await self.get_state_data()
            state_flight = state[2]
            if ModeFlight(state_flight) is ModeFlight.Landing:
                break
            else:
                await self.sendLanding()
                await asyncio.sleep(0.01)

        await asyncio.sleep(4)

    def emergency_stop(self):
        """
        Sends a command to stop all motors immediately.

        :return: None
        """

        if sys.platform != 'emscripten' and not self._swarm:
            return self._emergency_stop_desktop()
        else:
            return asyncio.create_task(self._emergency_stop_emscripten())
    
    def _emergency_stop_desktop(self):
        self.reset_move_values()
        self.sendStop()

    async def _emergency_stop_emscripten(self):
        await self.reset_move_values()
        await self.sendStop()

    def stop_motors(self):
        """
        same as emergency stop just different name
        :return:
        """
        return self.emergency_stop()

    def hover(self, duration=0.01):
        """
        Hovers the drone in place for a duration of time.

        :param duration: number of seconds to perform the hover command
        TODO: Make this command use the sensors to attempt to stay at that position
        :return: None
        """
        if sys.platform != 'emscripten' and not self._swarm:
            return self._hover_desktop(duration)
        else:
            return asyncio.create_task(self._hover_emscripten(duration))

    def _hover_desktop(self, duration=0.01):
        self.sendControl(0, 0, 0, 0)
        time.sleep(duration)

    async def _hover_emscripten(self, duration=0.01):
        await self.sendControl(0, 0, 0, 0)
        await asyncio.sleep(duration)

    # Movement control

    def reset_move(self, attempts=3):
        if sys.platform != 'emscripten':
            print(Fore.YELLOW + "Warning: This method is deprecated and will be removed in a future release.\nPlease use 'drone.reset_move_values()' instead." + Style.RESET_ALL)
        else:
            print("Warning: This method is deprecated and will be removed in a future release.\nPlease use 'drone.reset_move_values()'", color="warning")
        return self.reset_move_values(attempts)

    def reset_move_values(self, attempts=3):
        """
        Resets the values of roll, pitch, yaw, and throttle to 0.

        :param attempts: number of times hover() command is sent
        :return: None
        """
        if sys.platform != 'emscripten' and not self._swarm:
            return self._reset_move_desktop(attempts)
        else:
            return asyncio.create_task(self._reset_move_emscripten(attempts))

    def _reset_move_desktop(self, attempts=3):
        # make sure the drone doesnt have any previous YPRT
        for i in range(attempts):
            self.hover()
        
    async def _reset_move_emscripten(self, attempts=3):
        for i in range(attempts):
            await self.hover()

    def set_roll(self, power):
        """
        Sets the roll variable for flight movement.

        :param power: int from -100-100
        :return: None
        """
        self._control.roll = int(power)

        if sys.platform == 'emscripten':
            self._trigger_callback('roll_pitch')

    def set_pitch(self, power):
        """
        Sets the pitch variable for flight movement.

        :param power: int from 100-100
        :return: None
        """
        self._control.pitch = int(power)

        if sys.platform == 'emscripten':
            self._trigger_callback('roll_pitch')

    def set_yaw(self, power):
        """
        Sets the yaw variable for flight movement.

        :param power: int from -100-100
        :return: None
        """
        self._control.yaw = int(power)

    def set_throttle(self, power):
        """
        Sets the yaw variable for flight movement.

        :param power: int from -100-100
        :return: None
        """
        self._control.throttle = int(power)

    def move(self, duration=None):
        """
        Used with set_roll, set_pitch, set_yaw, set_throttle commands.
        Sends flight movement values to the drone.

        :param duration: Number of seconds to perform the action
        :return: None
        """
        if sys.platform != 'emscripten' and not self._swarm:
            return self._move_desktop(duration)
        else:
            return asyncio.create_task(self._move_emscripten(duration))

    def _move_desktop(self, duration=None):
        if duration is None:
            self.sendControl(*vars(self._control).values())
            time.sleep(0.003)

        else:
            milliseconds = int(duration * 1000)
            # there is a while loop inside of the send control method.
            self.sendControlWhile(*vars(self._control).values(), milliseconds)

    async def _move_emscripten(self, duration=None):
        if duration is None:
            await self.sendControl(*vars(self._control).values())
            await asyncio.sleep(0.003)

        else:
            milliseconds = int(duration * 1000)
            # there is a while loop inside of the send control method.
            await self.sendControlWhile(*vars(self._control).values(), milliseconds)


    def print_move_values(self):
        """
        Prints current values of roll, pitch, yaw, and throttle.

        :return: None
        """
        print(*vars(self._control).values())
        if sys.platform != 'emscripten':
            print(Fore.YELLOW + "Warning: This method is deprecated and will be removed in a future release.\nPlease use 'drone.get_move_values()' instead." + Style.RESET_ALL)
        else:
            print("Warning: This method is deprecated and will be removed in a future release.\nPlease use 'drone.get_move_values()'", color="warning")

    def get_move_values(self):
        """
        Returns current values of roll, pitch, yaw, and throttle.

        :return: List of values
        """
        return [*vars(self._control).values()]

    def turn(self, power=50, seconds=None):
        """
        Turns the drone in the yaw direction
        :param seconds: Number of seconds to perform the turn
        :param power: int from -100 - 100
        :return: None
        """
        if sys.platform != 'emscripten' and not self._swarm:
            return self._turn_desktop(power, seconds)
        else:
            return asyncio.create_task(self._turn_emscripten(power, seconds))
    
    def _turn_desktop(self, power=50, seconds=None):
        if seconds is None:
            self.sendControl(0, 0, power, 0)
            time.sleep(0.003)
        else:
            seconds = seconds * 1000
            self.sendControlWhile(0, 0, power, 0, seconds)
            self.hover(0.5)

    async def _turn_emscripten(self, power=50, seconds=None):
        if seconds is None:
            await self.sendControl(0, 0, power, 0)
            await asyncio.sleep(0.003)
        else:
            seconds = seconds * 1000
            await self.sendControlWhile(0, 0, power, 0, seconds)
            await self.hover(0.5)

    def set_waypoint(self):
        """Saves current position data to waypoint_data list
        :return: current position data
        """
        if sys.platform != 'emscripten' and not self._swarm:
            return self._set_waypoint_desktop()
        else:
            return asyncio.create_task(self._set_waypoint_emscripten())
        
    def _set_waypoint_desktop(self):
        self.get_position_data()
        x = self.get_position_data()[1]
        y = self.get_position_data()[2]
        z = self.get_position_data()[3]
        temp = [x, y, z]
        return self.waypoint_data.append(temp)
    
    async def _set_waypoint_emscripten(self):
        await self.get_position_data()
        x = (await self.get_position_data())[1]
        y = (await self.get_position_data())[2]
        z = (await self.get_position_data())[3]
        temp = [x, y, z]
        return self.waypoint_data.append(temp)

    def sendTakeOff(self):

        header = Header()

        header.dataType = DataType.Command
        header.length = Command.getSize()
        header.from_ = DeviceType.Base
        header.to_ = DeviceType.Drone

        data = Command()

        data.commandType = CommandType.FlightEvent
        data.option = FlightEvent.TakeOff.value

        return self.transfer(header, data)
    
    def sendLanding(self):
        if sys.platform != 'emscripten' and not self._swarm:
            return self._sendLanding_desktop()
        else:
            return asyncio.create_task(self._sendLanding_emscripten())

    def _sendLanding_desktop(self):

        self._control.roll = 0
        self._control.pitch = 0
        self._control.yaw = 0
        self._control.throttle = 0
        self.move()

        header = Header()

        header.dataType = DataType.Command
        header.length = Command.getSize()
        header.from_ = DeviceType.Base
        header.to_ = DeviceType.Drone

        data = Command()

        data.commandType = CommandType.FlightEvent
        data.option = FlightEvent.Landing.value

        return self.transfer(header, data)
    
    async def _sendLanding_emscripten(self):
        self._control.roll = 0
        self._control.pitch = 0
        self._control.yaw = 0
        self._control.throttle = 0
        await self.move()

        header = Header()

        header.dataType = DataType.Command
        header.length = Command.getSize()
        header.from_ = DeviceType.Base
        header.to_ = DeviceType.Drone

        data = Command()

        data.commandType = CommandType.FlightEvent
        data.option = FlightEvent.Landing.value

        await self.transfer(header, data)

    def sendStop(self):

        header = Header()

        header.dataType = DataType.Command
        header.length = Command.getSize()
        header.from_ = DeviceType.Base
        header.to_ = DeviceType.Drone

        data = Command()

        data.commandType = CommandType.Stop
        data.option = 0

        return self.transfer(header, data)

    def sendControl(self, roll, pitch, yaw, throttle):
        '''
        Sends roll, pitch, yaw, throttle values to the drone.

        :param roll: int from -100-100
        :param pitch: int from -100-100
        :param yaw: int from -100-100
        :param throttle: int from -100-100
        :return: transfer()
        '''

        if ((not isinstance(roll, int)) or (not isinstance(pitch, int)) or (not isinstance(yaw, int)) or (
                not isinstance(throttle, int))):
            return None

        header = Header()

        header.dataType = DataType.Control
        header.length = ControlQuad8.getSize()
        header.from_ = DeviceType.Base
        header.to_ = DeviceType.Drone

        self._control.roll = roll
        self._control.pitch = pitch
        self._control.yaw = yaw
        self._control.throttle = throttle

        return self.transfer(header, self._control)
    
    def sendControlWhile(self, roll, pitch, yaw, throttle, timeMs):
        """
        Sends roll, pitch, yaw, throttle values continuously to the drone for timeMs

        :param roll: int from -100-100
        :param pitch: int from -100-100
        :param yaw: int from -100-100
        :param throttle: int from -100-100
        :param timeMs: int from -100-1000000 in milliseconds

        """
        if sys.platform != 'emscripten' and not self._swarm:
            return self._sendControlWhile_desktop(roll, pitch, yaw, throttle, timeMs)
        else:
            return asyncio.create_task(self._sendControlWhile_emscripten(roll, pitch, yaw, throttle, timeMs))

    def _sendControlWhile_desktop(self, roll, pitch, yaw, throttle, timeMs):
        if ((not isinstance(roll, int)) or
                (not isinstance(pitch, int)) or
                (not isinstance(yaw, int)) or
                (not isinstance(throttle, int))):
            return None

        time_sec = timeMs / 1000
        time_start = time.perf_counter()

        while (time.perf_counter() - time_start) < time_sec:
            self.sendControl(roll, pitch, yaw, throttle)
            time.sleep(0.003)

    async def _sendControlWhile_emscripten(self, roll, pitch, yaw, throttle, timeMs):
        if ((not isinstance(roll, int)) or
                (not isinstance(pitch, int)) or
                (not isinstance(yaw, int)) or
                (not isinstance(throttle, int))):
            return None

        time_sec = timeMs / 1000
        time_start = time.perf_counter()

        while (time.perf_counter() - time_start) < time_sec:
            await self.sendControl(roll, pitch, yaw, throttle)
            await asyncio.sleep(0.003)

    def sendControlPosition(self, positionX, positionY, positionZ, velocity, heading, rotationalVelocity):
        """
        drone movement command

        Use real values for position and velocity, and
        integer values for heading and rotational Velocity.
        :param positionX: float	-10.0 ~ 10.0	meter	Front (+), Back (-)
        :param positionY: float	-10.0 ~ 10.0	meter	Left(+), Right(-)
        :param positionZ: float	-10.0 ~ 10.0	meter	Up (+), Down (-)
        :param velocity: float	0.5 ~ 2.0	m/s	position movement speed
        :param heading: Int16	-360 ~ 360	degree	Turn left (+), turn right (-)
        :param rotationalVelocity:
        :return: Int16	10 ~ 360	degree/s	left and right rotation speed
        """

        if not (isinstance(positionX, float) or isinstance(positionX, int)):
            return None

        if not (isinstance(positionY, float) or isinstance(positionY, int)):
            return None

        if not (isinstance(positionZ, float) or isinstance(positionZ, int)):
            return None

        if not (isinstance(velocity, float) or isinstance(velocity, int)):
            return None

        if (not isinstance(heading, int)) or (not isinstance(rotationalVelocity, int)):
            return None

        header = Header()

        header.dataType = DataType.Control
        header.length = ControlPosition.getSize()
        header.from_ = DeviceType.Base
        header.to_ = DeviceType.Drone

        data = ControlPosition()

        data.positionX = float(positionX)
        data.positionY = float(positionY)
        data.positionZ = float(positionZ)
        data.velocity = float(velocity)
        data.heading = heading
        data.rotationalVelocity = rotationalVelocity

        return self.transfer(header, data)

    def move_distance(self, positionX, positionY, positionZ, velocity):
        if sys.platform != 'emscripten' and not self._swarm:
            return self._move_distance_desktop(positionX, positionY, positionZ, velocity)
        else:
            return asyncio.create_task(self._move_distance_emscripten(positionX, positionY, positionZ, velocity))

    def _move_distance_desktop(self, positionX, positionY, positionZ, velocity):
        from math import sqrt
        distance = sqrt(positionX ** 2 + positionY ** 2 + positionZ ** 2)  # distance travelled
        wait = (distance / velocity) + 2.5
        self.sendControlPosition(positionX, positionY, positionZ, velocity, 0, 0)
        time.sleep(wait)

    async def _move_distance_emscripten(self, positionX, positionY, positionZ, velocity):
        from math import sqrt
        distance = sqrt(positionX ** 2 + positionY ** 2 + positionZ ** 2)  # distance travelled
        wait = (distance / velocity) + 2.5
        await self.sendControlPosition(positionX, positionY, positionZ, velocity, 0, 0)
        await asyncio.sleep(wait)

    def move_forward(self, distance, units="cm", speed=0.5):
        """
        :param distance: the numerical value of the value to move
        :param units: can either be in inches, centimeters, meters, feet.
        :param speed: default 1 meter per second. Max is 2 meters/second.
        :return: N/A
        """
        if sys.platform != 'emscripten' and not self._swarm:
            return self._move_forward_desktop(distance, units, speed)
        else:
            return asyncio.create_task(self._move_forward_emscripten(distance, units, speed))

    def _move_forward_desktop(self, distance, units="cm", speed=1.0):
        if units == "cm":
            distance_meters = distance / 100
        elif units == "ft":
            distance_meters = distance / 3.28084
        elif units == "in":
            distance_meters = distance / 39.37
        elif units == "m":
            distance_meters = distance * 1
        else:
            print(Fore.RED + "Error: Not a valid unit." + Style.RESET_ALL)
            return

        # cap the speed
        if speed > 2:
            speed = 2
        elif speed < 0:
            speed = 0

        # read the current position and move relative to
        # position
        self.sendControlPosition(positionX=distance_meters,
                                    positionY=0,
                                    positionZ=0,
                                    velocity=speed,
                                    heading=0,
                                    rotationalVelocity=0)
        delay = distance_meters / speed
        time.sleep(delay + 1.0)

    async def _move_forward_emscripten(self, distance, units="cm", speed=1.0):
        if units == "cm":
            distance_meters = distance / 100
        elif units == "ft":
            distance_meters = distance / 3.28084
        elif units == "in":
            distance_meters = distance / 39.37
        elif units == "m":
            distance_meters = distance * 1
        else:
            print("Error: Not a valid unit.", color="error")
            return
        
        # cap the speed
        if speed > 2:
            speed = 2
        elif speed < 0:
            speed = 0

        await self.sendControlPosition(positionX=distance_meters,
                                    positionY=0,
                                    positionZ=0,
                                    velocity=speed,
                                    heading=0,
                                    rotationalVelocity=0)

        delay = distance_meters / speed
        await asyncio.sleep(delay + 1.0)

    def move_backward(self, distance, units="cm", speed=1.0):
        """
        :param distance: the numerical value of the value to move
        :param units: can either be in inches, centimeters, meters, feet.
        :param speed: default 1 meter per second. Max is 2 meters/second.
        :return: N/A
        """
        if sys.platform != 'emscripten' and not self._swarm:
            return self._move_backward_desktop(distance, units, speed)
        else:
            return asyncio.create_task(self._move_backward_emscripten(distance, units, speed))
    
    def _move_backward_desktop(self, distance, units="cm", speed=1.0):
        if units == "cm":
            distance_meters = distance / 100
        elif units == "ft":
            distance_meters = distance / 3.28084
        elif units == "in":
            distance_meters = distance / 39.37
        elif units == "m":
            distance_meters = distance * 1
        else:
            print(Fore.RED + "Error: Not a valid unit." + Style.RESET_ALL)
            return


        # cap the speed
        if speed > 2:
            speed = 2
        elif speed < 0:
            speed = 0

        self.sendControlPosition(positionX=-distance_meters,
                                    positionY=0,
                                    positionZ=0,
                                    velocity=speed,
                                    heading=0,
                                    rotationalVelocity=0)

        delay = distance_meters / speed
        time.sleep(delay + 1.0)

    async def _move_backward_emscripten(self, distance, units="cm", speed=1.0):
        if units == "cm":
            distance_meters = distance / 100
        elif units == "ft":
            distance_meters = distance / 3.28084
        elif units == "in":
            distance_meters = distance / 39.37
        elif units == "m":
            distance_meters = distance * 1
        else:
            print("Error: Not a valid unit.", color="error")
            return
        
        # cap the speed
        if speed > 2:
            speed = 2
        elif speed < 0:
            speed = 0

        await self.sendControlPosition(positionX=-distance_meters,
                                    positionY=0,
                                    positionZ=0,
                                    velocity=speed,
                                    heading=0,
                                    rotationalVelocity=0)

        delay = distance_meters / speed
        await asyncio.sleep(delay + 1.0)

    def move_left(self, distance, units="cm", speed=1.0):
        """
        :param distance: the numerical value of the value to move
        :param units: can either be in inches, centimeters, meters, feet.
        :param speed: default 1 meter per second. Max is 2 meters/second.
        :return: N/A
        """
        if sys.platform != 'emscripten' and not self._swarm:
            return self._move_left_desktop(distance, units, speed)
        else:
            return asyncio.create_task(self._move_left_emscripten(distance, units, speed))
    
    def _move_left_desktop(self, distance, units="cm", speed=1.0):
        if units == "cm":
            distance_meters = distance / 100
        elif units == "ft":
            distance_meters = distance / 3.28084
        elif units == "in":
            distance_meters = distance / 39.37
        elif units == "m":
            distance_meters = distance * 1
        else:
            print(Fore.RED + "Error: Not a valid unit." + Style.RESET_ALL)
            return

        # cap the speed
        if speed > 2:
            speed = 2
        elif speed < 0:
            speed = 0

        self.sendControlPosition(positionX=0,
                                    positionY=distance_meters,
                                    positionZ=0,
                                    velocity=speed,
                                    heading=0,
                                    rotationalVelocity=0)

        delay = distance_meters / speed
        time.sleep(delay + 1.0)

    async def _move_left_emscripten(self, distance, units="cm", speed=1.0):
        if units == "cm":
            distance_meters = distance / 100
        elif units == "ft":
            distance_meters = distance / 3.28084
        elif units == "in":
            distance_meters = distance / 39.37
        elif units == "m":
            distance_meters = distance * 1
        else:
            print("Error: Not a valid unit.", color="error")
            return
        
        # cap the speed
        if speed > 2:
            speed = 2
        elif speed < 0:
            speed = 0

        await self.sendControlPosition(positionX=0,
                                    positionY=distance_meters,
                                    positionZ=0,
                                    velocity=speed,
                                    heading=0,
                                    rotationalVelocity=0)

        delay = distance_meters / speed
        await asyncio.sleep(delay + 1.0)

    def move_right(self, distance, units="cm", speed=1.0):
        """
        :param distance: the numerical value of the value to move
        :param units: can either be in inches, centimeters, meters, feet.
        :param speed: default 1 meter per second. Max is 2 meters/second.
        :return: N/A
        """
        if sys.platform != 'emscripten' and not self._swarm:
            return self._move_right_desktop(distance, units, speed)
        else:
            return asyncio.create_task(self._move_right_emscripten(distance, units, speed))
    
    def _move_right_desktop(self, distance, units="cm", speed=1.0):
        if units == "cm":
            distance_meters = distance / 100
        elif units == "ft":
            distance_meters = distance / 3.28084
        elif units == "in":
            distance_meters = distance / 39.37
        elif units == "m":
            distance_meters = distance * 1
        else:
            print(Fore.RED + "Error: Not a valid unit." + Style.RESET_ALL)
            return

        # cap the speed
        if speed > 2:
            speed = 2
        elif speed < 0:
            speed = 0

        self.sendControlPosition(positionX=0,
                                    positionY=-distance_meters,
                                    positionZ=0,
                                    velocity=speed,
                                    heading=0,
                                    rotationalVelocity=0)

        delay = distance_meters / speed
        time.sleep(delay + 1.0)

    async def _move_right_emscripten(self, distance, units="cm", speed=1.0):
        if units == "cm":
            distance_meters = distance / 100
        elif units == "ft":
            distance_meters = distance / 3.28084
        elif units == "in":
            distance_meters = distance / 39.37
        elif units == "m":
            distance_meters = distance * 1
        else:
            print("Error: Not a valid unit.", color="error")
            return
        
        # cap the speed
        if speed > 2:
            speed = 2
        elif speed < 0:
            speed = 0

        await self.sendControlPosition(positionX=0,
                                    positionY=-distance_meters,
                                    positionZ=0,
                                    velocity=speed,
                                    heading=0,
                                    rotationalVelocity=0)

        delay = distance_meters / speed
        await asyncio.sleep(delay + 1.0)


    def send_absolute_position(self, positionX, positionY, positionZ, velocity, heading, rotationalVelocity):
        """
        drone movement command

        Use real values for position and velocity, and
        integer values for heading and rotational Velocity.
        :param positionX: float	-10.0 ~ 10.0	meter	Front (+), Back (-)
        :param positionY: float	-10.0 ~ 10.0	meter	Left(+), Right(-)
        :param positionZ: float	-10.0 ~ 10.0	meter	Up (+), Down (-)
        :param velocity: float	0.5 ~ 2.0	m/s	position movement speed
        :param heading: Int16	-360 ~ 360	degree	Turn left (+), turn right (-)
        :param rotationalVelocity: Int16	10 ~ 360	degree/s	left and right rotation speed
        :return: None
        """

        if sys.platform != 'emscripten' and not self._swarm:
            return self._send_absolute_position_desktop(positionX, positionY, positionZ, velocity, heading, rotationalVelocity)
        else:
            return asyncio.create_task(self._send_absolute_position_emscripten(positionX, positionY, positionZ, velocity, heading, rotationalVelocity))
    
    def _send_absolute_position_desktop(self, positionX, positionY, positionZ, velocity, heading, rotationalVelocity):
        if not (isinstance(positionX, float) or isinstance(positionX, int)):
            print(Fore.RED+"Error: positionX must be an int or float."+Style.RESET_ALL)
            return

        if not (isinstance(positionY, float) or isinstance(positionY, int)):
            print(Fore.RED+"Error: positionY must be an int or float."+Style.RESET_ALL)
            return

        if not (isinstance(positionZ, float) or isinstance(positionZ, int)):
            print(Fore.RED+"Error: positionZ must be an int or float."+Style.RESET_ALL)
            return

        if not (isinstance(velocity, float) or isinstance(velocity, int)):
            print(Fore.RED+"Error: velocity must be an int or float."+Style.RESET_ALL)
            return

        if (not isinstance(heading, int)) or (not isinstance(rotationalVelocity, int)):
            print(Fore.RED+"Error: heading or rotationalVelocity must be an int."+Style.RESET_ALL)
            return

        from math import sqrt, cos, sin, pi

        header = Header()

        header.dataType = DataType.Control
        header.length = ControlPosition.getSize()
        header.from_ = DeviceType.Base
        header.to_ = DeviceType.Drone

        data = ControlPosition()

        # store current position
        pos_data = None
        z_angle = None
        if self.information_data[1] == ModelNumber.Drone_12_Drone_P1:
            for _ in range(3):
                pos_data = self.get_position_data()
                z_angle = self.get_angle_z()
                time.sleep(0.1)
        else:
            for _ in range(3):
                pos_data = self.get_position_data()
                z_angle = self.get_angle_z()
                time.sleep(0.05)


        positionX = float(positionX)
        positionY = float(positionY)
        z_angle_rad = (pi / 180) * z_angle

        # calculate deltas in the world reference frame (the original reference frame when the drone is paired)
        dx = positionX - (self.previous_land[0] + pos_data[1])
        dy = positionY - (self.previous_land[1] + pos_data[2])
        dz = positionZ - pos_data[3]

        # transform deltas into drone's reference frame
        dx_prime = dx * cos(z_angle_rad) + dy * sin(z_angle_rad)
        dy_prime = -dx * sin(z_angle_rad) + dy * cos(z_angle_rad)
        dz_prime = dz

        # calculate the deltas in position needed to fly in those axis.
        data.positionX = dx_prime
        data.positionY = dy_prime
        data.positionZ = dz_prime
        data.velocity = float(velocity)
        # computes shortest possible delta needed to travel from "z_angle" to "heading"
        # modulo operator allows for heading over 360
        data.heading = ((int(heading) - z_angle + 180) % 360) - 180
        data.rotationalVelocity = rotationalVelocity

        temp = sqrt(data.positionX ** 2 + data.positionY ** 2 + data.positionZ ** 2) # distance travelled
        if data.rotationalVelocity == 0:
            wait = (temp / velocity) + 1
        elif data.velocity == 0:
            wait = (abs(data.heading) / data.rotationalVelocity) + 1
        else:
            # wait time is equal to the largest duration of movement: linear or rotational movement
            wait = max((temp / velocity) + 1, (abs(data.heading) / data.rotationalVelocity) + 1)

        self.transfer(header, data)
        sleep(wait+1.25)

    
    async def _send_absolute_position_emscripten(self, positionX, positionY, positionZ, velocity, heading, rotationalVelocity):
        if not (isinstance(positionX, float) or isinstance(positionX, int)):
            print("Error: positionX must be an int or float.", color="error")
            return

        if not (isinstance(positionY, float) or isinstance(positionY, int)):
            print("Error: positionY must be an int or float.", color="error")
            return

        if not (isinstance(positionZ, float) or isinstance(positionZ, int)):
            print("Error: positionZ must be an int or float.", color="error")
            return

        if not (isinstance(velocity, float) or isinstance(velocity, int)):
            print("Error: velocity must be an int or float.", color="error")
            return

        if (not isinstance(heading, int)) or (not isinstance(rotationalVelocity, int)):
            print("Error: heading or rotationalVelocity must be an int.", color="error")
            return

        from math import sqrt, cos, sin, pi

        header = Header()

        header.dataType = DataType.Control
        header.length = ControlPosition.getSize()
        header.from_ = DeviceType.Base
        header.to_ = DeviceType.Drone

        data = ControlPosition()

        # store current position
        pos_data = None
        z_angle = None
        if self.information_data[1] == ModelNumber.Drone_12_Drone_P1:
            for _ in range(3):
                pos_data = await self.get_position_data()
                z_angle = await self.get_angle_z()
                await asyncio.sleep(0.1)
        else:
            for _ in range(3):
                pos_data = await self.get_position_data()
                z_angle = await self.get_angle_z()
                await asyncio.sleep(0.05)

        positionX = float(positionX)
        positionY = float(positionY)
        z_angle_rad = (pi / 180) * z_angle

        # calculate deltas in the world reference frame (the original reference frame when the drone is paired)
        dx = positionX - (self.previous_land[0] + pos_data[1])
        dy = positionY - (self.previous_land[1] + pos_data[2])
        dz = positionZ - pos_data[3]

        # transform deltas into drone's reference frame
        dx_prime = dx * cos(z_angle_rad) + dy * sin(z_angle_rad)
        dy_prime = -dx * sin(z_angle_rad) + dy * cos(z_angle_rad)
        dz_prime = dz

        # calculate the deltas in position needed to fly in those axis.
        data.positionX = dx_prime
        data.positionY = dy_prime
        data.positionZ = dz_prime
        data.velocity = float(velocity)
        # computes shortest possible delta needed to travel from "z_angle" to "heading"
        # modulo operator allows for heading over 360
        data.heading = ((int(heading) - z_angle + 180) % 360) - 180
        data.rotationalVelocity = rotationalVelocity

        temp = sqrt(data.positionX ** 2 + data.positionY ** 2 + data.positionZ ** 2)  # distance travelled
        if data.rotationalVelocity == 0:
            wait = (temp / velocity) + 1
        elif data.velocity == 0:
            wait = (abs(data.heading) / data.rotationalVelocity) + 1
        else:
            # wait time is equal to the largest duration of movement: linear or rotational movement
            wait = max((temp / velocity) + 1, (abs(data.heading) / data.rotationalVelocity) + 1)

        await self.transfer(header, data)
        await asyncio.sleep(wait+1.25)

    def goto_waypoint(self, waypoint, velocity):
        """
        drone movement command

        Use real values for position and velocity, and
        integer values for heading and rotational Velocity.
        :param positionX: float	-10.0 ~ 10.0	meter	Front (+), Back (-)
        :param positionY: float	-10.0 ~ 10.0	meter	Left(+), Right(-)
        :param positionZ: float	-10.0 ~ 10.0	meter	Up (+), Down (-)
        :param velocity: float	0.5 ~ 2.0	m/s	position movement speed
        :param heading: Int16	-360 ~ 360	degree	Turn left (+), turn right (-)
        :param rotationalVelocity: Int16	10 ~ 360	degree/s	left and right rotation speed
        :return: None
        """
        if sys.platform != 'emscripten' and not self._swarm:
            return self._goto_waypoint_desktop(waypoint, velocity)
        else:
            return asyncio.create_task(self._goto_waypoint_emscripten(waypoint, velocity))
    
    def _goto_waypoint_desktop(self, waypoint, velocity):
        if not (isinstance(waypoint[0], float) or isinstance(waypoint[0], int)):
            return None

        if not (isinstance(waypoint[1], float) or isinstance(waypoint[1], int)):
            return None

        if not (isinstance(waypoint[2], float) or isinstance(waypoint[2], int)):
            return None

        if not (isinstance(velocity, float) or isinstance(velocity, int)):
            return None

        from math import sqrt

        header = Header()

        header.dataType = DataType.Control
        header.length = ControlPosition.getSize()
        header.from_ = DeviceType.Base
        header.to_ = DeviceType.Drone

        data = ControlPosition()

        data.positionX = float(waypoint[0]) - (self.previous_land[0] + self.get_position_data()[1])
        data.positionY = float(waypoint[1]) - (self.previous_land[1] + self.get_position_data()[2])
        data.positionZ = data.positionZ
        data.velocity = float(velocity)
        data.heading = 0
        data.rotationalVelocity = 0

        temp = sqrt(data.positionX ** 2 + data.positionY ** 2)
        wait = (temp / velocity) + 1
        self.transfer(header, data)
        time.sleep(wait)

    async def _goto_waypoint_emscripten(self, waypoint, velocity):
        if not (isinstance(waypoint[0], float) or isinstance(waypoint[0], int)):
            return None

        if not (isinstance(waypoint[1], float) or isinstance(waypoint[1], int)):
            return None

        if not (isinstance(waypoint[2], float) or isinstance(waypoint[2], int)):
            return None

        if not (isinstance(velocity, float) or isinstance(velocity, int)):
            return None

        from math import sqrt

        header = Header()

        header.dataType = DataType.Control
        header.length = ControlPosition.getSize()
        header.from_ = DeviceType.Base
        header.to_ = DeviceType.Drone

        data = ControlPosition()

        data.positionX = float(waypoint[0]) - (self.previous_land[0] + (await self.get_position_data())[1])
        data.positionY = float(waypoint[1]) - (self.previous_land[1] + (await self.get_position_data())[2])
        data.positionZ = data.positionZ
        data.velocity = float(velocity)
        data.heading = 0
        data.rotationalVelocity = 0

        temp = sqrt(data.positionX ** 2 + data.positionY ** 2)
        wait = (temp / velocity) + 1
        await self.transfer(header, data)
        await asyncio.sleep(wait)

    # Control End
    def percent_error(self, desired, current):
        """
        Calculates the percent error of two values.

        :param desired: numerical value
        :param current: numerical value
        :return: positive or negative value of error percent
        """

        error_percent = (current - desired)

        # cap the value between -100% and 100%
        if error_percent > 100:
            error_percent = 100
        elif error_percent < -100:
            error_percent = -100

        return error_percent

    def turn_degree(self, degree=90, timeout=3, p_value=10):
        """
        Turns right or left with absolute reference frame to
        drone's initial heading.
        Positive degrees turn to right and
        negative degrees turn to the left.

        :param degree: integer from -180->180 degrees
        :param timeout: duration in seconds that drone will try to turn
        :param p_value: the gain of the proportional controller,
        if this increased CDE will turn quicker, the smaller the slower.
        examples values 0.5 -> 1.5
        :return: None
        """
        if sys.platform != 'emscripten' and not self._swarm:
            return self._turn_degree_desktop(degree, timeout, p_value)
        else:
            return asyncio.create_task(self._turn_degree_emscripten(degree, timeout, p_value))
    
    def _turn_degree_desktop(self, degree, timeout=3, p_value=10):
        # make sure you arent moving
        self.hover(0.01)
        init_time = time.time()
        time_elapsed = time.time() - init_time
        init_angle = self.get_angle_z()
        desired_angle = degree

        if desired_angle >= 180:
            desired_angle = 180
        elif desired_angle <= -180:
            desired_angle = -180

        while time_elapsed < timeout:
            time_elapsed = time.time() - init_time
            current_angle = self.get_angle_z()
            # find the distance to the desired angle
            degree_diff = desired_angle - current_angle

            # save the first distance turning in one direction
            degree_dist_1 = abs(degree_diff)

            # now we find what direction to turn
            # sign will be either +1 or -1
            if degree_dist_1 > 0:
                sign = degree_diff / degree_dist_1
            else:
                sign = 1

            # now save the second distance going
            # the opposite direction turning
            degree_dist_2 = 360 - degree_dist_1

            # find which one is the shorter path
            if degree_dist_1 <= degree_dist_2:
                # normalize the degree distance so it goes from 0-100%
                # where 100% would be 360 degree distance
                error_percent = int(degree_dist_1 / 360 * 100)
                error_percent = int(error_percent * p_value)
                # cap the value between -100% and 100%
                if error_percent > 100:
                    error_percent = 100
                elif error_percent < -100:
                    error_percent = -100
                # now we can use the sign to determine the turning direction
                speed = int(sign * error_percent)
                self.sendControl(0, 0, speed, 0)
                time.sleep(0.005)
                # print( error_percent, " ,", current_angle," ,", sign," ,", degree_dist_1,
                #      " ,", degree_dist_2, " ,", speed, " ,", time.time(), " ,", desired_angle)


            elif degree_dist_2 < degree_dist_1:
                error_percent = int(degree_dist_2 / 360 * 100)
                error_percent = int(error_percent * p_value)
                # cap the value between -100% and 100%
                if error_percent > 100:
                    error_percent = 100
                elif error_percent < -100:
                    error_percent = -100
                speed = int(-1 * sign * error_percent)
                self.sendControl(0, 0, speed, 0)
                time.sleep(0.005)
                # print( error_percent, " ,", current_angle," ,", sign," ,", degree_dist_1,
                #       " ,", degree_dist_2, " ,", speed, " ,", time.time(), " ,", desired_angle)

        # stop any movement just in case
        self.hover(0.05)
    
    async def _turn_degree_emscripten(self, degree, timeout=3, p_value=10):
        # make sure you arent moving
        await self.hover(0.01)
        init_time = time.time()
        time_elapsed = time.time() - init_time
        init_angle = await self.get_angle_z()
        desired_angle = degree

        if desired_angle >= 180:
            desired_angle = 180
        elif desired_angle <= -180:
            desired_angle = -180

        while time_elapsed < timeout:
            time_elapsed = time.time() - init_time
            current_angle = await self.get_angle_z()
            # find the distance to the desired angle
            degree_diff = desired_angle - current_angle

            # save the first distance turning in one direction
            degree_dist_1 = abs(degree_diff)

            # now we find what direction to turn
            # sign will be either +1 or -1
            if degree_dist_1 > 0:
                sign = degree_diff / degree_dist_1
            else:
                sign = 1

            # now save the second distance going
            # the opposite direction turning
            degree_dist_2 = 360 - degree_dist_1

            # find which one is the shorter path
            if degree_dist_1 <= degree_dist_2:
                # normalize the degree distance so it goes from 0-100%
                # where 100% would be 360 degree distance
                error_percent = int(degree_dist_1 / 360 * 100)
                error_percent = int(error_percent * p_value)
                # cap the value between -100% and 100%
                if error_percent > 100:
                    error_percent = 100
                elif error_percent < -100:
                    error_percent = -100
                # now we can use the sign to determine the turning direction
                speed = int(sign * error_percent)
                await self.sendControl(0, 0, speed, 0)
                await asyncio.sleep(0.005)
                # print( error_percent, " ,", current_angle," ,", sign," ,", degree_dist_1,
                #      " ,", degree_dist_2, " ,", speed, " ,", time.time(), " ,", desired_angle)


            elif degree_dist_2 < degree_dist_1:
                error_percent = int(degree_dist_2 / 360 * 100)
                error_percent = int(error_percent * p_value)
                # cap the value between -100% and 100%
                if error_percent > 100:
                    error_percent = 100
                elif error_percent < -100:
                    error_percent = -100
                speed = int(-1 * sign * error_percent)
                await self.sendControl(0, 0, speed, 0)
                await asyncio.sleep(0.005)
                # print( error_percent, " ,", current_angle," ,", sign," ,", degree_dist_1,
                #       " ,", degree_dist_2, " ,", speed, " ,", time.time(), " ,", desired_angle)

        # stop any movement just in case
        await self.hover(0.05)

    def turn_left(self, degree=90, timeout=3):
        if sys.platform != 'emscripten' and not self._swarm:
            return self._turn_left_desktop(degree, timeout)
        else:
            return asyncio.create_task(self._turn_left_emscripten(degree, timeout))
    
    def _turn_left_desktop(self, degree=90, timeout=3):
        # make sure it is an int and a positive value
        degree = int(abs(degree))
        # cap the max value to turn to 180
        if degree >= 180:
            degree = 179

        current_degree = self.get_angle_z()
        # positive degrees are to the left
        des_degree = degree + current_degree
        if des_degree > 180:
            new_degree = -(360 - des_degree)
            self.turn_degree(new_degree, timeout=timeout)
        else:
            self.turn_degree(des_degree, timeout=timeout)

    async def _turn_left_emscripten(self, degree=90, timeout=3):
        # make sure it is an int and a positive value
        degree = int(abs(degree))
        # cap the max value to turn to 180
        if degree >= 180:
            degree = 179

        current_degree = await self.get_angle_z()
        # positive degrees are to the left
        des_degree = degree + current_degree
        if des_degree > 180:
            new_degree = -(360 - des_degree)
            await self.turn_degree(new_degree, timeout=timeout)
        else:
            await self.turn_degree(des_degree, timeout=timeout)

    def turn_right(self, degree=90, timeout=3):
        if sys.platform != 'emscripten' and not self._swarm:
            return self._turn_right_desktop(degree, timeout)
        else:
            return asyncio.create_task(self._turn_right_emscripten(degree, timeout))
    
    def _turn_right_desktop(self, degree=90, timeout=3):
        # make sure it is an int and a positive value
        degree = int(abs(degree))
        # cap the max value to turn to 180
        if degree >= 180:
            degree = 179

        current_degree = self.get_angle_z()
        # positive degrees are to the left
        des_degree = current_degree - degree
        if des_degree < -180:
            new_degree = (360 - des_degree)
            self.turn_degree(new_degree, timeout=timeout)
        else:
            self.turn_degree(des_degree, timeout=timeout)
    
    async def _turn_right_emscripten(self, degree=90, timeout=3):
        # make sure it is an int and a positive value
        degree = int(abs(degree))
        # cap the max value to turn to 180
        if degree >= 180:
            degree = 179

        current_degree = await self.get_angle_z()
        # positive degrees are to the left
        des_degree = current_degree - degree
        if des_degree < -180:
            new_degree = (360 - des_degree)
            await self.turn_degree(new_degree, timeout=timeout)
        else:
            await self.turn_degree(des_degree, timeout=timeout)

    # Flight Sequences Start
    def avoid_wall(self, timeout=2, distance=70):
        """
        A looped method that makes the drone fly forward until it reaches
        a desired distance.
        The range of front sensor is from 0cm-100cm

        :param timeout:  duration in seconds that function will run
        :param distance: distance in cm the drone will stop in front of object
        :return:
        """
        if sys.platform != 'emscripten' and not self._swarm:
            return self._avoid_wall_desktop(timeout, distance)
        else:
            return asyncio.create_task(self._avoid_wall_emscripten(timeout, distance))
    
    def _avoid_wall_desktop(self, timeout=2, distance=70):
        threshold = 20
        p_value = 0.4
        counter = 0

        init_time = time.time()
        time_elapsed = time.time() - init_time
        prev_distance = 0
        change_in_distance = 0
        while time_elapsed < timeout:
            time_elapsed = time.time() - init_time
            current_distance = self.get_front_range("cm")
            change_in_distance = prev_distance - current_distance
            prev_distance = current_distance
            data_now = self.get_flow_data()
            error_percent = self.percent_error(desired=distance, current=current_distance)
            # speed can range from -100 to 100
            speed = int(error_percent * p_value)
            # print(data_now[0], ",", current_distance, ",",change_in_distance, ",",data_now[1], ",",data_now[2])

            if current_distance > distance + threshold or current_distance < distance - threshold:
                self.sendControl(0, speed, 0, 0)
                time.sleep(0.005)
            else:
                self.hover()
                counter = counter + 1
                if counter == 20:
                    break
        self.hover()

    async def _avoid_wall_emscripten(self, timeout=2, distance=70):
        threshold = 20
        p_value = 0.4
        counter = 0

        init_time = time.time()
        time_elapsed = time.time() - init_time
        prev_distance = 0
        change_in_distance = 0
        while time_elapsed < timeout:
            time_elapsed = time.time() - init_time
            current_distance = await self.get_front_range("cm")
            change_in_distance = prev_distance - current_distance
            prev_distance = current_distance
            data_now = await self.get_flow_data()
            error_percent = self.percent_error(desired=distance, current=current_distance)
            # speed can range from -100 to 100
            speed = int(error_percent * p_value)
            # print(data_now[0], ",", current_distance, ",",change_in_distance, ",",data_now[1], ",",data_now[2])

            if current_distance > distance + threshold or current_distance < distance - threshold:
                await self.sendControl(0, speed, 0, 0)
                await asyncio.sleep(0.005)
            else:
                await self.hover()
                counter = counter + 1
                if counter == 20:
                    break
        await self.hover()

    def keep_distance(self, timeout=2, distance=50):
        """
        A looped method that makes the drone fly forward until it reaches
        a desired distance. The drone will keep that distance.
        The range of front sensor is from 0cm-100cm

        :param timeout: duration in seconds that function will run
        :param distance: distance in cm the drone will maintain in front of object
        :return:
        """
        if sys.platform != 'emscripten' and not self._swarm:
            return self._keep_distance_desktop(timeout, distance)
        else:
            return asyncio.create_task(self._keep_distance_emscripten(timeout, distance))
    
    def _keep_distance_desktop(self, timeout=2, distance=50):
        threshold = 10
        p_value = 0.4

        init_time = time.time()
        time_elapsed = time.time() - init_time
        while time_elapsed < timeout:
            time_elapsed = time.time() - init_time
            current_distance = self.get_front_range("cm")
            error_percent = self.percent_error(desired=distance, current=current_distance)
            # speed can range from -100 to 100
            speed = int(error_percent * p_value)

            if current_distance > distance + threshold or current_distance < distance - threshold:
                self.sendControl(0, speed, 0, 0)
                time.sleep(0.005)
            else:
                self.hover()

    async def _keep_distance_emscripten(self, timeout=2, distance=50):
        threshold = 10
        p_value = 0.4

        init_time = time.time()
        time_elapsed = time.time() - init_time
        while time_elapsed < timeout:
            time_elapsed = time.time() - init_time
            current_distance = await self.get_front_range("cm")
            error_percent = self.percent_error(desired=distance, current=current_distance)
            # speed can range from -100 to 100
            speed = int(error_percent * p_value)

            if current_distance > distance + threshold or current_distance < distance - threshold:
                await self.sendControl(0, speed, 0, 0)
                await asyncio.sleep(0.005)
            else:
                await self.hover()

    def detect_wall(self, distance=50):
        """
        Returns True when a distance below the threshold is reached.
        The range of front sensor is from 0cm-100cm

        :param distance: threshold in millimeters that returns True
        :return: Boolean
        """
        if sys.platform != 'emscripten' and not self._swarm:
            return self._detect_wall_desktop(distance)
        else:
            return asyncio.create_task(self._detect_wall_emscripten(distance))
    
    def _detect_wall_desktop(self, distance=50):
        current_distance = self.get_front_range("cm")

        if current_distance < distance:
            return True
        else:
            return False
        
    async def _detect_wall_emscripten(self, distance=50):
        current_distance = await self.get_front_range("cm")

        if current_distance < distance:
            return True
        else:
            return False

    def flip(self, direction="back"):
        """
        Calls sendFlip() command to flip the drone in desired direction.
        Options are: "front", "back", "left", and "right"

        :param string: that determines flip direction
        :return: None
        """

        if sys.platform != 'emscripten' and not self._swarm:
            return self._flip_desktop(direction)
        elif sys.platform != 'emscripten' and self._swarm:
            return self._flip_swarm(direction)
        else:
            return asyncio.create_task(self._flip_emscripten(direction))
    
    def _flip_desktop(self, direction="back"):
        state = self.get_state_data()
        battery = state[6]
        if battery < 50:
            print(Fore.YELLOW + "Warning: Unable to perform flip; battery level is below 50%." + Style.RESET_ALL)
            self.controller_buzzer(587, 100)
            self.controller_buzzer(554, 100)
            self.controller_buzzer(523, 100)
            self.controller_buzzer(494, 150)
            return

        if direction == "back":
            mode = FlightEvent.FlipRear
        elif direction == "front":
            mode = FlightEvent.FlipFront
        elif direction == "right":
            mode = FlightEvent.FlipRight
        elif direction == "left":
            mode = FlightEvent.FlipLeft
        else:
            print("Invalid flip direction.")
            return

        self.sendFlip(mode)

    async def _flip_swarm(self, direction="back"):
        state = await self.get_state_data()
        battery = state[6]
        if battery < 50:
            print("Warning: Unable to perform flip; battery level is below 50%.", color="warning")
            await self.controller_buzzer(587, 100)
            await self.controller_buzzer(554, 100)
            await self.controller_buzzer(523, 100)
            await self.controller_buzzer(494, 150)
            return

        if direction == "back":
            mode = FlightEvent.FlipRear
        elif direction == "front":
            mode = FlightEvent.FlipFront
        elif direction == "right":
            mode = FlightEvent.FlipRight
        elif direction == "left":
            mode = FlightEvent.FlipLeft
        else:
            print("Invalid flip direction.")
            return

        await self.sendFlip(mode)

    async def _flip_emscripten(self, direction="back"):
        battery = await self.get_battery()
        if battery < 50:
            print("Warning: Unable to perform flip; battery level is below 50%.", color="warning")
            await self.controller_buzzer(587, 100)
            await self.controller_buzzer(554, 100)
            await self.controller_buzzer(523, 100)
            await self.controller_buzzer(494, 150)
            return

        if direction == "back":
            mode = FlightEvent.FlipRear
        elif direction == "front":
            mode = FlightEvent.FlipFront
        elif direction == "right":
            mode = FlightEvent.FlipRight
        elif direction == "left":
            mode = FlightEvent.FlipLeft
        else:
            print("Invalid flip direction.")
            return

        await self.sendFlip(mode)

    def sendFlip(self, mode):

        header = Header()
        header.dataType = DataType.Command
        header.length = Command.getSize()
        header.from_ = DeviceType.Base
        header.to_ = DeviceType.Drone

        data = Command()
        data.commandType = CommandType.FlightEvent
        data.option = mode.value
        return self.transfer(header, data)

    def square(self, speed=60, seconds=1, direction=1):
        """
        Flies the drone in the shape of a square. Defaults to the right.

        :param speed: integer from 0 to 100
        :param seconds:  integer that describes the duration of each side
        :param direction: integer, -1 or 1 that determines direction.
        :return:
        """

        if sys.platform != 'emscripten' and not self._swarm:
            return self._square_desktop(speed, seconds, direction)
        else:
            return asyncio.create_task(self._square_emscripten(speed, seconds, direction))
    
    def _square_desktop(self, speed=60, seconds=1, direction=1):
        power = int(speed)
        duration = int(seconds * 1000)

        self.sendControlWhile(0, power, 0, 0, duration)  # Pitch
        self.sendControlWhile(0, -power, 0, 0, 50)

        self.sendControlWhile(power * direction, 0, 0, 0, duration)  # roll
        self.sendControlWhile(-power * direction, 0, 0, 0, 50)

        self.sendControlWhile(0, -power, 0, 0, duration)  # -Pitch
        self.sendControlWhile(0, power, 0, 0, 50)

        self.sendControlWhile(-power * direction, 0, 0, 0, duration)  # Roll
        self.sendControlWhile(power * direction, 0, 0, 0, 50)

    async def _square_emscripten(self, speed=60, seconds=1, direction=1):
        power = int(speed)
        duration = int(seconds * 1000)

        await self.sendControlWhile(0, power, 0, 0, duration)  # Pitch
        await self.sendControlWhile(0, -power, 0, 0, 50)

        await self.sendControlWhile(power * direction, 0, 0, 0, duration)  # roll
        await self.sendControlWhile(-power * direction, 0, 0, 0, 50)

        await self.sendControlWhile(0, -power, 0, 0, duration)  # -Pitch
        await self.sendControlWhile(0, power, 0, 0, 50)

        await self.sendControlWhile(-power * direction, 0, 0, 0, duration)  # Roll
        await self.sendControlWhile(power * direction, 0, 0, 0, 50)

    def triangle(self, speed=60, seconds=1, direction=1):
        """
        Flies the drone in the shape of a triangle. Defaults to the right.

        :param speed: integer from 0 to 100
        :param seconds:  integer that describes the duration of each side
        :param direction: integer, -1 or 1 that determines direction.
        :return:
                """
        if sys.platform != 'emscripten' and not self._swarm:
            return self._triangle_desktop(speed, seconds, direction)
        else:
            return asyncio.create_task(self._triangle_emscripten(speed, seconds, direction))
    
    def _triangle_desktop(self, speed=60, seconds=1, direction=1):
        power = int(speed)
        duration = int(seconds * 1000)

        self.sendControlWhile(power * direction, power, 0, 0, duration)  # Pitch
        self.sendControlWhile(-power * direction, -power, 0, 0, 50)

        self.sendControlWhile(power * direction, -power, 0, 0, duration)  # -Pitch
        self.sendControlWhile(-power * direction, power, 0, 0, 50)

        self.sendControlWhile(-power * direction, 0, 0, 0, duration)  # Roll
        self.sendControlWhile(power * direction, 0, 0, 0, 50)

    async def _triangle_emscripten(self, speed=60, seconds=1, direction=1):
        power = int(speed)
        duration = int(seconds * 1000)

        await self.sendControlWhile(power * direction, power, 0, 0, duration)  # Pitch
        await self.sendControlWhile(-power * direction, -power, 0, 0, 50)

        await self.sendControlWhile(power * direction, -power, 0, 0, duration)  # -Pitch
        await self.sendControlWhile(-power * direction, power, 0, 0, 50)

        await self.sendControlWhile(-power * direction, 0, 0, 0, duration)  # Roll
        await self.sendControlWhile(power * direction, 0, 0, 0, 50)

    def triangle_turn(self, speed=60, seconds=2, direction=1):
        """
        Flies the drone in the shape of a triangle by changing yaw. Defaults to the right.

        :param speed: integer from 0 to 100
        :param seconds:  integer that describes the duration of each side
        :param direction: integer, -1 or 1 that determines direction.
        :return:
        """
        if sys.platform != 'emscripten' and not self._swarm:
            return self._triangle_turn_desktop(speed, seconds, direction)
        else:
            return asyncio.create_task(self._triangle_turn_emscripten(speed, seconds, direction))
    
    def _triangle_turn_desktop(self, speed=60, seconds=2, direction=1):
        # TODO Check this
        power = int(speed)
        duration = int(seconds * 1000)
        self.sendControlWhile(power * direction, power, 0, 0, duration)
        self.sendControlWhile(power * direction, -power, 0, 0, duration)
        self.sendControlWhile(-power * direction, 0, 0, 0, duration)

    async def _triangle_turn_emscripten(self, speed=60, seconds=2, direction=1):
        # TODO Check this
        power = int(speed)
        duration = int(seconds * 1000)
        await self.sendControlWhile(power * direction, power, 0, 0, duration)
        await self.sendControlWhile(power * direction, -power, 0, 0, duration)
        await self.sendControlWhile(-power * direction, 0, 0, 0, duration)

    def spiral(self, speed=50, seconds=5, direction=1):
        """
        Flies the drone in a downward spiral for a specified duration. Defaults to the right.

        :param speed: integer from 0 to 100
        :param seconds:  integer that describes the duration of the movement
        :param direction: integer, -1 or 1 that determines direction.
        :return:
        """
        if sys.platform != 'emscripten' and not self._swarm:
            return self._spiral_desktop(speed, seconds, direction)
        else:
            return asyncio.create_task(self._spiral_emscripten(speed, seconds, direction))
    
    def _spiral_desktop(self, speed=50, seconds=5, direction=1):
        power = int(speed)
        self.sendControl(0, power, 100 * -direction, -power)
        time.sleep(seconds)

    async def _spiral_emscripten(self, speed=50, seconds=5, direction=1):
        power = int(speed)
        await self.sendControl(0, power, 100 * -direction, -power)
        await asyncio.sleep(seconds)

    def circle(self, speed=75, direction=1):
        """
        Flies the drone in a circular turn. Defaults to the right.
        
        :param speed: integer from 0 to 100
        :param direction: integer, -1 or 1 that determines direction.
        :return:
        """
        if sys.platform != 'emscripten' and not self._swarm:
            return self._circle_desktop(speed, direction)
        else:
            return asyncio.create_task(self._circle_emscripten(speed, direction))
    
    def _circle_desktop(self, speed=75, direction=1):
        # TODO Fix this later with gyro
        self.sendControl(0, speed, direction * speed, 0)
        time.sleep(5)

    async def _circle_emscripten(self, speed=75, direction=1):
        # TODO Fix this later with gyro
        await self.sendControl(0, speed, direction * speed, 0)
        await asyncio.sleep(5)

    def circle_turn(self, speed=30, seconds=1, direction=1):
        if sys.platform != 'emscripten' and not self._swarm:
            return self._circle_turn_desktop(speed, seconds, direction)
        else:
            return asyncio.create_task(self._circle_turn_emscripten(speed, seconds, direction))
    
    def _circle_turn_desktop(self, speed=30, seconds=1, direction=1):
        pitch = int(speed)
        roll = 0
        for i in range(4):
            self.sendControlWhile(roll, pitch, 0, 0, 400)
            roll = roll + 10
            pitch = pitch - 10
        for i in range(4):
            self.sendControlWhile(roll, pitch, 0, 0, 400)
            roll = roll - 10
            pitch = pitch - 10
        for i in range(4):
            self.sendControlWhile(roll, pitch, 0, 0, 400)
            roll = roll - 10
            pitch = pitch + 10
        for i in range(4):
            self.sendControlWhile(roll, pitch, 0, 0, 400)
            roll = roll + 10
            pitch = pitch + 10

    async def _circle_turn_emscripten(self, speed=30, seconds=1, direction=1):
        pitch = int(speed)
        roll = 0
        for i in range(4):
            await self.sendControlWhile(roll, pitch, 0, 0, 400)
            roll = roll + 10
            pitch = pitch - 10
        for i in range(4):
            await self.sendControlWhile(roll, pitch, 0, 0, 400)
            roll = roll - 10
            pitch = pitch - 10
        for i in range(4):
            await self.sendControlWhile(roll, pitch, 0, 0, 400)
            roll = roll - 10
            pitch = pitch + 10
        for i in range(4):
            await self.sendControlWhile(roll, pitch, 0, 0, 400)
            roll = roll + 10
            pitch = pitch + 10

    def sway(self, speed=30, seconds=2, direction=1):
        """
        Moves the drone left and right twice. Defaults to start to the left

        :param speed: integer from 0 to 100
        :param seconds:  integer that describes the duration of the movement
        :param direction: integer, -1 or 1 that determines direction.
        :return:
        """
        if sys.platform != 'emscripten' and not self._swarm:
            return self._sway_desktop(speed, seconds, direction)
        else:
            return asyncio.create_task(self._sway_emscripten(speed, seconds, direction))
    
    def _sway_desktop(self, speed=30, seconds=2, direction=1):
        power = int(speed)
        duration = int(seconds * 1000)
        for i in range(2):
            self.sendControlWhile(-power * direction, 0, 0, 0, duration)
            self.sendControlWhile(power * direction, 0, 0, 0, duration)

    async def _sway_emscripten(self, speed=30, seconds=2, direction=1):
        power = int(speed)
        duration = int(seconds * 1000)
        for i in range(2):
            await self.sendControlWhile(-power * direction, 0, 0, 0, duration)
            await self.sendControlWhile(power * direction, 0, 0, 0, duration)

    # Flight Sequences End

    # Setup Start

    def sendCommand(self, commandType, option=0):
        """
        Used to send commands to the drone.
        The option must contain either a value value
         of each format or a numeric value.
        https://dev.byrobot.co.kr/documents/kr/products/e_drone/library/python/e_drone/04_protocol/#CommandType
        :param commandType: CommandType	command type
        :param option: 	ModeControlFlight	option
                        FlightEvent
                        Headless
                        Trim
                        UInt8
        :return: transfer()
        """

        if ((not isinstance(commandType, CommandType)) or
                (not isinstance(option, int))):
            return None

        header = Header()

        header.dataType = DataType.Command
        header.length = Command.getSize()
        header.from_ = DeviceType.Base
        header.to_ = DeviceType.Drone

        data = Command()

        data.commandType = commandType
        data.option = option

        return self.transfer(header, data)

    # Sounds

    def start_drone_buzzer(self, note):
        """
        starts buzzer indefinitely.

        :param note: integer frequency or Note object
        :param duration: duration of the note in milliseconds
        :return: None
        """

        if isinstance(note, int):
            mode = BuzzerMode.Hz
            note_value = note

        elif isinstance(note, Note):
            mode = BuzzerMode.Scale
            note_value = note.value

        else:
            print("Input must be Note or integer.")
            return self.transfer(header, data)

        header = Header()

        header.dataType = DataType.Buzzer
        header.length = Buzzer.getSize()
        header.from_ = DeviceType.Tester
        header.to_ = DeviceType.Drone

        data = Buzzer()

        data.mode = mode
        data.value = note_value
        data.time = 65535
        
        if sys.platform != 'emscripten' and not self._swarm:
            return self._start_drone_buzzer_desktop(header, data)
        else:
            return asyncio.create_task(self._start_drone_buzzer_emscripten(header, data))

    def _start_drone_buzzer_desktop(self, header, data):
        self.transfer(header, data)
        sleep(0.07)
    
    async def _start_drone_buzzer_emscripten(self, header, data):
        await self.transfer(header, data)
        await asyncio.sleep(0.07)

    def stop_drone_buzzer(self):
        """
        stops buzzer.

        :return: None
        """
        header = Header()

        header.dataType = DataType.Buzzer
        header.length = Buzzer.getSize()
        header.from_ = DeviceType.Tester
        header.to_ = DeviceType.Drone

        data = Buzzer()

        data.mode = BuzzerMode.Mute
        data.value = BuzzerMode.Mute.value
        data.time = 1

        if sys.platform != 'emscripten' and not self._swarm:
            return self._stop_drone_buzzer_desktop(header, data)
        else:
            return asyncio.create_task(self._stop_drone_buzzer_emscripten(header, data))
    
    def _stop_drone_buzzer_desktop(self, header, data):
        self.transfer(header, data)
        sleep(0.1)
    
    async def _stop_drone_buzzer_emscripten(self, header, data):
        await self.transfer(header, data)
        await asyncio.sleep(0.1)

    def start_controller_buzzer(self, note):
        """
       starts buzzer indefinitely.

        :param note: integer frequency or Note object
        :param duration: duration of the note in milliseconds
        :return: None
        """

        if isinstance(note, int):
            mode = BuzzerMode.Hz
            note_value = note

        elif isinstance(note, Note):
            mode = BuzzerMode.Scale
            note_value = note.value

        else:
            print("Input must be Note or integer.")
            return

        header = Header()

        header.dataType = DataType.Buzzer
        header.length = Buzzer.getSize()
        header.from_ = DeviceType.Tester
        header.to_ = DeviceType.Controller

        data = Buzzer()

        data.mode = mode
        data.value = note_value
        data.time = 65535
        
        if sys.platform != 'emscripten' and not self._swarm:
            return self._start_controller_buzzer_desktop(header, data)
        else:
            return asyncio.create_task(self._start_controller_buzzer_emscripten(header, data))
    
    def _start_controller_buzzer_desktop(self, header, data):
        self.transfer(header, data)
        sleep(0.07)

    async def _start_controller_buzzer_emscripten(self, header, data):
        await self.transfer(header, data)
        await asyncio.sleep(0.07)

    def stop_controller_buzzer(self):
        """
        stops buzzer.

        :return: None
        """
        header = Header()

        header.dataType = DataType.Buzzer
        header.length = Buzzer.getSize()
        header.from_ = DeviceType.Tester
        header.to_ = DeviceType.Controller

        data = Buzzer()

        data.mode = BuzzerMode.Mute
        data.value = BuzzerMode.Mute.value
        data.time = 1

        if sys.platform != 'emscripten' and not self._swarm:
            return self._stop_controller_buzzer_desktop(header, data)
        else:
            return asyncio.create_task(self._stop_controller_buzzer_emscripten(header, data))
    
    def _stop_controller_buzzer_desktop(self, header, data):
        self.transfer(header, data)
        sleep(0.1)
    
    async def _stop_controller_buzzer_emscripten(self, header, data):
        await self.transfer(header, data)
        await asyncio.sleep(0.1)

    def controller_buzzer(self, note, duration):
        """
        Plays a note using the controller's buzzer.

        :param note: integer frequency or Note object
        :param duration: duration of the note in milliseconds
        :return: None
        """
        if sys.platform != 'emscripten' and not self._swarm:
            return self._controller_buzzer_desktop(note, duration)
        else:
            return asyncio.create_task(self._controller_buzzer_emscripten(note, duration))
    
    def _controller_buzzer_desktop(self, note, duration):
        if isinstance(note, int):
            mode = BuzzerMode.Hz

        elif isinstance(note, Note):
            mode = BuzzerMode.Scale
            note = note.value

        else:
            print("Input must be Note or integer.")
            return

        self.sendBuzzer(mode, note, duration)
        time.sleep(duration / 1000)
        self.sendBuzzerMute(0.01)

    async def _controller_buzzer_emscripten(self, note, duration):
        if isinstance(note, int):
            mode = BuzzerMode.Hz

        elif isinstance(note, Note):
            mode = BuzzerMode.Scale
            note = note.value

        else:
            print("Input must be Note or integer.")
            return

        await self.sendBuzzer(mode, note, duration)
        await asyncio.sleep(duration / 1000)
        await self.sendBuzzerMute(10) # 10ms

    def drone_buzzer(self, note, duration):
        """
        Plays a note using the drone's buzzer.

        :param note: integer frequency or Note object
        :param duration: duration of the note in milliseconds
        :return: None
        """
        if sys.platform != 'emscripten' and not self._swarm:
            return self._drone_buzzer_desktop(note, duration)
        else:
            return asyncio.create_task(self._drone_buzzer_emscripten(note, duration))
    
    def _drone_buzzer_desktop(self, note, duration):
        if isinstance(note, int):
            mode = BuzzerMode.Hz
            note_value = note

        elif isinstance(note, Note):
            mode = BuzzerMode.Scale
            note_value = note.value

        else:
            print("Input must be Note or integer.")
            return

        header = Header()

        header.dataType = DataType.Buzzer
        header.length = Buzzer.getSize()
        header.from_ = DeviceType.Tester
        header.to_ = DeviceType.Drone

        data = Buzzer()

        data.mode = mode
        data.value = note_value
        data.time = duration

        self.transfer(header, data)
        time.sleep(duration / 1000)
        self.sendBuzzerMute(0.01)

    async def _drone_buzzer_emscripten(self, note, duration):
        if isinstance(note, int):
            mode = BuzzerMode.Hz
            note_value = note

        elif isinstance(note, Note):
            mode = BuzzerMode.Scale
            note_value = note.value

        else:
            print("Input must be Note or integer.")
            return

        header = Header()

        header.dataType = DataType.Buzzer
        header.length = Buzzer.getSize()
        header.from_ = DeviceType.Base
        header.to_ = DeviceType.Drone

        data = Buzzer()

        data.mode = mode
        data.value = note_value
        data.time = duration

        await self.transfer(header, data)
        await asyncio.sleep(duration / 1000)
        await self.sendBuzzerMute(10) # 10ms

    # Lights

    def set_drone_LED(self, r, g, b, brightness):
        """
        Changes the drone LED to a specified color using RGB values.

        :param r: integer from 0-255
        :param g: integer from 0-255
        :param b: integer from 0-255
        :param brightness: integer from 0-255
        :return: None
        """
        if sys.platform != 'emscripten' and not self._swarm:
            return self._set_drone_LED_desktop(r, g, b, brightness)
        else:
            return asyncio.create_task(self._set_drone_LED_emscripten(r, g, b, brightness))

    
    def _set_drone_LED_desktop(self, r, g, b, brightness):
        self.sendLightDefaultColor(LightModeDrone.BodyHold, brightness, r, g, b)
        time.sleep(0.005)

    async def _set_drone_LED_emscripten(self, r, g, b, brightness):
        await self.sendLightDefaultColor(LightModeDrone.BodyHold, brightness, r, g, b)
        await asyncio.sleep(0.005)

    def set_controller_LED(self, r, g, b, brightness):
        """
        Changes the controller LED to a specified color using RGB values.

        :param r: integer from 0-255
        :param g: integer from 0-255
        :param b: integer from 0-255
        :param brightness: integer from 0-255
        :return: None
        """
        if sys.platform != 'emscripten' and not self._swarm:
            return self._set_controller_LED_desktop(r, g, b, brightness)
        else:
            return asyncio.create_task(self._set_controller_LED_emscripten(r, g, b, brightness))

    def _set_controller_LED_desktop(self, r, g, b, brightness):
        self.sendLightDefaultColor(LightModeController.BodyHold, brightness, r, g, b)
        time.sleep(0.005)

    async def _set_controller_LED_emscripten(self, r, g, b, brightness):
        await self.sendLightDefaultColor(LightModeController.BodyHold, brightness, r, g, b)
        await asyncio.sleep(0.005)

    def drone_LED_off(self):
        """
        Turns off the drone LED.

        :return: None
        """
        if sys.platform != 'emscripten' and not self._swarm:
            return self._drone_LED_off_desktop()
        else:
            return asyncio.create_task(self._drone_LED_off_emscripten())
    
    def _drone_LED_off_desktop(self):
        self.sendLightDefaultColor(LightModeDrone.BodyHold, 0, 0, 0, 0)
        time.sleep(0.005)

    async def _drone_LED_off_emscripten(self):
        await self.sendLightDefaultColor(LightModeDrone.BodyHold, 0, 0, 0, 0)
        await asyncio.sleep(0.005)

    def controller_LED_off(self):
        """
        Turns off the controller LED.

        :return: None
        """
        if sys.platform != 'emscripten' and not self._swarm:
            return self._controller_LED_off_desktop()
        else:
            return asyncio.create_task(self._controller_LED_off_emscripten())
    
    def _controller_LED_off_desktop(self):
        self.sendLightDefaultColor(LightModeController.BodyHold, 0, 0, 0, 0)
        time.sleep(0.005)

    async def _controller_LED_off_emscripten(self):
        await self.sendLightDefaultColor(LightModeController.BodyHold, 0, 0, 0, 0)
        await asyncio.sleep(0.005)

    def sendCommandLightEvent(self, commandType, option, lightEvent, interval, repeat):
        """
        Command + LED Event
        Used to send commands to the drone.
        The option must contain either a value value of each format or a numeric value.

        :param commandType: CommandType	command type
        :param option:
        ModeControlFlight	option
        FlightEvent
        Headless
        Trim
        UInt8
        :param lightEvent: UInt8	LED operating mode
        :param interval: 0 ~ 65535	Internal brightness control function call cycle
        :param repeat: 0 ~ 255	number of repetitions
        :return: transfer()
        """

        if ((not isinstance(commandType, CommandType)) or
                (not isinstance(option, int)) or
                (not isinstance(interval, int)) or
                (not isinstance(repeat, int))):
            return None

        header = Header()

        header.dataType = DataType.Command
        header.length = CommandLightEvent.getSize()
        header.from_ = DeviceType.Base

        data = CommandLightEvent()

        if isinstance(lightEvent, LightModeDrone):
            header.to_ = DeviceType.Drone
            data.event.event = lightEvent.value

        elif isinstance(lightEvent, LightModeController):
            header.to_ = DeviceType.Controller
            data.event.event = lightEvent.value

        elif isinstance(lightEvent, int):
            header.to_ = DeviceType.Drone
            data.event.event = lightEvent

        else:
            return None

        data.command.commandType = commandType
        data.command.option = option

        data.event.interval = interval
        data.event.repeat = repeat

        return self.transfer(header, data)

    def sendCommandLightEventColor(self, commandType, option, lightEvent, interval, repeat, r, g, b):

        if ((not isinstance(commandType, CommandType)) or
                (not isinstance(option, int)) or
                (not isinstance(interval, int)) or
                (not isinstance(repeat, int)) or
                (not isinstance(r, int)) or
                (not isinstance(g, int)) or
                (not isinstance(b, int))):
            return None

        header = Header()

        header.dataType = DataType.Command
        header.length = CommandLightEventColor.getSize()
        header.from_ = DeviceType.Base

        data = CommandLightEventColor()

        if isinstance(lightEvent, LightModeDrone):
            header.to_ = DeviceType.Drone
            data.event.event = lightEvent.value

        elif isinstance(lightEvent, LightModeController):
            header.to_ = DeviceType.Controller
            data.event.event = lightEvent.value

        elif isinstance(lightEvent, int):
            header.to_ = DeviceType.Drone
            data.event.event = lightEvent

        else:
            return None

        data.command.commandType = commandType
        data.command.option = option

        data.event.interval = interval
        data.event.repeat = repeat

        data.color.r = r
        data.color.g = g
        data.color.b = b

        return self.transfer(header, data)

    def sendCommandLightEventColors(self, commandType, option, lightEvent, interval, repeat, colors):

        if ((not isinstance(commandType, CommandType)) or
                (not isinstance(option, int)) or
                (not isinstance(interval, int)) or
                (not isinstance(repeat, int)) or
                (not isinstance(colors, Colors))):
            return None

        header = Header()

        header.dataType = DataType.Command
        header.length = CommandLightEventColors.getSize()
        header.from_ = DeviceType.Base

        data = CommandLightEventColors()

        if isinstance(lightEvent, LightModeDrone):
            header.to_ = DeviceType.Drone
            data.event.event = lightEvent.value

        elif isinstance(lightEvent, LightModeController):
            header.to_ = DeviceType.Controller
            data.event.event = lightEvent.value

        elif isinstance(lightEvent, int):
            header.to_ = DeviceType.Drone
            data.event.event = lightEvent

        else:
            return None

        data.command.commandType = commandType
        data.command.option = option

        data.event.interval = interval
        data.event.repeat = repeat

        data.colors = colors

        return self.transfer(header, data)

    def sendModeControlFlight(self, modeControlFlight):

        if not isinstance(modeControlFlight, ModeControlFlight):
            return None

        header = Header()

        header.dataType = DataType.Command
        header.length = Command.getSize()
        header.from_ = DeviceType.Base
        header.to_ = DeviceType.Drone

        data = Command()

        data.commandType = CommandType.ModeControlFlight
        data.option = modeControlFlight.value

        return self.transfer(header, data)

    def sendHeadless(self, headless):

        if not isinstance(headless, Headless):
            return None

        header = Header()

        header.dataType = DataType.Command
        header.length = Command.getSize()
        header.from_ = DeviceType.Base
        header.to_ = DeviceType.Drone

        data = Command()

        data.commandType = CommandType.Headless
        data.option = headless.value

        return self.transfer(header, data)

    def reset_sensor(self):
        if sys.platform != 'emscripten':
            print(Fore.YELLOW + "Warning: The 'drone.reset_sensor()' function is deprecated and will be removed in a future release.\nPlease use 'drone.reset_gyro()'" + Style.RESET_ALL)
        else:
            print("Warning: The 'drone.reset_sensor()' function is deprecated and will be removed in a future release.\nPlease use 'drone.reset_gyro()'", color="warning")
        return self.reset_gyro()

    def reset_gyro(self):
        """
        This method will reset the gyroscope and calibrate it.

        While this program runs the drone must be on a leveled flat surface
        in order for the Gyroscope to be cleared.
        If the calibration is done while the drone is moving
        the drone will have incorrect calibration values
        resulting in incorrect gyro angle values

        :return:
        """
        # send RF command to clear gyro bias and initiate the calibration
        if sys.platform != 'emscripten' and not self._swarm:
            return self._reset_gyro_desktop()
        else:
            return asyncio.create_task(self._reset_gyro_emscripten())
    
    def _reset_gyro_desktop(self):
        # send RF command to clear the bias and initiate the calibration
        self.sendClearBias()
        time.sleep(0.2)

        #print("Lay the drone on a flat surface & Do not move CoDrone EDU")
        while True:
            self.get_error_data()
            error_flag_now = self.error_data[1]
            if (error_flag_now & ErrorFlagsForSensor.Motion_Calibrating.value) == 0:
                break

    async def _reset_gyro_emscripten(self):
        # send RF command to clear the bias and initiate the calibration
        await self.sendClearBias()
        await asyncio.sleep(0.01)

        print("Lay the drone on a flat surface & "
              "Do not move CoDrone EDU")
        await asyncio.sleep(1)
        while True:
            await self.get_error_data()
            error_flag_now = self.error_data[1]
            if (error_flag_now & ErrorFlagsForSensor.Motion_Calibrating.value) == 0:
                break
                await asyncio.sleep(0.5)
        print("Done calibrating.")

    def set_trim(self, roll, pitch):
        """
        Sets the drone trim values for roll, pitch, yaw, and throttle.

        :param roll: integer from -100-100
        :param pitch: integer from -100-100
        :return: None
        """
        if sys.platform != 'emscripten' and not self._swarm:
            return self._set_trim_desktop(roll, pitch)
        else:
            return asyncio.create_task(self._set_trim_emscripten(roll, pitch))
    
    def _set_trim_desktop(self, roll, pitch):
        roll = int(roll)
        pitch = int(pitch)
        self.sendTrim(roll, pitch, 0, 0)
        time.sleep(0.2)

    async def _set_trim_emscripten(self, roll, pitch):
        roll = int(roll)
        pitch = int(pitch)
        await self.sendTrim(roll, pitch, 0, 0)
        await asyncio.sleep(0.2)

        self.set_roll(roll)
        self.set_pitch(pitch)

    def reset_trim(self):
        """
        Resets all of the trim values to 0.

        :return: None
        """
        if sys.platform != 'emscripten' and not self._swarm:
            return self._reset_trim_desktop()
        else:
            return asyncio.create_task(self._reset_trim_emscripten())
    
    def _reset_trim_desktop(self):
        self.sendTrim(0, 0, 0, 0)
        time.sleep(0.2)

    async def _reset_trim_emscripten(self):
        await self.sendTrim(0, 0, 0, 0)
        await asyncio.sleep(0.2)

        self.set_roll(0)
        self.set_pitch(0)

    def get_trim(self):
        """
        Returns current trim values.

        :return: None
        """
        if sys.platform != 'emscripten' and not self._swarm:
            return self._get_trim_desktop()
        else:
            return asyncio.create_task(self._get_trim_emscripten())
    
    def _get_trim_desktop(self):
        trim = self.get_trim_data()[1:3]
        time.sleep(0.005)
        return trim
    
    async def _get_trim_emscripten(self):
        trim = (await self.get_trim_data())[1:3]
        await asyncio.sleep(0.005)
        return trim

    def sendTrim(self, roll, pitch, yaw, throttle):

        if ((not isinstance(roll, int)) or (not isinstance(pitch, int)) or (not isinstance(yaw, int)) or (
                not isinstance(throttle, int))):
            return None

        header = Header()

        header.dataType = DataType.Trim
        header.length = Trim.getSize()
        header.from_ = DeviceType.Base
        header.to_ = DeviceType.Drone

        data = Trim()

        data.roll = roll
        data.pitch = pitch
        data.yaw = yaw
        data.throttle = throttle

        return self.transfer(header, data)

    def sendWeight(self, weight):

        header = Header()

        header.dataType = DataType.Weight
        header.length = Weight.getSize()
        header.from_ = DeviceType.Base
        header.to_ = DeviceType.Drone

        data = Weight()

        data.weight = weight

        return self.transfer(header, data)

    def sendLostConnection(self, timeNeutral, timeLanding, timeStop):

        header = Header()

        header.dataType = DataType.LostConnection
        header.length = LostConnection.getSize()
        header.from_ = DeviceType.Base
        header.to_ = DeviceType.Drone

        data = LostConnection()

        data.timeNeutral = timeNeutral
        data.timeLanding = timeLanding
        data.timeStop = timeStop

        return self.transfer(header, data)

    def sendFlightEvent(self, flightEvent):

        if ((not isinstance(flightEvent, FlightEvent))):
            return None

        header = Header()

        header.dataType = DataType.Command
        header.length = Command.getSize()
        header.from_ = DeviceType.Base
        header.to_ = DeviceType.Drone

        data = Command()

        data.commandType = CommandType.FlightEvent
        data.option = flightEvent.value

        return self.transfer(header, data)

    def sendClearBias(self):

        header = Header()

        header.dataType = DataType.Command
        header.length = Command.getSize()
        header.from_ = DeviceType.Base
        header.to_ = DeviceType.Drone

        data = Command()

        data.commandType = CommandType.ClearBias
        data.option = 0

        return self.transfer(header, data)

    def sendClearTrim(self):

        header = Header()

        header.dataType = DataType.Command
        header.length = Command.getSize()
        header.from_ = DeviceType.Tester
        header.to_ = DeviceType.Drone

        data = Command()

        data.commandType = CommandType.ClearTrim
        data.option = 0

        return self.transfer(header, data)

    def sendSetDefault(self, deviceType):

        if ((not isinstance(deviceType, DeviceType))):
            return None

        header = Header()

        header.dataType = DataType.Command
        header.length = Command.getSize()
        header.from_ = DeviceType.Base
        header.to_ = deviceType

        data = Command()

        data.commandType = CommandType.SetDefault
        data.option = 0

        return self.transfer(header, data)

    def sendBacklight(self, flagPower):

        if ((not isinstance(flagPower, bool))):
            return None

        header = Header()

        header.dataType = DataType.Command
        header.length = Command.getSize()
        header.from_ = DeviceType.Base
        header.to_ = DeviceType.Controller

        data = Command()

        data.commandType = CommandType.Backlight
        data.option = int(flagPower)

        return self.transfer(header, data)

    def sendControlleLinkMode(self):
        header = Header()

        header.dataType = DataType.Command
        header.length = Command.getSize()
        header.from_ = DeviceType.Base
        header.to_ = DeviceType.Controller

        data = Command()

        data.commandType = CommandType.ModeController
        data.option = 0x80

        return self.transfer(header, data)

    # Setup End

    # Device Start

    def sendMotor(self, motor0, motor1, motor2, motor3):

        if ((not isinstance(motor0, int)) or
                (not isinstance(motor1, int)) or
                (not isinstance(motor2, int)) or
                (not isinstance(motor3, int))):
            return None

        header = Header()

        header.dataType = DataType.Motor
        header.length = Motor.getSize()
        header.from_ = DeviceType.Base
        header.to_ = DeviceType.Drone

        data = Motor()

        data.motor[0].value = motor0
        data.motor[1].value = motor1
        data.motor[2].value = motor2
        data.motor[3].value = motor3

        return self.transfer(header, data)
    
    def set_motor_speed(self, front_right=0, back_right=0, back_left=0, front_left=0, time_delay=0.001):
        """
        for controlling the invidual motor speeds
        0-1000 integer

        :return:
        """
        if sys.platform != 'emscripten' and not self._swarm:
            return self._set_motor_speed_desktop(front_right, back_right, back_left, front_left, time_delay)
        else:
            return asyncio.create_task(self._set_motor_speed_emscripten(front_right, back_right, back_left, front_left, time_delay))

    def _set_motor_speed_desktop(self, front_right=0, back_right=0, back_left=0, front_left=0, time_delay=0.001):
        self.sendMotor(int(front_right), int(back_right), int(back_left), int(front_left))
        sleep(time_delay)

    async def _set_motor_speed_emscripten(self, front_right=0, back_right=0, back_left=0, front_left=0, time_delay=0.001):
        await self.sendMotor(int(front_right), int(back_right), int(back_left), int(front_left))
        await asyncio.sleep(time_delay)

    def sendMotorSingle(self, target, value):

        if ((not isinstance(target, int)) or
                (not isinstance(value, int))):
            return None

        header = Header()

        header.dataType = DataType.MotorSingle
        header.length = MotorSingle.getSize()
        header.from_ = DeviceType.Base
        header.to_ = DeviceType.Drone

        data = MotorSingle()

        data.target = target
        data.value = value

        return self.transfer(header, data)

    # Device End

    # Light Start

    def sendLightManual(self, deviceType, flags, brightness):

        if ((not isinstance(deviceType, DeviceType)) or
                (not isinstance(flags, int)) or
                (not isinstance(brightness, int))):
            return None

        header = Header()

        header.dataType = DataType.LightManual
        header.length = LightManual.getSize()
        header.from_ = DeviceType.Base
        header.to_ = deviceType

        data = LightManual()

        data.flags = flags
        data.brightness = brightness

        return self.transfer(header, data)

    def sendLightModeColor(self, lightMode, interval, r, g, b):

        if ((not isinstance(lightMode, int)) or
                (not isinstance(interval, int)) or
                (not isinstance(r, int)) or
                (not isinstance(g, int)) or
                (not isinstance(b, int))):
            return None

        header = Header()

        header.dataType = DataType.LightMode
        header.length = LightModeColor.getSize()
        header.from_ = DeviceType.Base

        data = LightModeColor()

        if isinstance(lightMode, LightModeDrone):
            header.to_ = DeviceType.Drone
            data.mode.mode = lightMode.value

        elif isinstance(lightMode, LightModeController):
            header.to_ = DeviceType.Controller
            data.mode.mode = lightMode.value

        elif isinstance(lightMode, int):
            header.to_ = DeviceType.Drone
            data.mode.mode = lightMode

        else:
            return None

        data.mode.interval = interval

        data.color.r = r
        data.color.g = g
        data.color.b = b

        return self.transfer(header, data)

    def sendLightModeColors(self, lightMode, interval, colors):

        if ((not isinstance(interval, int)) or
                (not isinstance(colors, Colors))):
            return None

        header = Header()

        header.dataType = DataType.LightMode
        header.length = LightModeColors.getSize()
        header.from_ = DeviceType.Base

        data = LightModeColors()

        if isinstance(lightMode, LightModeDrone):
            header.to_ = DeviceType.Drone
            data.mode.mode = lightMode.value

        elif isinstance(lightMode, LightModeController):
            header.to_ = DeviceType.Controller
            data.mode.mode = lightMode.value

        elif isinstance(lightMode, int):
            header.to_ = DeviceType.Drone
            data.mode.mode = lightMode

        else:
            return None

        data.mode.interval = interval
        data.colors = colors

        return self.transfer(header, data)

    def sendLightEventColor(self, lightEvent, interval, repeat, r, g, b):

        if ((not isinstance(interval, int)) or
                (not isinstance(repeat, int)) or
                (not isinstance(r, int)) or
                (not isinstance(g, int)) or
                (not isinstance(b, int))):
            return None

        header = Header()

        header.dataType = DataType.LightEvent
        header.length = LightEventColor.getSize()
        header.from_ = DeviceType.Base

        data = LightEventColor()

        if isinstance(lightEvent, LightModeDrone):
            header.to_ = DeviceType.Drone
            data.event.event = lightEvent.value

        elif isinstance(lightEvent, LightModeController):
            header.to_ = DeviceType.Controller
            data.event.event = lightEvent.value

        elif isinstance(lightEvent, int):
            header.to_ = DeviceType.Drone
            data.event.event = lightEvent

        else:
            return None

        data.event.interval = interval
        data.event.repeat = repeat

        data.color.r = r
        data.color.g = g
        data.color.b = b

        return self.transfer(header, data)

    def sendLightEventColors(self, lightEvent, interval, repeat, colors):

        if ((not isinstance(interval, int)) or
                (not isinstance(repeat, int)) or
                (not isinstance(colors, Colors))):
            return None

        header = Header()

        header.dataType = DataType.LightEvent
        header.length = LightEventColors.getSize()
        header.from_ = DeviceType.Base

        data = LightEventColors()

        if isinstance(lightEvent, LightModeDrone):
            header.to_ = DeviceType.Drone
            data.event.event = lightEvent.value

        elif isinstance(lightEvent, LightModeController):
            header.to_ = DeviceType.Controller
            data.event.event = lightEvent.value

        elif isinstance(lightEvent, int):
            header.to_ = DeviceType.Drone
            data.event.event = lightEvent

        else:
            return None

        data.event.interval = interval
        data.event.repeat = repeat

        data.colors = colors

        return self.transfer(header, data)

    def sendLightDefaultColor(self, lightMode, interval, r, g, b):

        if ((not isinstance(interval, int)) or
                (not isinstance(r, int)) or
                (not isinstance(g, int)) or
                (not isinstance(b, int))):
            return None

        header = Header()

        header.dataType = DataType.LightDefault
        header.length = LightModeColor.getSize()
        header.from_ = DeviceType.Base

        data = LightModeColor()

        if isinstance(lightMode, LightModeDrone):
            header.to_ = DeviceType.Drone
            data.mode.mode = lightMode.value

        elif isinstance(lightMode, LightModeController):
            header.to_ = DeviceType.Controller
            data.mode.mode = lightMode.value

        elif isinstance(lightMode, int):
            header.to_ = DeviceType.Drone
            data.mode.mode = lightMode

        else:
            return None

        data.mode.interval = interval

        data.color.r = r
        data.color.g = g
        data.color.b = b

        return self.transfer(header, data)

    # Light End

    # Color Start

    def get_colors(self):
        """
        Access the color data using the default ByRobot
        color prediction
        Returns a list of strings
        """
        if sys.platform != 'emscripten' and not self._swarm:
            return self._get_colors_desktop()
        else:
            return asyncio.create_task(self._get_colors_emscripten())

    def _get_colors_desktop(self):
        color_data = self.get_color_data()

        try:
            front_color = color_data[9].name.lower()
            if front_color == "cyan":
                front_color = "light blue"
            elif front_color == "magenta":
                front_color = "purple"
            
        except AttributeError:
            front_color = 'Unknown'
        try:
            back_color = color_data[10].name.lower()
            if back_color == "cyan":
                back_color = "light blue"
            elif back_color == "magenta":
                back_color = "purple"

        except AttributeError:
            back_color = 'Unknown'
        colors = [front_color, back_color]
        return colors
    
    async def _get_colors_emscripten(self):
        color_data = await self.get_color_data()

        try:
            front_color = color_data[9].name.lower()
            if front_color == "cyan":
                front_color = "light blue"
            elif front_color == "magenta":
                front_color = "purple"

        except AttributeError:
            front_color = 'Unknown'
        try:
            back_color = color_data[10].name.lower()
            if back_color == "cyan":
                back_color = "light blue"
            elif back_color == "magenta":
                back_color = "purple"

        except AttributeError:
            back_color = 'Unknown'
        colors = [front_color, back_color]
        return colors

    # this functions returns a string (red, blue, magenta..)
    def get_front_color(self):
        if sys.platform != 'emscripten' and not self._swarm:
            return self._get_front_color_desktop()
        else:
            return asyncio.create_task(self._get_front_color_emscripten())

    def _get_front_color_desktop(self):
        return self.get_colors()[0]

    async def _get_front_color_emscripten(self):
        return (await self.get_colors())[0]

    def get_back_color(self):
        if sys.platform != 'emscripten' and not self._swarm:
            return self._get_back_color_desktop()
        else:
            return asyncio.create_task(self._get_back_color_emscripten())

    def _get_back_color_desktop(self):
        return self.get_colors()[1]
      
    async def _get_back_color_emscripten(self):
        return (await self.get_colors())[1]

    def detect_colors(self, color_data):
        try:
            prediction_front = self.knn.predict([color_data[1], color_data[2], color_data[3], color_data[4]])
            prediction_back = self.knn.predict([color_data[5], color_data[6], color_data[7], color_data[8]])
            prediction = [str(prediction_front), str(prediction_back)]
            return prediction
        except:
            if sys.platform != 'emscripten':
                print(Fore.RED + "Error: A classifier has not been loaded. Call drone.load_color_data() and try again." + Style.RESET_ALL)
                self.disconnect()
            else:
                print("Error: A classifier has not been loaded. Call drone.load_color_data() and try again.", color="error")
                raise Exception("A classifier has not been loaded. Call drone.load_color_data() and try again.")
            exit()

    def predict_colors(self, color_data):
        return self.detect_colors(color_data)
    
    def reset_classifier(self):
        self.knn.reset()

    def load_classifier(self, dataset=None, show_graph=False):
        if sys.platform != 'emscripten':
            print(Fore.YELLOW + "Warning: The 'drone.load_classifier()' function is deprecated and will be removed in a future release.\nPlease use 'drone.load_color_data()'." + Style.RESET_ALL)
        else:
            print("Warning: The 'drone.load_classifier()' function is deprecated and will be removed in a future release.\nPlease use 'drone.load_color_data()'", color="warning")
        return self.load_color_data(dataset, show_graph)

    def load_color_data(self, dataset=None, show_graph=False):
        # TODO Check first if all text tiles in the dataset have the same number of data points 0.6

        if dataset is None:  # path to default data inside of cde lib
            lib_dir = os.path.dirname(os.path.abspath(__file__))
            path = lib_dir + "/data/"

        else:
            path = os.path.join(self.parent_dir, dataset)  # user defined data

            if not os.path.isdir(path):
                if sys.platform != 'emscripten':
                    print(Fore.RED + "Error: Cannot load color data. Dataset \"" + dataset + "\" does not exist.")
                    print("Use new_color_data() method to add data." + Style.RESET_ALL)
                    self.disconnect()
                else:
                    print("Error: Cannot load color data. Dataset \"" + dataset + "\" does not exist.", color="error")
                    print("Use new_color_data() method to add data.", color="error")
                    raise Exception("Cannot load color data. Dataset \"" + dataset + "\" does not exist.\nUse new_color_data() method to add data.")
                exit()

            else:
                folder = os.listdir(path)

                if len(folder) == 0:
                    if sys.platform != 'emscripten':
                        print(Fore.RED + "Error: Cannot load color data. Dataset \"" + dataset + "\" is empty.")
                        print("Use the new_color_data() method to add data." + Style.RESET_ALL)
                        self.disconnect()
                    else:
                        print("Error: Cannot load color data. Dataset \"" + dataset + "\" is empty.", color="error")
                        print("Use the new_color_data() method to add data.", color="error")
                        raise Exception("Cannot load color data. Dataset \"" + dataset + "\" does not exist.\nUse new_color_data() method to add data.")
                    exit()

        all_data = []
        all_labels = []
        sample_size = None
        prev_sample_size = None
        samp_size_list = []
        sizes_different = False

        for filename in os.listdir(path):
            data = np.loadtxt(path + '/' + filename) # grab the data from the file
            all_data.append(data) # append the data to the list

            sample_size = len(data) # number of samples (lines) in the file
            samp_size_list.append([sample_size, filename])

            if prev_sample_size is None:
                prev_sample_size = sample_size

            if prev_sample_size != sample_size:
                sizes_different = True

            prev_sample_size = sample_size
            all_labels.append(filename.strip('.txt')) # append the label to the list

        if len(all_labels) < 3:
            if sys.platform != 'emscripten':
                print(Fore.RED + "Error: Dataset must have at least 3 labels to call load_color_data()." + Style.RESET_ALL)
            else:
                print("Error: Dataset must have at least 3 labels to call load_color_data().", color="error")

        if sizes_different:
            if sys.platform != 'emscripten':
                print(Fore.RED + "Error: Files do not have the same number of samples." + Style.RESET_ALL)
            else:
                print("Error: Files do not have the same number of samples.", color="error")
            for sizes in samp_size_list:
                print("samples ", sizes[0], " filename ", sizes[1])

        x = []  # Hue
        y = []  # Saturation
        z = []  # Value
        w = []  # Luminosity
        labels_list = []

        for color in range(len(all_labels)): # for each color index, ex. for "red" color = 0

            for i in range(samp_size_list[color][0]):   # iterate the number of samples per label
                labels_list.append(all_labels[color])
                # use data from both sensors front
                x.append(all_data[color][i][1])  # Hue
                y.append(all_data[color][i][2])  # Saturation
                z.append(all_data[color][i][3])  # Value
                w.append(all_data[color][i][4])  # Luminosity

        x_data = []
        for i in range(len(x)):
            x_data.append([x[i], y[i], z[i], w[i]])
        y_data = labels_list
        self.knn.fit(x_data, y_data)

        if show_graph:
            from mpl_toolkits import mplot3d
            import matplotlib.pyplot as plt
            fig = plt.figure()
            ax = fig.add_subplot(projection='3d')
            ax.scatter3D(x, y, z, c=z)
            plt.show()
        print("Successfully loaded \"" + dataset + "\" dataset.")
        return all_data

    def print_num_data(self, label, dataset):
        folder = dataset
        parent_dir = os.getcwd() if sys.platform != 'emscripten' else '/home/web_user/data/'
        path = os.path.join(parent_dir, folder)
        filename = path + '/' + label + '.txt'
        file_exists = os.path.exists(filename)

        if not file_exists:
            if sys.platform != 'emscripten':
                print(Fore.RED + "Error: Cannot count data. Folder and file do not exist. Use new_color_data()." + Style.RESET_ALL)
            else:
                print("Error: Cannot count data. Folder and file do not exist. Use new_color_data().", color="error")
            return

        data = np.loadtxt(filename)
        return len(data)

    def append_color_data(self, label, data, dataset):

        """
          This function will append data to an already existing label in a dataset.
          If the file doesn't exist, then it will print an error.

          :param label: String label name that will be used for the filename
          :param data: List of HSV data samples
          :param dataset: String folder name where the text file will be stored.
          :return: None
          """
        folder = dataset
        parent_dir = os.getcwd() if sys.platform != 'emscripten' else '/home/web_user/data/'
        path = os.path.join(parent_dir, folder)
        filename = path + '/' + label + '.txt'
        file_exists = os.path.exists(filename)

        if not os.path.isdir(path) or not file_exists:
            if sys.platform != 'emscripten':
                print(Fore.RED + "Error: Cannot append data. Folder and file do not exist. Use new_color_data()." + Style.RESET_ALL)
            else:
                print("Error: Cannot append data. Folder and file do not exist. Use new_color_data().", color="error")
            return

        print("Appending data to " + label + "...")

        new_data = data  # new data we want to add
        con_data = np.array(new_data)  # convert it first to np array
        old_data = np.loadtxt(filename)  # load existing data
        all_data = np.concatenate((old_data, con_data))  # add the data
        np.savetxt(filename, all_data)  # save the new combined data

    def new_color_data(self, label, data, dataset):        
        """
        This function creates a new textfile label.txt in a dataset folder.

        :param label: String label name that will be used for the filename
        :param data: List of HSV data samples
        :param dataset: String folder name where the text file will be stored.
        :return: None
        """
        folder = dataset
        parent_dir = os.getcwd() if sys.platform != 'emscripten' else '/home/web_user/data/'
        path = os.path.join(parent_dir, folder)

        if not os.path.isdir(path):
            # print("Creating new dataset.")
            os.makedirs(path)
        print("Adding " + label + " to", dataset)
        filename = label + ".txt"
        np.savetxt(path + '/' + filename, data)

    # Color End

    # Display Start

    def sendDisplayClearAll(self, pixel=DisplayPixel.White):

        if (not isinstance(pixel, DisplayPixel)):
            return None

        header = Header()

        header.dataType = DataType.DisplayClear
        header.length = DisplayClearAll.getSize()
        header.from_ = DeviceType.Base
        header.to_ = DeviceType.Controller

        data = DisplayClearAll()

        data.pixel = pixel

        return self.transfer(header, data)

    def sendDisplayClear(self, x, y, width, height, pixel=DisplayPixel.White):

        if (not isinstance(pixel, DisplayPixel)):
            return None

        header = Header()

        header.dataType = DataType.DisplayClear
        header.length = DisplayClear.getSize()
        header.from_ = DeviceType.Base
        header.to_ = DeviceType.Controller

        data = DisplayClear()

        data.x = x
        data.y = y
        data.width = width
        data.height = height
        data.pixel = pixel

        return self.transfer(header, data)

    def sendDisplayInvert(self, x, y, width, height):

        header = Header()

        header.dataType = DataType.DisplayInvert
        header.length = DisplayInvert.getSize()
        header.from_ = DeviceType.Base
        header.to_ = DeviceType.Controller

        data = DisplayInvert()

        data.x = x
        data.y = y
        data.width = width
        data.height = height

        return self.transfer(header, data)

    def sendDisplayDrawPoint(self, x, y, pixel=DisplayPixel.Black):

        if (not isinstance(pixel, DisplayPixel)):
            return None

        header = Header()

        header.dataType = DataType.DisplayDrawPoint
        header.length = DisplayDrawPoint.getSize()
        header.from_ = DeviceType.Base
        header.to_ = DeviceType.Controller

        data = DisplayDrawPoint()

        data.x = x
        data.y = y
        data.pixel = pixel

        return self.transfer(header, data)

    def sendDisplayDrawLine(self, x1, y1, x2, y2, pixel=DisplayPixel.Black, line=DisplayLine.Solid):

        if ((not isinstance(pixel, DisplayPixel)) or (not isinstance(line, DisplayLine))):
            return None

        header = Header()

        header.dataType = DataType.DisplayDrawLine
        header.length = DisplayDrawLine.getSize()
        header.from_ = DeviceType.Base
        header.to_ = DeviceType.Controller

        data = DisplayDrawLine()

        data.x1 = x1
        data.y1 = y1
        data.x2 = x2
        data.y2 = y2
        data.pixel = pixel
        data.line = line

        return self.transfer(header, data)

    def sendDisplayDrawRect(self, x, y, width, height, pixel=DisplayPixel.Black, flagFill=False,
                            line=DisplayLine.Solid):

        if ((not isinstance(pixel, DisplayPixel)) or (not isinstance(flagFill, bool)) or (
                not isinstance(line, DisplayLine))):
            return None

        header = Header()

        header.dataType = DataType.DisplayDrawRect
        header.length = DisplayDrawRect.getSize()
        header.from_ = DeviceType.Base
        header.to_ = DeviceType.Controller

        data = DisplayDrawRect()

        data.x = x
        data.y = y
        data.width = width
        data.height = height
        data.pixel = pixel
        data.flagFill = flagFill
        data.line = line

        return self.transfer(header, data)

    def sendDisplayDrawCircle(self, x, y, radius, pixel=DisplayPixel.Black, flagFill=True):

        if ((not isinstance(pixel, DisplayPixel)) or (not isinstance(flagFill, bool))):
            return None

        header = Header()

        header.dataType = DataType.DisplayDrawCircle
        header.length = DisplayDrawCircle.getSize()
        header.from_ = DeviceType.Base
        header.to_ = DeviceType.Controller

        data = DisplayDrawCircle()

        data.x = x
        data.y = y
        data.radius = radius
        data.pixel = pixel
        data.flagFill = flagFill

        return self.transfer(header, data)

    def sendDisplayDrawString(self, x, y, message, font=DisplayFont.LiberationMono5x8, pixel=DisplayPixel.Black):

        if ((not isinstance(font, DisplayFont)) or (not isinstance(pixel, DisplayPixel)) or (
                not isinstance(message, str))):
            return None

        header = Header()

        header.dataType = DataType.DisplayDrawString
        header.length = DisplayDrawString.getSize() + len(message)
        header.from_ = DeviceType.Base
        header.to_ = DeviceType.Controller

        data = DisplayDrawString()

        data.x = x
        data.y = y
        data.font = font
        data.pixel = pixel
        data.message = message

        return self.transfer(header, data)

    def sendDisplayDrawStringAlign(self, x_start, x_end, y, message, align=DisplayAlign.Center,
                                   font=DisplayFont.LiberationMono5x8, pixel=DisplayPixel.Black):

        if ((not isinstance(align, DisplayAlign)) or (not isinstance(font, DisplayFont)) or (
                not isinstance(pixel, DisplayPixel)) or (not isinstance(message, str))):
            return None

        header = Header()

        header.dataType = DataType.DisplayDrawStringAlign
        header.length = DisplayDrawStringAlign.getSize() + len(message)
        header.from_ = DeviceType.Base
        header.to_ = DeviceType.Controller

        data = DisplayDrawStringAlign()

        data.x_start = x_start
        data.x_end = x_end
        data.y = y
        data.align = align
        data.font = font
        data.pixel = pixel
        data.message = message

        return self.transfer(header, data)

    def controller_create_canvas(self, color="white"):
        """
        Creates a clean canvas for drawing and creates/resets preview canvas
        :param color: the pixel color of the canvas
        :return: image object
        """
        if sys.platform != 'emscripten':
            return self._controller_create_canvas_desktop(color)
        else:
            return asyncio.create_task(self._controller_create_canvas_emscripten(color))
        
    def _controller_create_canvas_desktop(self, color="white"):
        if color == "white":
            self._canvas = PIL.Image.new("RGB", (127, 63), color=color)
            image = PIL.Image.new("RGB", (127, 63), color=color)
        elif color == "black":
            self._canvas = PIL.Image.new("RGB", (127, 63), color=color)
            image = PIL.Image.new("RGB", (127, 63), color=color)
        else:
            raise Exception("Invalid color. Color value must be 'white' or 'black'")
        return image
    
    async def _controller_create_canvas_emscripten(self, color="white"):
        if (await self.get_information_data())[0] == ModelNumber.Drone_12_Drone_P1:
            warnings.warn(
                "This function is not currently supported for CoDrone EDU (JROTC ed.).",
                RuntimeWarning,
                stacklevel=2
            )
            return
        
        if color == "white":
            self._canvas = PIL.Image.new("RGB", (127, 63), color=color)
            image = PIL.Image.new("RGB", (127, 63), color=color)
        elif color == "black":
            self._canvas = PIL.Image.new("RGB", (127, 63), color=color)
            image = PIL.Image.new("RGB", (127, 63), color=color)
        else:
            raise Exception("Invalid color. Color value must be 'white' or 'black'")
        return image


    def controller_preview_canvas(self):
        """
        Pops up a window of the current canvas
        :return: nothing
        """
        if sys.platform == 'emscripten':
            warnings.warn(
                "This method is not supported on Python for Robolink.",
                RuntimeWarning,
                stacklevel=2
            )
            return
        #image.show()
        self._canvas.show()

    def get_image_data(self, image_file_name):
        """
        gets image data when given image file name
        :param image_file_name: the image file name
        :return: list of data resized to fit on controller screen
        """
        if sys.platform == 'emscripten':
            warnings.warn(
                "This method is not supported on Python for Robolink.",
                RuntimeWarning,
                stacklevel=2
            )
            return
        img = PIL.Image.open(image_file_name)
        controller_size = (127, 63)
        img = img.resize(controller_size)
        return list(img.getdata())

    def controller_draw_canvas(self, image):
        """
        Draws custom image canvas onto the controller screen
        :param image: image to be drawn
        :return: nothing
        """
        if not isinstance(image, PIL.Image.Image):
            if sys.platform != 'emscripten':
                raise Exception("Unable to draw image canvas. Use controller_create_canvas() to create a canvas.")
            else:
                print("Error: Unable to draw image canvas. Use controller_create_canvas() to create a canvas.",
                      color="error")
                raise Exception("Unable to draw image canvas. Use controller_create_canvas() to create a canvas.")

        if sys.platform != 'emscripten':
            return self._controller_draw_canvas_desktop(image)
        else:
            return asyncio.create_task(self._controller_draw_canvas_emscripten(image))

    def _controller_draw_canvas_desktop(self, image):
        img = list(image.getdata())
        self.controller_draw_image(img)
        
    async def _controller_draw_canvas_emscripten(self, image):
        img = list(image.getdata())
        await self.controller_draw_image(img)

    def controller_draw_line(self, x1, y1, x2, y2, image, color="black", pixel_width=1):
        """
        (x1,y1) \
                 \
                  \
                   (x2,y2)
        draws a line between points (x1, y1) and (x2, y2)
        :param x1: point 1 x coordinate
        :param y1: point 1 y coordinate
        :param x2: point 2 x coordinate
        :param y2: point 2 y coordinate
        :param image: image object where line will be drawn on
        :param color: color of line
        :param pixel_width: width of pixel line
        :return: nothing
        """
        if not isinstance(image, PIL.Image.Image):
            if sys.platform != 'emscripten':
                raise Exception("Unable to draw line on image canvas. Use controller_create_canvas() to create a canvas.")
            else:
                print("Error: Unable to draw line on image canvas. Use controller_create_canvas() to create a canvas.",color="error")
                raise Exception("Unable to draw line on image canvas. Use controller_create_canvas() to create a canvas.")

        if sys.platform != 'emscripten':
            return self._controller_draw_line_desktop(x1, y1, x2, y2, image, color, pixel_width)
        else:
            return asyncio.create_task(self._controller_draw_line_emscripten(x1, y1, x2, y2, image, color, pixel_width))
          
    def _controller_draw_line_desktop(self, x1, y1, x2, y2, image, color, pixel_width):
        draw = PIL.ImageDraw.Draw(image)
        preview_draw = PIL.ImageDraw.Draw(self._canvas)
        if color == "black" or color=="white":
            draw.line([(x1, int(y1 * 0.80)), (x2, int(y2 * 0.80))], fill=color, width=pixel_width)
            preview_draw.line([(x1, y1), (x2, y2)], fill=color, width=pixel_width)
        else:
            raise Exception("Invalid color. Color value must be 'white' or 'black'")
            
    async def _controller_draw_line_emscripten(self, x1, y1, x2, y2, image, color, pixel_width):
        if (await self.get_information_data())[0] == ModelNumber.Drone_12_Drone_P1:
            warnings.warn(
                "This function is not currently supported for CoDrone EDU (JROTC ed.).",
                RuntimeWarning,
                stacklevel=2
            )
            return
            
        draw = PIL.ImageDraw.Draw(image)
        preview_draw = PIL.ImageDraw.Draw(self._canvas)
        if color == "black" or color=="white":
            draw.line([(x1, int(y1 * 0.80)), (x2, int(y2 * 0.80))], fill=color, width=pixel_width)
            preview_draw.line([(x1, y1), (x2, y2)], fill=color, width=pixel_width)
        else:
            raise Exception("Invalid color. Color value must be 'white' or 'black'")

    def controller_draw_rectangle(self, x, y, width, height, image, color="black", fill_in=None, pixel_width=1):

        """
                   width
        (x,y)|---------------|
             |               | height
             |_______________|

        draws a rectangle onto the controller screen starting from point (x,y) and extends to
        given height and width
        :param x: top left corner x coordinate
        :param y: top left corner y coordinate
        :param width: width of rectangle
        :param height: height of rectangle
        :param image: image object where rectangle will be drawn on
        :param color: color of rectangle. By default, color is black
        :param fill_in: color of fill. By default, no fill in
        :param pixel_width: width of pixel outline.
        :return: nothing
        """
        if not isinstance(image, PIL.Image.Image):
            if sys.platform != 'emscripten':
                raise Exception("Unable to draw rectangle on image canvas. Use controller_create_canvas() to create a canvas.")
            else:
                print("Error: Unable to draw rectangle on image canvas. Use controller_create_canvas() to create a canvas.",color="error")
                raise Exception("Unable to draw rectangle on image canvas. Use controller_create_canvas() to create a canvas.")

        if sys.platform != 'emscripten':
            return self._controller_draw_rectangle_desktop(x, y, width, height, image, color, fill_in, pixel_width)
        else:
            return asyncio.create_task(self._controller_draw_rectangle_emscripten(x, y, width, height, image, color, fill_in, pixel_width))
        
    def _controller_draw_rectangle_desktop(self, x, y, width, height, image, color, fill_in, pixel_width):
        draw = PIL.ImageDraw.Draw(image)
        preview_draw = PIL.ImageDraw.Draw(self._canvas)
        if (color == "black" or color == "white") and (fill_in == "black" or fill_in == "white" or fill_in is None):
            draw.rectangle([x, int(y * 0.8), x + width, int((y + height) * 0.8)], fill=fill_in, width=pixel_width, outline=color)
            preview_draw.rectangle([x, y, x + width, y + height], fill=fill_in, width=pixel_width, outline=color)

        else:
            raise Exception("Invalid color. Color value must be 'white' or 'black'")

    async def _controller_draw_rectangle_emscripten(self, x, y, width, height, image, color, fill_in, pixel_width):
        if (await self.get_information_data())[0] == ModelNumber.Drone_12_Drone_P1:
            warnings.warn(
                "This function is not currently supported for CoDrone EDU (JROTC ed.).",
                RuntimeWarning,
                stacklevel=2
            )
            return
        
        draw = PIL.ImageDraw.Draw(image)
        preview_draw = PIL.ImageDraw.Draw(self._canvas)
        if (color == "black" or color == "white") and (fill_in == "black" or fill_in == "white" or fill_in is None):
            draw.rectangle([x, int(y * 0.8), x + width, int((y + height) * 0.8)], fill=fill_in, width=pixel_width, outline=color)
            preview_draw.rectangle([x, y, x + width, y + height], fill=fill_in, width=pixel_width, outline=color)

        else:
            raise Exception("Invalid color. Color value must be 'white' or 'black'")

    def controller_draw_square(self, x, y, width, image, color="black", fill_in=None, pixel_width=1):
        """
               width
        (x,y)|-------|
             |       | width
             |_______|

        draws a square onto the controller screen starting from point (x,y) and extends to
        given width
        :param x: top left corner x coordinate
        :param y: top left corner y coordinate
        :param width: width of square
        :param image: image object where square will be drawn on
        :param color: color of square. By default, color is black
        :param fill_in: color of fill. By default, no fill in
        :param pixel_width: width of pixel outline.
        :return: nothing
        """
        if not isinstance(image, PIL.Image.Image):
            if sys.platform != 'emscripten':
                raise Exception("Unable to draw square on image canvas. Use controller_create_canvas() to create a canvas.")
            else:
                print("Error: Unable to draw square on image canvas. Use controller_create_canvas() to create a canvas.",color="error")
                raise Exception("Unable to draw square on image canvas. Use controller_create_canvas() to create a canvas.")

        if sys.platform != 'emscripten':
            return self._controller_draw_square_desktop(x, y, width, image, color, fill_in, pixel_width)
        else:
            return asyncio.create_task(self._controller_draw_square_emscripten(x, y, width, image, color, fill_in, pixel_width))        

    def _controller_draw_square_desktop(self, x, y, width, image, color, fill_in, pixel_width):
        draw = PIL.ImageDraw.Draw(image)
        preview_draw = PIL.ImageDraw.Draw(self._canvas)
        if (color == "black" or color == "white") and (fill_in == "black" or fill_in == "white" or fill_in is None):
            draw.rectangle([x, int(y * 0.8), x + width, int((y + width) * 0.8)], fill=fill_in, width=pixel_width,
                           outline=color)
            preview_draw.rectangle([x, y, x + width, y + width], fill=fill_in, width=pixel_width, outline=color)

        else:
            raise Exception("Invalid color. Color value must be 'white' or 'black'")

    async def _controller_draw_square_emscripten(self, x, y, width, image, color, fill_in, pixel_width):
        if (await self.get_information_data())[0] == ModelNumber.Drone_12_Drone_P1:
            warnings.warn(
                "This function is not currently supported for CoDrone EDU (JROTC ed.).",
                RuntimeWarning,
                stacklevel=2
            )
            return
        
        draw = PIL.ImageDraw.Draw(image)
        preview_draw = PIL.ImageDraw.Draw(self._canvas)
        if (color == "black" or color == "white") and (fill_in == "black" or fill_in == "white" or fill_in is None):
            draw.rectangle([x, int(y * 0.8), x + width, int((y + width) * 0.8)], fill=fill_in, width=pixel_width,
                           outline=color)
            preview_draw.rectangle([x, y, x + width, y + width], fill=fill_in, width=pixel_width, outline=color)

        else:
            raise Exception("Invalid color. Color value must be 'white' or 'black'")

    def controller_draw_point(self, x, y, image, color="black"):
        """
        draws a single pixel at the point (x,y)
        :param x: x coordinate
        :param y: y coordinate
        :param image: image object where point will be drawn on
        :param color: color of point. By default, color is black
        :return: nothing
        """
        if not isinstance(image, PIL.Image.Image):
            if sys.platform != 'emscripten':
                raise Exception("Unable to draw point on image canvas. Use controller_create_canvas() to create a canvas.")
            else:
                print("Error: Unable to draw point on image canvas. Use controller_create_canvas() to create a canvas.",color="error")
                raise Exception("Unable to draw point on image canvas. Use controller_create_canvas() to create a canvas.")

        if sys.platform != 'emscripten':
            return self._controller_draw_point_desktop(x, y, image, color)
        else:
            return asyncio.create_task(self._controller_draw_point_emscripten(x, y, image, color))

    def _controller_draw_point_desktop(self, x, y, image, color):
        draw = PIL.ImageDraw.Draw(image)
        preview_draw = PIL.ImageDraw.Draw(self._canvas)
        if color == "black" or color == "white":
            draw.point([x, int(y * 0.8)], fill=color)
            preview_draw.point([x, y], fill=color)
        else:
            raise Exception("Invalid color. Color value must be 'white' or 'black'")

    async def _controller_draw_point_emscripten(self, x, y, image, color):
        if (await self.get_information_data())[0] == ModelNumber.Drone_12_Drone_P1:
            warnings.warn(
                "This function is not currently supported for CoDrone EDU (JROTC ed.).",
                RuntimeWarning,
                stacklevel=2
            )
            return
        
        draw = PIL.ImageDraw.Draw(image)
        preview_draw = PIL.ImageDraw.Draw(self._canvas)
        if color == "black" or color == "white":
            draw.point([x, int(y * 0.8)], fill=color)
            preview_draw.point([x, y], fill=color)
        else:
            raise Exception("Invalid color. Color value must be 'white' or 'black'")

    def controller_clear_screen(self, pixel=DisplayPixel.White):
        """
        clears all drawings from the controller screen
        :param pixel: make all pixels white or black. white is default.
        :return: nothing
        """

        if sys.platform != 'emscripten':
            return self._controller_clear_screen_desktop(pixel)
        else:
            return asyncio.create_task(self._controller_clear_screen_emscripten(pixel))

    def _controller_clear_screen_desktop(self, pixel=DisplayPixel.White):
        self.sendDisplayClearAll(pixel)

    async def _controller_clear_screen_emscripten(self, pixel=DisplayPixel.White):
        if (await self.get_information_data())[0] == ModelNumber.Drone_12_Drone_P1:
            warnings.warn(
                "This function is not currently supported for CoDrone EDU (JROTC ed.).",
                RuntimeWarning,
                stacklevel=2
            )
            return
        
        await self.sendDisplayClearAll(pixel)

    def controller_draw_polygon(self, point_list, image, color="black", fill_in=None, pixel_width=1):
        """
        The polygon outline consists of straight lines between the
        given coordinates, plus a straight line between the last and the first coordinate.
        :param point_list: the list of coordinates
        :param image: image object where polygon will be drawn on
        :param color: color of polygon. By default, color is black
        :param fill_in: color of fill. By default, no fill in
        :param pixel_width: width of pixel outline.
        :return: nothing
        """
        if not isinstance(image, PIL.Image.Image):
            if sys.platform != 'emscripten':
                raise Exception("Unable to draw polygon on image canvas. Use controller_create_canvas() to create a canvas.")
            else:
                print("Error: Unable to draw polygon on image canvas. Use controller_create_canvas() to create a canvas.",color="error")
                raise Exception("Unable to draw polygon on image canvas. Use controller_create_canvas() to create a canvas.")

        if sys.platform != 'emscripten':
            return self._controller_draw_polygon_desktop(point_list, image, color, fill_in, pixel_width)
        else:
            return asyncio.create_task(self._controller_draw_polygon_emscripten(point_list, image, color, fill_in, pixel_width))
        
    def _controller_draw_polygon_desktop(self, point_list, image, color, fill_in, pixel_width):
        if isinstance(point_list, list):
            new_point_list = [[*point] for point in point_list]

            for i in range(len(new_point_list)):
                new_point_list[i][1] = int(new_point_list[i][1]*0.8)
                point = tuple(new_point_list[i])
                new_point_list[i] = point

            draw = PIL.ImageDraw.Draw(image)
            preview_draw = PIL.ImageDraw.Draw(self._canvas)
            if (color == "black" or color == "white") and (fill_in == "black" or fill_in == "white" or fill_in is None):
                draw.polygon(new_point_list, fill=fill_in, width=pixel_width, outline=color)
                preview_draw.polygon(point_list, fill=fill_in, width=pixel_width, outline=color)

            else:
                raise Exception("Invalid color. Color value must be 'white' or 'black'")
        else:
            raise Exception(f"Error: Could not draw the list: {point_list}.\nUse a list in the format: list [ (x1,y1), (x2, y2),..., (xn, yn) ]")


    async def _controller_draw_polygon_emscripten(self, point_list, image, color, fill_in, pixel_width):
        if (await self.get_information_data())[0] == ModelNumber.Drone_12_Drone_P1:
            warnings.warn(
                "This function is not currently supported for CoDrone EDU (JROTC ed.).",
                RuntimeWarning,
                stacklevel=2
            )
            return
        
        if isinstance(point_list, list):
            new_point_list = [[*point] for point in point_list]

            for i in range(len(new_point_list)):
                new_point_list[i][1] = int(new_point_list[i][1]*0.8)
                point = tuple(new_point_list[i])
                new_point_list[i] = point

            draw = PIL.ImageDraw.Draw(image)
            preview_draw = PIL.ImageDraw.Draw(self._canvas)
            if (color == "black" or color == "white") and (fill_in == "black" or fill_in == "white" or fill_in is None):
                draw.polygon(new_point_list, fill=fill_in, width=pixel_width, outline=color)
                preview_draw.polygon(point_list, fill=fill_in, width=pixel_width, outline=color)

            else:
                raise Exception("Invalid color. Color value must be 'white' or 'black'")
        else:
            raise Exception(f"Error: Could not draw the list: {point_list}.\nUse a list in the format: list [ (x1,y1), (x2, y2),..., (xn, yn) ]")

    def controller_draw_ellipse(self, ellipse_list, image, color="black", fill_in=None, pixel_width=1):
        """
        Draws an ellipse inside the given bounding box.
        :param ellipse_list: Two points to define the bounding box. Sequence of [(x0, y0), (x1, y1)]
                             where x1 >= x0 and y1 >= y0.
        :param image: image object where ellipse will be drawn on
        :param color: color of ellipse. By default, color is black
        :param fill_in: color of fill. By default, no fill in
        :param pixel_width: width of pixel outline.
        :return: nothing
        """
        print(not isinstance(image, PIL.Image.Image))
        if not isinstance(image, PIL.Image.Image):
            if sys.platform != 'emscripten':
                raise Exception("Unable to draw ellipse on image canvas. Use controller_create_canvas() to create a canvas.")
            else:
                print("Error: Unable to draw ellipse on image canvas. Use controller_create_canvas() to create a canvas.",color="error")
                raise Exception("Unable to draw ellipse on image canvas. Use controller_create_canvas() to create a canvas.")
        if sys.platform != 'emscripten':
            return self._controller_draw_ellipse_desktop(ellipse_list, image, color, fill_in, pixel_width)
        else:
            return asyncio.create_task(self._controller_draw_ellipse_emscripten(ellipse_list, image, color, fill_in, pixel_width))

    def _controller_draw_ellipse_desktop(self, ellipse_list, image, color, fill_in=None, pixel_width=1):
        new_ellipse_list = [[*point] for point in ellipse_list]

        for i in range(len(new_ellipse_list)):
            new_ellipse_list[i][1] = int(new_ellipse_list[i][1] * 0.8)
            point = tuple(new_ellipse_list[i])
            new_ellipse_list[i] = point

        draw = PIL.ImageDraw.Draw(image)
        preview_draw = PIL.ImageDraw.Draw(self._canvas)
        if (color == "black" or color == "white") and (fill_in == "black" or fill_in == "white" or fill_in is None):
            draw.ellipse(new_ellipse_list, fill=fill_in, width=pixel_width, outline=color)
            preview_draw.ellipse(ellipse_list, fill=fill_in, width=pixel_width, outline=color)

        else:
            raise Exception("Invalid color. Color value must be 'white' or 'black'")

    async def _controller_draw_ellipse_emscripten(self, ellipse_list, image, color, fill_in=None, pixel_width=1):
        if (await self.get_information_data())[0] == ModelNumber.Drone_12_Drone_P1:
            warnings.warn(
                "This function is not currently supported for CoDrone EDU (JROTC ed.).",
                RuntimeWarning,
                stacklevel=2
            )
            return
          
        new_ellipse_list = [[*point] for point in ellipse_list]

        for i in range(len(new_ellipse_list)):
            new_ellipse_list[i][1] = int(new_ellipse_list[i][1] * 0.8)
            point = tuple(new_ellipse_list[i])
            new_ellipse_list[i] = point

        draw = PIL.ImageDraw.Draw(image)
        preview_draw = PIL.ImageDraw.Draw(self._canvas)
        if (color == "black" or color == "white") and (fill_in == "black" or fill_in == "white" or fill_in is None):
            draw.ellipse(new_ellipse_list, fill=fill_in, width=pixel_width, outline=color)
            preview_draw.ellipse(ellipse_list, fill=fill_in, width=pixel_width, outline=color)

        else:
            raise Exception("Invalid color. Color value must be 'white' or 'black'")

    def controller_draw_arc(self, arc_list, start_angle, end_angle, image, color="black", pixel_width=1):
        """
        Draws an arc (a portion of a circle outline) between the start and end angles, inside the given bounding box.
        :param arc_list: Two points to define the bounding box. Sequence of [(x0, y0), (x1, y1)], where x1 >= x0
        and y1 >= y0.
        :param start_angle: Starting angle, in degrees. Angles are measured from 3 o’clock, increasing clockwise.
        :param end_angle: Ending angle, in degrees.
        :param image: image object where arc will be drawn on
        :param color: color of arc. By default, color is black
        :param pixel_width: width of pixel outline
        :return: nothing
        """
        if not isinstance(image, PIL.Image.Image):
            if sys.platform != 'emscripten':
                raise Exception("Unable to draw arc on image canvas. Use controller_create_canvas() to create a canvas.")
            else:
                print("Error: Unable to draw arc on image canvas. Use controller_create_canvas() to create a canvas.",color="error")
                raise Exception("Unable to draw arc on image canvas. Use controller_create_canvas() to create a canvas.")

        if sys.platform != 'emscripten':
            return self._controller_draw_arc_desktop(arc_list, start_angle, end_angle, image, color, pixel_width)
        else:
            return asyncio.create_task(self._controller_draw_arc_emscripten(arc_list, start_angle, end_angle, image, color, pixel_width))

    def _controller_draw_arc_desktop(self, arc_list, start_angle, end_angle, image, color, pixel_width):
        new_arc_list = [[*point] for point in arc_list]

        for i in range(len(new_arc_list)):
            new_arc_list[i][1] = int(new_arc_list[i][1] * 0.8)
            point = tuple(new_arc_list[i])
            new_arc_list[i] = point

        draw = PIL.ImageDraw.Draw(image)
        preview_draw = PIL.ImageDraw.Draw(self._canvas)
        if color == "black" or color == "white":
            draw.arc(new_arc_list, start_angle, end_angle, fill=color, width=pixel_width)
            preview_draw.arc(arc_list, start_angle, end_angle, fill=color, width=pixel_width)

        else:
            raise Exception("Invalid color. Color value must be 'white' or 'black'")
            
    async def _controller_draw_arc_emscripten(self, arc_list, start_angle, end_angle, image, color, pixel_width):
        if (await self.get_information_data())[0] == ModelNumber.Drone_12_Drone_P1:
            warnings.warn(
                "This function is not currently supported for CoDrone EDU (JROTC ed.).",
                RuntimeWarning,
                stacklevel=2
            )
            return
          
        new_arc_list = [[*point] for point in arc_list]

        for i in range(len(new_arc_list)):
            new_arc_list[i][1] = int(new_arc_list[i][1] * 0.8)
            point = tuple(new_arc_list[i])
            new_arc_list[i] = point

        draw = PIL.ImageDraw.Draw(image)
        preview_draw = PIL.ImageDraw.Draw(self._canvas)
        if color == "black" or color == "white":
            draw.arc(new_arc_list, start_angle, end_angle, fill=color, width=pixel_width)
            preview_draw.arc(arc_list, start_angle, end_angle, fill=color, width=pixel_width)

        else:
            raise Exception("Invalid color. Color value must be 'white' or 'black'")

    def controller_draw_chord(self, chord_list, start_angle, end_angle, image, color="black", fill_in=None, pixel_width=1):
        """
        Same as controller_draw_arc(), but connects the end points with a straight line.
        :param chord_list: Two points to define the bounding box. Sequence of [(x0, y0), (x1, y1)], where x1 >= x0
        and y1 >= y0.
        :param start_angle: Starting angle, in degrees. Angles are measured from 3 o’clock, increasing clockwise.
        :param end_angle: Ending angle, in degrees.
        :param image: image object where chord will be drawn on
        :param color: color of chord. By default, color is black
        :param fill_in: color of fill. By default, no fill in
        :param pixel_width: width of pixel outline.
        :return: nothing
        """
        if not isinstance(image, PIL.Image.Image):
            if sys.platform != 'emscripten':
                raise Exception("Unable to draw chord on image canvas. Use controller_create_canvas() to create a canvas.")
            else:
                print("Error: Unable to draw chord on image canvas. Use controller_create_canvas() to create a canvas.",color="error")
                raise Exception("Unable to draw chord on image canvas. Use controller_create_canvas() to create a canvas.")

        if sys.platform != 'emscripten':
            return self._controller_draw_chord_desktop(chord_list, start_angle, end_angle, image, color, fill_in, pixel_width)
        else:
            return asyncio.create_task(self._controller_draw_chord_emscripten(chord_list, start_angle, end_angle, image, color, fill_in, pixel_width))

    def _controller_draw_chord_desktop(self, chord_list, start_angle, end_angle, image, color, fill_in, pixel_width):
        new_chord_list = [[*point] for point in chord_list]

        for i in range(len(new_chord_list)):
            new_chord_list[i][1] = int(new_chord_list[i][1] * 0.8)
            point = tuple(new_chord_list[i])
            new_chord_list[i] = point

        draw = PIL.ImageDraw.Draw(image)
        preview_draw = PIL.ImageDraw.Draw(self._canvas)
        if (color == "black" or color == "white") and (fill_in == "black" or fill_in == "white" or fill_in is None):
            draw.chord(new_chord_list, start_angle, end_angle, fill=fill_in, width=pixel_width, outline=color)
            preview_draw.chord(chord_list, start_angle, end_angle, fill=fill_in, width=pixel_width, outline=color)

        else:
            raise Exception("Invalid color. Color value must be 'white' or 'black'")

    async def _controller_draw_chord_emscripten(self, chord_list, start_angle, end_angle, image, color, fill_in, pixel_width):
        if (await self.get_information_data())[0] == ModelNumber.Drone_12_Drone_P1:
            warnings.warn(
                "This function is not currently supported for CoDrone EDU (JROTC ed.).",
                RuntimeWarning,
                stacklevel=2
            )
            return
          
        new_chord_list = [[*point] for point in chord_list]

        for i in range(len(new_chord_list)):
            new_chord_list[i][1] = int(new_chord_list[i][1] * 0.8)
            point = tuple(new_chord_list[i])
            new_chord_list[i] = point

        draw = PIL.ImageDraw.Draw(image)
        preview_draw = PIL.ImageDraw.Draw(self._canvas)
        if (color == "black" or color == "white") and (fill_in == "black" or fill_in == "white" or fill_in is None):
            draw.chord(new_chord_list, start_angle, end_angle, fill=fill_in, width=pixel_width, outline=color)
            preview_draw.chord(chord_list, start_angle, end_angle, fill=fill_in, width=pixel_width, outline=color)

        else:
            raise Exception("Invalid color. Color value must be 'white' or 'black'")

    def controller_draw_string(self, x, y, string, image, color="black"):
        """
        Draws a string starting from the given x, y position
        :param x: starting x position
        :param y: starting y position
        :param string: the string to write
        :param image: image object where string will be drawn on
        :param color: color of string
        :return: nothing
        """
        if not isinstance(image, PIL.Image.Image):
            if sys.platform != 'emscripten':
                raise Exception("Unable to draw string on image canvas. Use controller_create_canvas() to create a canvas.")
            else:
                print("Error: Unable to draw string on image canvas. Use controller_create_canvas() to create a canvas.",color="error")
                raise Exception("Unable to draw string on image canvas. Use controller_create_canvas() to create a canvas.")

        if sys.platform != 'emscripten':
            return self._controller_draw_string_desktop(x, y, string, image, color)
        else:
            return asyncio.create_task(self._controller_draw_string_emscripten(x, y, string, image, color))

    def _controller_draw_string_desktop(self, x, y, string, image, color):
        draw = PIL.ImageDraw.Draw(image)
        preview_draw = PIL.ImageDraw.Draw(self._canvas)
        if color == "black" or color == "white":
            draw.text((x, int(y * 0.8)), text=string, fill=color)
            preview_draw.text((x, y), text=string, fill=color)

        else:
            raise Exception("Invalid color. Color value must be 'white' or 'black'")

    async def _controller_draw_string_emscripten(self, x, y, string, image, color):
        if (await self.get_information_data())[0] == ModelNumber.Drone_12_Drone_P1:
            warnings.warn(
                "This function is not currently supported for CoDrone EDU (JROTC ed.).",
                RuntimeWarning,
                stacklevel=2
            )
            return
        
        draw = PIL.ImageDraw.Draw(image)
        preview_draw = PIL.ImageDraw.Draw(self._canvas)
        if color == "black" or color == "white":
            draw.text((x, int(y * 0.8)), text=string, fill=color)
            preview_draw.text((x, y), text=string, fill=color)

        else:
            raise Exception("Invalid color. Color value must be 'white' or 'black'")

    def controller_draw_string_align(self, x_start, x_end, y, string, image, color="black", alignment="left"):
        """
        Draws a string from the given x_start, x_end and y positions. The string can be aligned along the x_start
        and x_end positions
        :param x_start: starting x position
        :param x_end: ending x position
        :param y: y position
        :param string: the string to write
        :param image: image object where string will be drawn on
        :param color: color of string
        :param alignment: alignment between x_start and x_end. can align left, right, or center.
        :return: nothing
        """
        if not isinstance(image, PIL.Image.Image):
            if sys.platform != 'emscripten':
                raise Exception("Unable to draw string on image canvas. Use controller_create_canvas() to create a canvas.")
            else:
                print("Error: Unable to draw string on image canvas. Use controller_create_canvas() to create a canvas.",color="error")
                raise Exception("Unable to draw string on image canvas. Use controller_create_canvas() to create a canvas.")
        if sys.platform != 'emscripten':
            return self._controller_draw_string_align_desktop(x_start, x_end, y, string, image, color, alignment)
        else:
            return asyncio.create_task(self._controller_draw_string_align_emscripten(x_start, x_end, y, string, image, color, alignment))
        

    def _controller_draw_string_align_desktop(self, x_start, x_end, y, string, image, color, alignment):
        if x_end < x_start:
            raise Exception(Fore.RED + "Error: x_end must be larger than x_start." + Style.RESET_ALL)

        draw = PIL.ImageDraw.Draw(image)
        preview_draw = PIL.ImageDraw.Draw(self._canvas)
        string_length = draw.textlength(string) # pixel length of string given image size

        if alignment == "left":
            text_start = x_start

        elif alignment == "center":
            x_mid = (x_start + x_end)//2
            string_length_mid = string_length//2
            text_start = x_mid - string_length_mid

        elif alignment == "right":
            text_start = x_end - string_length

        else:
            raise Exception(Fore.RED + "Error: Invalid alignment value. Please use 'left', 'center', 'right'." + Style.RESET_ALL)

        if color == "black" or color == "white":
            draw.text((text_start, int(y * 0.8)), text=string, fill=color)
            preview_draw.text((text_start, y), text=string, fill=color)

        else:
            raise Exception("Invalid color. Color value must be 'white' or 'black'")

    async def _controller_draw_string_align_emscripten(self, x_start, x_end, y, string, image, color, alignment):
        if (await self.get_information_data())[0] == ModelNumber.Drone_12_Drone_P1:
            warnings.warn(
                "This function is not currently supported for CoDrone EDU (JROTC ed.).",
                RuntimeWarning,
                stacklevel=2
            )
            return
        
        if x_end < x_start:
            raise Exception("x_end must be larger than x_start.")

        draw = PIL.ImageDraw.Draw(image)
        preview_draw = PIL.ImageDraw.Draw(self._canvas)
        string_length = draw.textlength(string) # pixel length of string given image size

        if alignment == "left":
            text_start = x_start

        elif alignment == "center":
            x_mid = (x_start + x_end)//2
            string_length_mid = string_length//2
            text_start = x_mid - string_length_mid

        elif alignment == "right":
            text_start = x_end - string_length

        else:
            raise Exception("Invalid alignment value. Please use 'left', 'center', 'right'.")

        if color == "black" or color == "white":
            draw.text((text_start, int(y * 0.8)), text=string, fill=color)
            preview_draw.text((text_start, y), text=string, fill=color)

        else:
            raise Exception("Invalid color. Color value must be 'white' or 'black'")

    def controller_draw_image(self, pixel_list):
        """
        draws image when given a pixel_list of image data
        :param pixel_list: the list of image data
        :return: nothing
        """
        if sys.platform != 'emscripten':
            return self._controller_draw_image_desktop(pixel_list)
        else:
            return asyncio.create_task(self._controller_draw_image_emscripten(pixel_list))
    
    def _controller_draw_image_desktop(self, pixel_list):
        self.controller_clear_screen()

        if isinstance(pixel_list, list) is not True:
            print(Fore.RED + "Error: the pixel list passed into controller_draw_image() is not a list." + Style.RESET_ALL)
            return None

        num_elem = len(pixel_list[0])
        for k in range(64):
            for i in range(128):

                if (127 * k) + i == 8001:
                    return  # end
                else:
                    current_index = pixel_list[(127 * k) + i]

                if num_elem == 4:  # png
                    if current_index[0] > 200 and current_index[1] > 200 and current_index[2] > 200 and \
                            current_index[3] > 200:
                        None
                    elif current_index[0] == 0 and current_index[1] == 0 and current_index[2] == 0 and \
                            current_index[3] == 0:
                        None
                    else:
                        self.sendDisplayDrawPoint(i, k, DisplayPixel.Black)
                        self.sendDisplayDrawPoint(i, k, DisplayPixel.Black)
                        time.sleep(0.001)

                elif num_elem == 3:  # jpg
                    if current_index[0] > 200 and current_index[1] > 200 and current_index[2] > 200:
                        None
                    else:
                        self.sendDisplayDrawPoint(i, k, DisplayPixel.Black)
                        self.sendDisplayDrawPoint(i, k, DisplayPixel.Black)
                        time.sleep(0.001)
                else:
                    print("Can't find image type. Please use a .jpg or .png file")
                    return
                
    async def _controller_draw_image_emscripten(self, pixel_list):
        if (await self.get_information_data())[0] == ModelNumber.Drone_12_Drone_P1:
            warnings.warn(
                "This function is not currently supported for CoDrone EDU (JROTC ed.).",
                RuntimeWarning,
                stacklevel=2
            )
            return

        await self.controller_clear_screen()

        if isinstance(pixel_list, list) is not True:
            print("Error: the pixel list passed into controller_draw_image() is not a list", color="error")
            return None

        num_elem = len(pixel_list[0])
        for k in range(64):
            for i in range(128):

                if (127 * k) + i == 8001:
                    return  # end
                else:
                    current_index = pixel_list[(127 * k) + i]

                if num_elem == 4:  # png
                    if current_index[0] > 200 and current_index[1] > 200 and current_index[2] > 200 and \
                            current_index[3] > 200:
                        None
                    elif current_index[0] == 0 and current_index[1] == 0 and current_index[2] == 0 and \
                            current_index[3] == 0:
                        None
                    else:
                        await self.sendDisplayDrawPoint(i, k, DisplayPixel.Black)
                        await self.sendDisplayDrawPoint(i, k, DisplayPixel.Black)

                elif num_elem == 3:  # jpg
                    if current_index[0] > 200 and current_index[1] > 200 and current_index[2] > 200:
                        None
                    else:
                        await self.sendDisplayDrawPoint(i, k, DisplayPixel.Black)
                        await self.sendDisplayDrawPoint(i, k, DisplayPixel.Black)
                else:
                    print("Can't find image type. Please use a .jpg or .png file")
                    return

    # Display End

    # Buzzer Start

    def sendBuzzer(self, mode, value, duration):

        if ((not isinstance(mode, BuzzerMode)) or
                (not isinstance(value, int)) or
                (not isinstance(duration, int))):
            return None

        header = Header()

        header.dataType = DataType.Buzzer
        header.length = Buzzer.getSize()
        header.from_ = DeviceType.Base
        header.to_ = DeviceType.Controller

        data = Buzzer()

        data.mode = mode
        data.value = value
        data.time = duration

        return self.transfer(header, data)

    def sendBuzzerMute(self, duration):

        if (not isinstance(duration, int)):
            return None

        header = Header()

        header.dataType = DataType.Buzzer
        header.length = Buzzer.getSize()
        header.from_ = DeviceType.Base
        header.to_ = DeviceType.Controller

        data = Buzzer()

        data.mode = BuzzerMode.Mute
        data.value = BuzzerScale.Mute.value
        data.time = duration

        return self.transfer(header, data)

    def sendBuzzerMuteReserve(self, duration):

        if (not isinstance(duration, int)):
            return None

        header = Header()

        header.dataType = DataType.Buzzer
        header.length = Buzzer.getSize()
        header.from_ = DeviceType.Base
        header.to_ = DeviceType.Controller

        data = Buzzer()

        data.mode = BuzzerMode.MuteReserve
        data.value = BuzzerScale.Mute.value
        data.time = duration

        return self.transfer(header, data)

    def sendBuzzerScale(self, scale, duration):

        if ((not isinstance(scale, BuzzerScale)) or
                (not isinstance(duration, int))):
            return None

        header = Header()

        header.dataType = DataType.Buzzer
        header.length = Buzzer.getSize()
        header.from_ = DeviceType.Base
        header.to_ = DeviceType.Controller

        data = Buzzer()

        data.mode = BuzzerMode.Scale
        data.value = scale.value
        data.time = duration

        return self.transfer(header, data)

    def sendBuzzerScaleReserve(self, scale, duration):

        if ((not isinstance(scale, BuzzerScale)) or
                (not isinstance(duration, int))):
            return None

        header = Header()

        header.dataType = DataType.Buzzer
        header.length = Buzzer.getSize()
        header.from_ = DeviceType.Base
        header.to_ = DeviceType.Controller

        data = Buzzer()

        data.mode = BuzzerMode.ScaleReserve
        data.value = scale.value
        data.time = duration

        return self.transfer(header, data)

    def sendBuzzerHz(self, hz, duration):

        if ((not isinstance(hz, int)) or
                (not isinstance(duration, int))):
            return None

        header = Header()

        header.dataType = DataType.Buzzer
        header.length = Buzzer.getSize()
        header.from_ = DeviceType.Base
        header.to_ = DeviceType.Controller

        data = Buzzer()

        data.mode = BuzzerMode.Hz
        data.value = hz
        data.time = duration

        return self.transfer(header, data)

    def sendBuzzerHzReserve(self, hz, duration):

        if ((not isinstance(hz, int)) or
                (not isinstance(duration, int))):
            return None

        header = Header()

        header.dataType = DataType.Buzzer
        header.length = Buzzer.getSize()
        header.from_ = DeviceType.Base
        header.to_ = DeviceType.Controller

        data = Buzzer()

        data.mode = BuzzerMode.HzReserve
        data.value = hz
        data.time = duration

        return self.transfer(header, data)

    # Buzzer End

    # Vibrator Start

    def sendVibrator(self, on, off, total):

        if ((not isinstance(on, int)) or
                (not isinstance(off, int)) or
                (not isinstance(total, int))):
            return None

        header = Header()

        header.dataType = DataType.Vibrator
        header.length = Vibrator.getSize()
        header.from_ = DeviceType.Base
        header.to_ = DeviceType.Controller

        data = Vibrator()

        data.mode = VibratorMode.Instantally
        data.on = on
        data.off = off
        data.total = total

        return self.transfer(header, data)

    def sendVibratorReserve(self, on, off, total):

        if ((not isinstance(on, int)) or
                (not isinstance(off, int)) or
                (not isinstance(total, int))):
            return None

        header = Header()

        header.dataType = DataType.Vibrator
        header.length = Vibrator.getSize()
        header.from_ = DeviceType.Base
        header.to_ = DeviceType.Controller

        data = Vibrator()

        data.mode = VibratorMode.Continually
        data.on = on
        data.off = off
        data.total = total

        return self.transfer(header, data)

# Vibrator End


# Update Start


# Update End

# ColorClassifier Start
class ColorClassifier:
    def __init__(self, n_neighbors=9):
        self.n_neighbors = n_neighbors
        self.x_train = None
        self.y_train = None

    def reset(self):
        self.x_train = None
        self.y_train = None

    def fit(self, x_train, y_train):
        self.x_train = np.array(x_train)
        self.y_train = np.array(y_train)

    def _euclidean_distance(self, x_test_point, x_train):
        return np.sqrt(np.sum((x_train - x_test_point) ** 2, axis=1))

    def predict(self, x_test):
        x_test_point = np.array(x_test)

        distances = self._euclidean_distance(x_test_point, self.x_train)

        # sort distances and collect the indices of the k-nearest neighbors
        neighbor_indices = np.argsort(distances)[:self.n_neighbors]

        # collect the labels of the k-nearest neighbors and count the number of occurrences
        neighbor_label_count = {}
        for i in neighbor_indices:
            if self.y_train[i] not in neighbor_label_count:
                neighbor_label_count[self.y_train[i]] = 1
            else:
                neighbor_label_count[self.y_train[i]] += 1

        # find which label has the most occurrences
        prediction = max(neighbor_label_count, key=neighbor_label_count.get)

        return prediction


# ColorClassifier End

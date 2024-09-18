import os
import abc
import sys
import ssl
from struct import *
from enum import Enum
from urllib.request import urlopen
from time import sleep

from codrone_edu.drone import *


class FirmwareHeader():

    def __init__(self):
        self.modelNumber        = 0
        self.version            = 0
        self.length             = 0

        self.year               = 0
        self.month              = 0
        self.day                = 0

        self.versionMajor       = 0
        self.versionMinor       = 0
        self.versionBuild       = 0

    @classmethod
    def getSize(cls):
        return 16

    @classmethod
    def parse(cls, dataArray):
        data = FirmwareHeader()
        
        if len(dataArray) != cls.getSize():
            return None
        
        data.modelNumber, data.version, data.length, data.year, data.month, data.day = unpack('<IIIHBB', dataArray)
        data.modelNumber = ModelNumber(data.modelNumber)
        data.versionMajor = (data.version >> 24) & 0xFF
        data.versionMinor = (data.version >> 16) & 0xFF
        data.versionBuild = (data.version & 0xFFFF)

        return data


class Firmware:

    def __init__(self, file_path=None):

        if file_path is None:
            self.file_path = None     # Local file path
            self.resource = None      # Firmware binary data
            self.header = None        # Firmware header
            self.length = 0           # Length of the firmware data
            self.rawHeader = None     # Raw header data
            self.stringHeader = None  # Header data as a HEX string
        else:
            self.open(file_path)

    def open(self, file_path):

        self.file_path = file_path

        # Read the firmware data from a local file instead of a URL
        with open(self.file_path, 'rb') as file:
            self.resource = file.read()
            self.length = len(self.resource)
            self.rawHeader = self.resource[0:16]
            self.header = FirmwareHeader.parse(self.rawHeader)

            self.stringHeader = ""
            for data in self.rawHeader:
                self.stringHeader += "{0:02X} ".format(data)

            # Assuming you want to keep the print statements for confirmation
            print(Fore.CYAN + "  - {0}".format(self.header.modelNumber) + Style.RESET_ALL)
            print("    Header Hex : {0}".format(self.stringHeader))
            print("     File Size : {0} bytes".format(self.length))
            print("       Version : {0}.{1}.{2}".format(self.header.versionMajor, self.header.versionMinor, self.header.versionBuild))
            print("          Date : {0}.{1}.{2}".format(self.header.year, self.header.month, self.header.day))
            print("        Length : {0}\n".format(self.header.length))


class FirmwareURL:
    def __init__(self, url = None):

        if url == None:
            self.url            = 0         # firmware URL
            self.resource       = None      # entire firmware file
            self.header         = None      # firmware header
            self.length         = 0         # length of the firmware data

            self.rawHeader      = None      # Header array
            self.stringHeader   = None      # Header array converted to HEX string
        else:
            self.open(url)

    def open(self, url):

        self.url = url

        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        with urlopen(self.url, context=ssl_context) as res:
            self.resource   = res.read()
            self.length     = len(self.resource)
            self.rawHeader  = self.resource[0:16]
            self.header     = FirmwareHeader.parse(self.rawHeader)

            self.stringHeader = ""
            for data in self.rawHeader:
                self.stringHeader += "{0:02X} ".format(data)

            print(Fore.CYAN + "  - {0}".format(self.header.modelNumber) + Style.RESET_ALL)
            print("    Header Hex : {0}".format(self.stringHeader))
            print("     File Size : {0} bytes".format(self.length))
            print("       Version : {0}.{1}.{2}".format(self.header.versionMajor, self.header.versionMinor, self.header.versionBuild))
            print("          Date : {0}.{1}.{2}".format(self.header.year, self.header.month, self.header.day))
            print("        Length : {0}\n".format(self.header.length))

# Firmware End


class Updater:

    def __init__(self, online):

        self.modelNumber        = None
        self.deviceType         = None
        self.modeUpdate         = ModeUpdate.None_
        self.indexBlockNext     = 0
        self.flagUpdated        = False
        self.flagUpdateComplete = False
        self.onlineUpdate       = online


    def eventInformation(self, information):

        self.modeUpdate         = information.modeUpdate
        self.flagUpdated        = True
        self.modelNumber        = information.modelNumber
        self.deviceType         = DeviceType(((self.modelNumber.value >> 8) & 0xFF))
        
        if information.modeUpdate == ModeUpdate.Complete:
            self.flagUpdateComplete = True
        else:
            print(Fore.YELLOW + "* Connected Device : {0}".format(self.deviceType) + Style.RESET_ALL)
            print("  Model Number : {0}".format(information.modelNumber))
            print("       Version : {0}.{1}.{2} ({3} / 0x{3:08X})".format(information.version.major, information.version.minor, information.version.build, information.version.v))
            print("  Release Date : {0}.{1}.{2}".format(information.year, information.month, information.day))
            print("   Mode Update : {0}\n".format(information.modeUpdate))

    def eventUpdateLocation(self, updateLocation):

        self.flagUpdated        = True
        self.indexBlockNext     = updateLocation.indexBlockNext
        #print("* eventUpdateLocation({0})\n".format(updateLocation.indexBlockNext))


    def update(self):

        colorama.init()

        print(Back.WHITE + Fore.BLUE + " FIRMWARE UPDATE " + Style.RESET_ALL)
        print("")

        print(Fore.YELLOW + "* Firmware loading." + Style.RESET_ALL)
        print("")

        drone = Drone()

        if drone.open(updater=True) == False:
            print(Fore.RED + "* Error : Unable to open serial port." + Style.RESET_ALL)
            sys.exit(1)


        # Register event handling functions
        drone.setEventHandler(DataType.Information, self.eventInformation)
        drone.setEventHandler(DataType.UpdateLocation, self.eventUpdateLocation)

        flagRun             = True
        countError          = 0
        timeTransferNext    = 0
        timeDrawNext        = 0     # 업데이트 상태 다음 갱신 시각

        #print("sending request for drone")
        drone.sendRequest(DeviceType.Drone, DataType.Information)
        sleep(0.2)

        #print("sending request for controller")
        drone.sendRequest(DeviceType.Controller, DataType.Information)
        sleep(0.2)

        #print("device type ", self.deviceType)

        if self.deviceType == None:
            print(Fore.RED + "* Error : Could not detect device." + Style.RESET_ALL)
            sys.exit(1)

        header = Header()
        header.dataType = DataType.Update
        header.length   = 18
        header.from_    = DeviceType.Updater
        header.to_      = self.deviceType

        drone.sendRequest(header.to_, DataType.UpdateLocation)
        sleep(0.1)

        drone.sendRequest(header.to_, DataType.UpdateLocation)
        sleep(0.1)

        #print("model number", self.modelNumber)
        if self.modelNumber == ModelNumber.Drone_12_Drone_P1 or self.modelNumber == ModelNumber.Drone_12_Controller_P1:
            print(Fore.RED + "Python firmware updater not available for CoDrone EDU (JROTC ed.)")
            exit()

        # ------------------- FIRMWARE SELECTION ---------------------------
        if self.onlineUpdate:
            if self.deviceType == DeviceType.Drone:
                if self.modelNumber == ModelNumber.Drone_8_Drone_P1:
                    firmware_file = "https://storage.googleapis.com/codrone/cde_drone_p1_22_8_1.eb"
                else:
                    print(Fore.RED + "Python firmware updater not available for this device.")
                    exit()

            if self.deviceType == DeviceType.Controller:

                if self.modelNumber == ModelNumber.Drone_4_Controller_P3:
                    firmware_file = "https://storage.googleapis.com/codrone/cde_controller_p3_23_1_1.eb"
                elif self.modelNumber == ModelNumber.Drone_4_Controller_P2:
                    firmware_file = "https://storage.googleapis.com/codrone/cde_controller_p2_23_1_1.eb"
                else:
                    print(Fore.RED + "Python firmware updater not available for this device.")
                    exit()

            firmware = FirmwareURL(firmware_file)

        else:   # running offline

            lib_dir = os.path.dirname(os.path.abspath(__file__))

            if self.deviceType == DeviceType.Controller:  # if a controller is connected

                # if self.modelNumber == ModelNumber.Drone_12_Controller_P1:  # (JROTC ed.) controller first version
                #     fw_filepath = lib_dir + "/controller_jrotc.br"

                if self.modelNumber == ModelNumber.Drone_4_Controller_P3:  # CDE controller third (current) version
                    fw_filepath = lib_dir + "/cde_controller_p3_23_1_1.eb"

                elif self.modelNumber == ModelNumber.Drone_4_Controller_P2:  # CDE controller second version
                    fw_filepath = lib_dir + "/cde_controller_p2_23_1_1.eb"

                else:                                                        # Not a supported controller
                    print(Fore.RED + "Python firmware updater not available for this device.)")
                    exit()
            
            elif self.deviceType == DeviceType.Drone:  # if a drone is connected

                # if self.modelNumber == ModelNumber.Drone_12_Drone_P1:   # (JROTC ed.) drone first version
                #     fw_filepath = lib_dir + "/drone_jrotc.br"
                if self.modelNumber == ModelNumber.Drone_8_Drone_P1:   # CDE drone third (current) version
                    fw_filepath = lib_dir + "/cde_drone_p1_22_8_1.eb"
                else:
                    print(Fore.RED + "Python firmware updater not available for this device.)")
                    exit()

            firmware = Firmware(fw_filepath)  # load the firmware file

        # -------------------------------------------------------------------
        # Firmware updater

        # Verify that the device model matches firmware model
        if self.modelNumber == firmware.header.modelNumber:
            # print("fw header modelNumber ", firmware.header.modelNumber)
            # print("mode update ", self.modeUpdate)
            
            if self.modeUpdate == ModeUpdate.Ready or self.modeUpdate == ModeUpdate.Update:

                while flagRun:  # this is initialized to True

                    sleep(0.001)
                    now = time.perf_counter() * 1000

                    #print("flagUpdated ", self.flagUpdated)

                    if (self.flagUpdated == True) or (timeTransferNext < now):

                        #print("indexBlockNext ", self.indexBlockNext)

                        if self.indexBlockNext == 0:
                            timeTransferNext = now + 2400
                        else:
                            timeTransferNext = now + 100

                        # Error count
                        if self.flagUpdated == False:

                            countError = countError + 1

                            # # Cancel the update if errors accumulate excessively
                            if countError > 30:
                                print(Fore.RED + "* Error : No response." + Style.RESET_ALL)
                                flagRun = False
                        
                        else:
                            countError = 0

                        index = self.indexBlockNext * 16

                        # Terminate if the update position is exceeded
                        if index + 16 > firmware.length:
                            print(Fore.RED + "* Error : Index Over." + Style.RESET_ALL)
                            flagRun = False
                            break

                        # Terminate if the update is complete
                        if self.flagUpdateComplete == True:
                            sleep(1)
                            print("\n\n" + Fore.GREEN + "  Update Complete." + Style.RESET_ALL)
                            flagRun = False
                            break

                        data = bytearray(2)
                        data[0] = self.indexBlockNext & 0xFF
                        data[1] = (self.indexBlockNext >> 8) & 0xFF
                        data.extend(firmware.resource[index : index + 16])
                        drone.transfer(header, data)
                        
                        self.flagUpdated = False

                        # 진행률 표시
                        if (timeDrawNext < now) or (firmware.length - index < 128):

                            timeDrawNext    = now + 73
                            percentage      = index * 100 / firmware.length
                            print(Fore.YELLOW + "\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b{0:8.1f}%".format(percentage) + Style.RESET_ALL, end='')
            else:
                print(Fore.RED + "* Error : Firmware update is not available. Check that your device is in bootloader state." + Style.RESET_ALL)

        drone.close()


# Updater End




# Main Start

if __name__ == '__main__':

    updater = Updater(online=False)
    updater.update()


# Main End


from codrone_edu.drone import *
import re

def separate_letters_numbers(s):
    match = re.match(r"([a-zA-Z]+)(\d+)", s)
    if match:
        return match.group(1), match.group(2)
    else:
        return None, None


drone = Drone()
drone.pair()


noteString = "c4.d4.e4.f4.g4.a4.b4.c5"
parsedList = noteString.split('.')

for tempNote in parsedList:
    tempNote = tempNote.upper()

    if(tempNote == 'R'):
        continue

    let, num = separate_letters_numbers(tempNote)
    num = int(num)


    tempNum = 0
    if(let == 'C'):
        tempNum+=0
    elif (let == 'CS' or let == 'DF'):
        tempNum += 1
    elif (let == 'D'):
        tempNum += 2
    elif (let == 'DS' or let == 'EF'):
        tempNum += 3
    elif (let == 'E'):
        tempNum += 4
    elif (let == 'F'):
        tempNum += 5
    elif (let == 'FS' or let == 'GF'):
        tempNum += 6
    elif (let == 'G'):
        tempNum += 7
    elif (let == 'GS' or let == 'AF'):
        tempNum += 8
    elif (let == 'A'):
        tempNum += 9
    elif (let == 'AS' or let == 'BF'):
        tempNum += 10
    elif (let == 'B'):
        tempNum += 11

    tempNum += ((num-1)*12)

    print(tempNum)

    newnote = Note(tempNum)
    drone.drone_buzzer(newnote, 1000)






drone.close()
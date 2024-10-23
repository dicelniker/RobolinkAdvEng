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

tempo = 120
noteString = "b3.r.c4.r.r.r.r.c4.r.c4.a4.r"
parsedList = noteString.split('.')
quarternotelength = int(60000/tempo)
eighthnotelength = int(30000/tempo)
sixteenthnotelength = int(15000/tempo/2)
for tempNote in parsedList:
    tempNote = tempNote.upper()

    if(tempNote == 'R'):
        sleep(quarternotelength/1000)
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

    newnote = Note(int(tempNum))
    drone.controller_buzzer(newnote, sixteenthnotelength)

drone.close()
import threading
import time
import keyboard
import mouse
import winmouse

# Constants
settingsPath = "./settings"
loggPath = "./logg"

# Getting variables (settings)
settingsFile = open(settingsPath, "rt")
settings = settingsFile.read()
settingsFile.close()

keys = {"exit": "exit program:",
        "logg": "start/stop recording:",
        "mimic": "start/stop replaying:"}

for key_id in keys.keys():
    offset = settings.find(keys[key_id]) + len(keys[key_id])
    size = settings[offset:].find("\n")
    val = settings[offset:(offset + size)]
    keys[key_id] = val.replace(" ", "").lower()

# Setup
states = {"logging": False, "mimicking": False,
          False: {False: "Idle",                   # logging is False and mimicing is False
                  True: "Replaying"},              # logging is False and mimicing is True
          True: {False: "Recording",               # logging is True and mimicing is False
                 True: "Recording & Replaying"}}   # logging is True and mimicing is True


# Methods that make everything more straightforward
def print_state(prefix: str):
    print(f"{prefix} state: {states[states["logging"]][states["mimicking"]]}")


# Mimics & Loggers
def keylogg(init_time: float):
    if states["logging"]:  # Do some prep first
        loggFile = open(loggPath, "at")
        keystrokes = set()
        prevTimestamp = init_time

        def logg(event: keyboard.KeyboardEvent):
            nonlocal prevTimestamp
            if not states["logging"]:
                return
            keypress, timestamp = event.name, time.perf_counter()  # Updating values
            delay = round(timestamp - prevTimestamp, 4)  # Approximating to save less data

            # Key press recording
            if event.event_type == "down" and keypress not in keystrokes\
                    and keypress not in keys.values():
                keystrokes.add(keypress)
                loggFile.write(f"K, {delay}, {keypress}, down\n")
                loggFile.flush()

            # Key release recording
            elif event.event_type == "up" and keypress in keystrokes:
                keystrokes.remove(keypress)
                loggFile.write(f"K, {delay}, {keypress}, up\n")
                loggFile.flush()

            prevTimestamp = timestamp  # Next keystroke prep
        loggHook = keyboard.hook(logg)  # Keyboard press/release hooks

        # Logging thread waits while keyboard does the work
        while states["logging"]:
            time.sleep(0.001)

        # Unhook, i.e. stop recording & close file
        keyboard.unhook(loggHook)
        loggFile.close()


def clicklogg(init_time: float):
    if states["logging"]:  # Prep
        loggFile = open(loggPath, "at")
        prevTimestamp = init_time

        # Recording mouse
        def mouse_event(event):  # Do some prep first
            nonlocal prevTimestamp
            if not states["logging"]:
                return

            # Getting change in data
            timestamp = time.perf_counter()
            delay = round(timestamp - prevTimestamp, 4)  # Approximating to save less data
            if isinstance(event, mouse._mouse_event.MoveEvent):  # Mouse movement
                loggFile.write(f"M, {delay}, {event.x}, {event.y}\n")

            elif isinstance(event, mouse._mouse_event.WheelEvent):  # Mouse wheel movement
                loggFile.write(f"S, {delay}, {event.delta}\n")
                loggFile.flush()

            elif isinstance(event, mouse._mouse_event.ButtonEvent):  # Mouse button press
                if event.event_type == "down" or event.event_type == "double":
                    loggFile.write(f"C, {delay}, {event.button}, down\n")
                    loggFile.flush()

                elif event.event_type == "up":  # Mouse button release
                    loggFile.write(f"C, {delay}, {event.button}, up\n")
                    loggFile.flush()

            # Updates
            loggFile.flush()
            prevTimestamp = timestamp

        mouseHook = mouse.hook(mouse_event)  # Mouse press/release hooks
        while states["logging"]:  # Logging thread waits while mouse does the work
            time.sleep(0.001)

        # Unhook, i.e. stop recording & close file
        mouse.unhook(mouseHook)
        loggFile.close()


def mimick():
    if states["mimicking"]:  # Prep
        try:
            loggFile = open(loggPath, "rt")

            # Mimicking keystrokes & mouseclicks
            delta = 0.001  # The lower the value, the more the mimicking accuracy may decrease
            while states["mimicking"]:
                command = loggFile.readline()
                if not command:  # End of logg:
                    loggFile.seek(0)  # Loop back to start
                    continue

                # Separating data part 1
                command = command.strip("\n").split(", ")
                mode = command[0]  # Type of action that was made
                delay = float(command[1])  # Time until next action, i.e. delay

                # Making it responsive to potential halting
                def resp():
                    nonlocal delay, delta
                    while states["mimicking"] and delay > 0:  # Making it responsive
                        time.sleep(min(delay, delta))
                        delay -= delta

                # Separating data part 2 & executing it
                if mode == "K":  # Reading as keystroke
                    key, use = command[2], command[3]  # Keyboard key & whether pressed/released
                    resp()
                    if use == "down":  # Recreating press
                        keyboard.press(key)
                    elif use == "up":  # Recreating release
                        keyboard.release(key)

                elif mode == "M":  # Reading as mouse movement
                    posX, posY = int(command[2]), int(command[3])  # Next mouse position
                    resp()
                    winmouse.move(posX, posY)  # Recreating pointer movement

                elif mode == "S":  # Reading as mouse scroll
                    mov = int(command[2])  # Mouse wheel scroll direction
                    resp()
                    mouse.wheel(mov)  # Recreating mouse scroll

                elif mode == "C":  # Reading as mouse click
                    button, use = command[2], command[3]  # Mouse button & whether pressed/released
                    resp()
                    if use == "down":  # Recreating press
                        mouse.press(button)
                    elif use == "up":  # Recreating release
                        mouse.release(button)

            loggFile.close()  # Closing file
        except FileNotFoundError:
            print("Log file missing! Record something first.")


# Welcome text
print(f"\n--- Welcome fellow user! Here are the instructions: ---\n"
      f"Press '{keys["exit"].upper()}' to exit the program.\n"
      f"Press '{keys["logg"].upper()}' to start/stop recording your actions.\n"
      f"Press '{keys["mimic"].upper()}' to start/stop replaying those actions.\n")

# Setup
keylogger: threading.Thread | None = None
clicklogger: threading.Thread | None = None
mimicker: threading.Thread | None = None
running = True


# Main process checks for related triggers and initiates threads
def launcher(event: keyboard.KeyboardEvent):
    global keylogger, clicklogger, mimicker, running  # Prep
    if event.event_type == "up":
        key = event.name

        # Program halt trigger
        if key == keys["exit"]:
            running, states["logging"], states["mimicking"] = False, False, False
            if keylogger is not None:
                keylogger.join()
            if clicklogger is not None:
                clicklogger.join()
            if mimicker is not None:
                mimicker.join()
            print_state("Exit")

        # Logging trigger
        elif key == keys["logg"]:
            if states["logging"]:  # Stopping logging
                states["logging"] = False
                keylogger.join(), clicklogger.join()
                print_state("Current")

            else:  # Starting logging
                initialTime = time.perf_counter()
                open(loggPath, "w").close()  # Starting with an empty file
                states["logging"] = True
                keylogger = threading.Thread(target=keylogg, args=[initialTime])
                clicklogger = threading.Thread(target=clicklogg, args=[initialTime])
                keylogger.start(), clicklogger.start()
                print_state("Current")

        # Mimicking (i.e. repeating) trigger
        elif key == keys["mimic"]:
            if states["mimicking"]:  # Stopping mimicking
                states["mimicking"] = False
                if mimicker is not None:
                    mimicker.join()
                print_state("Current")

            else:  # Starting mimicking
                mimicker = threading.Thread(target=mimick)
                states["mimicking"] = True
                mimicker.start()
                print_state("Current")


# Main hook
launcherHook = keyboard.hook(launcher)
print_state("Start")  # Starting state info

# Process waits until finished
while running:
    time.sleep(0.001)

# Shutdown
states["logging"], states["mimicking"] = False, False
keyboard.unhook(launcherHook)
if keylogger is not None:
    keylogger.join()
if clicklogger is not None:
    clicklogger.join()
if mimicker is not None:
    mimicker.join()

print("\nBye bye 0/ Hope to see you again :D\n"
      "But seriously, don't leave me behind ;(\n"
      "It's kinda dark in here you know...")

exit()

#!/usr/bin/env python3

from inputs import devices, get_gamepad
import socket
import time
import queue
import sys
import threading


def all_controllers_are_separate(game_state):
    return game_state


def one_democratic_controller(game_state):
    democratic_game_state = {
        "X": 0,
        "Y": 0,
        "1": 0,
        "2": 0,
        "3": 0,
        "4": 0,
    }

    # Sum inputs
    for controller in game_state:
        for channel, value in controller.items():
            democratic_game_state[channel] += value
    # print("game state sum:", democratic_game_state)

    # Filter inputs with only one supporter
    for channel, value in democratic_game_state.items():
        if value < -1:
            democratic_game_state[channel] = -1
        elif value > 1:
            democratic_game_state[channel] = 1
        else:
            democratic_game_state[channel] = 0

    return [democratic_game_state]

def usage():
    print(f"Usage: {sys.argv[0]} [--democracy] REMOTE_HOST...")
    print("   REMOTE_HOST   One or more addresses to send inputs to")
    print("   --democracy   Map all controllers into one. At least two inputs are required to activate.")
    sys.exit(0)

game_state_mapper = all_controllers_are_separate

args = sys.argv[1:]
if len(args) == 0:
    usage()

if args[0] == "--democracy":
    print("Using democracy mode")
    game_state_mapper = one_democratic_controller
    args = args[1:]

if len(args) == 0:
    usage()


hosts = args
socks = []
for host in hosts:
    try:
        port = 55555
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect((host, port))

    except socket.gaierror:
        print(f"Host {host} not known")
        sys.exit(1)
    socks.append(sock)
print("Sending keys to the following endpoints:", ", ".join(hosts))


class GamepadReader(threading.Thread):

    def __init__(self, events, gamepad):
        super().__init__()
        self.__events = events
        self.__id, self.__gamepad = gamepad

    def run(self):
        while True:
            try:
                event = self.__gamepad.read()
            except OSError:
                print("Gamepad removed, exiting.")
                sys.exit(1)
            self.__events.put((self.__id, event))


game_state = []
game_state_changed = False

event_queue = queue.Queue()
print("Using the following game controllers:")
for gamepad in enumerate(devices.gamepads):
    gamepad_id, gamepad_device = gamepad
    game_state.append({
        "X": 0,
        "Y": 0,
        "1": 0,
        "2": 0,
        "3": 0,
        "4": 0,
    })
    print(f"{gamepad_id}. {gamepad_device}")
    GamepadReader(event_queue, gamepad).start()


while True:
    try:
        gid, events = event_queue.get()
    except KeyboardInterrupt:
        sys.exit(0)

    for event in events:
        game_state_changed = True
        # PS1/2 gamepad with usb adapter
        if event.code == "ABS_X":
            if event.state < 127:
                game_state[gid]["X"] = -1
            elif event.state > 128:
                game_state[gid]["X"] = 1
            else:
                game_state[gid]["X"] = 0
        elif event.code == "ABS_Y":
            if event.state < 127:
                game_state[gid]["Y"] = -1
            elif event.state > 128:
                game_state[gid]["Y"] = 1
            else:
                game_state[gid]["Y"] = 0
        elif event.code == "BTN_TOP":
            game_state[gid]["1"] = event.state
        elif event.code == "BTN_THUMB2":
            game_state[gid]["2"] = event.state
        elif event.code == "BTN_THUMB":
            game_state[gid]["3"] = event.state
        elif event.code == "BTN_BASE3":
            game_state[gid]["4"] = event.state

        # X360 USB
        # elif event.code.startswith("ABS_HAT0"):
        #     axis, direction = event.code[8], event.state
        #     game_state[gid][axis] = int(direction)
        # elif event.code.startswith("BTN_"):
        #     button, state = event.code[4], event.state
        #     print(button, state)
        #     game_state[gid][button] = int(state)
       
        else:
            # print(gid, event.code, event.state)
            game_state_changed = False

    if game_state_changed:
        sent_game_state = game_state_mapper(game_state)
        # print(sent_game_state)
        game_state_payload = ""
        for controller in sent_game_state:
            key_vector = list("00000000")
            #                  UDLRABCD
            if controller["Y"] < 0:
                key_vector[0] = "1"
            if controller["Y"] > 0:
                key_vector[1] = "1"
            if controller["X"] < 0:
                key_vector[2] = "1"
            if controller["X"] > 0:
                key_vector[3] = "1"
            if controller["1"] == 1:
                key_vector[4] = "1"
            if controller["2"] == 1:
                key_vector[5] = "1"
            if controller["3"] == 1:
                key_vector[6] = "1"
            if controller["4"] == 1:
                key_vector[7] = "1"
            game_state_payload += "".join(key_vector)

        encoded_payload = game_state_payload.encode("ascii")
        print(encoded_payload)
        try:
            # TODO: Add multicast / broadcast support
            for sock in socks:
                sock.send(encoded_payload)
        except ConnectionRefusedError:
            # Keep retrying
            pass
        game_state_changed = False

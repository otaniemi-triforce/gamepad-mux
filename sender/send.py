#!/usr/bin/env python3

from inputs import devices, get_gamepad
import socket
import time
import queue
import sys
import threading


hosts = sys.argv[1:]
if len(hosts) == 0:
    print(f"Usage: {sys.argv[0]} REMOTE_HOST...")
    sys.exit(0)

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

gamepad_state = {
    "X": 0, # D-pad X axis
    "Y": 0, # D-pad Y axis
    "S": 0, # A
    "E": 0, # B
    "N": 0, # X, west is down for some reason
    "W": 0, # Y, likewise, east is up
}
gamepad_state_changed = False
gamepad_last_update_sent = time.clock()


class GamepadReader(threading.Thread):

    def __init__(self, events, gamepad):
        super().__init__()
        self.__events = events
        self.__id, self.__gamepad = gamepad

    def run(self):
        while True:
            event = self.__gamepad.read()
            self.__events.put((self.__id, event))


event_queue = queue.Queue()
for gamepad in enumerate(devices.gamepads):
    gamepad_id, gamepad_device = gamepad
    print(f"{gamepad_id}. {gamepad_device}")
    GamepadReader(event_queue, gamepad).start()


while True:
    try:
        gid, events = event_queue.get()
    except KeyboardInterrupt:
        print()  # newline
        sys.exit(0)
    except OSError:
        print("Gamepad removed. Thank you for flying with Triforce Airlines.")
        sys.exit(1)

    for event in events:
        print(gid, event.code, event.state)
        if event.code.startswith("ABS_HAT0"):
            axis, direction = event.code[8], event.state
            gamepad_state[axis] = int(direction)
            gamepad_state_changed = True
        elif event.code.startswith("BTN_"):
            button, state = event.code[4], event.state
            print(button, state)
            gamepad_state[button] = int(state)
            gamepad_state_changed = True        
        # else:
        #     print(event.code, event.state)

    now = time.clock()

    if gamepad_state_changed or now > gamepad_last_update_sent + 1:
        key_vector = list("00000000")
        #                  UDLRABCD
        if gamepad_state["Y"] == -1:
            key_vector[0] = "1"
        if gamepad_state["Y"] == 1:
            key_vector[1] = "1"
        if gamepad_state["X"] == -1:
            key_vector[2] = "1"
        if gamepad_state["X"] == 1:
            key_vector[3] = "1"
        if gamepad_state["S"] == 1:
            key_vector[4] = "1"
        if gamepad_state["E"] == 1:
            key_vector[5] = "1"
        if gamepad_state["N"] == 1:
            key_vector[6] = "1"
        if gamepad_state["W"] == 1:
            key_vector[7] = "1"

        gamepad_state_payload = "".join(key_vector).encode("ascii")
        try:
            print(gamepad_state_payload)
            for sock in socks:
                sock.send(gamepad_state_payload)
        except ConnectionRefusedError:
            # Keep retrying
            pass

        gamepad_state_changed = False
        gamepad_last_update_sent = now
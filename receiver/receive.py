from pynput.keyboard import Key, Controller
from time import sleep
import socket, select

output_keyboard = Controller()

IP = "82.130.61.209"
PORT = 55555

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((IP, PORT))


keylist = ['w','s','a','d','r','t','y','u']
#, 
#           'w','s','a','d','1','2','3','4',
#           'w','s','a','d','1','2','3','4',
#           'w','s','a','d','1','2','3','4']

keys = ['a', 'b']
release = False



def keypresser(keys):
  for i in range(len(keylist)):
    output_keyboard.release(keylist[i])
    if keys[i] is '1':
      print(keylist[i])
      output_keyboard.press(keylist[i])
  



while(1):
  buf, e, o = select.select([sock], [],[], 0.5)
  if len(buf) <= 1024:
    data, addr = sock.recvfrom(1024)
    
    keys = data.decode("UTF-8")
    print(keys)
    keys = keys.replace(' ', '')
    if len(keys) is len(keylist):
      keypresser(keys)
    else:
      print("Incorrect format")
      









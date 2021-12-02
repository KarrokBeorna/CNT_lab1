import socket
import threading
import time
import os
import shutil

def read_s():
    global usernameApproved, s, user, lenMsg, filename
    while True:
        buffer = ''
        try:
            data = s.recv(1024)
            if len(data) > 2:
                lenMsg = int.from_bytes(data[:2], 'big')
                if data[2] == 3 or data[2] == 2:
                    if data[2] == 2:
                        i = 11
                        while data[i] != 255:
                            i += 1
                        lenFile = int.from_bytes(data[i+1:i+5], 'big')
                        split = data[i+5:].decode('utf8').split(' ')
                        if len(split) < 2:
                            filename = split[0]
                        else:
                            filename = split[0]
                            buffer = data[3:i].decode('utf8') + ' ' + data[i+6 + len(filename):].decode('utf8')
                    else:
                        buffer += data[3:].decode('utf8')
                    lenMsg -= 1022
                    while lenMsg > 0:
                        data = s.recv(1024)
                        buffer += data.decode('utf8')
                        lenMsg -= 1024
                    if len(buffer) != 0:
                        print(buffer)
                    if data[2] == 2:
                        with open('files' + user + '/' + filename, 'wb') as f:
                            time.sleep(1)
                            while lenFile > 0:
                                datafile = s.recv(4096)
                                f.write(datafile)
                                lenFile -= 4096
                elif data[2] == 0:
                    usernameApproved = True
                    buffer += data[3:].decode('utf8')
                    print(buffer)
                elif data[2] == 4:
                    buffer += data[3:].decode('utf8')
                    print(buffer)
                    #newUser = data[23:].decode('utf8')

        except ConnectionResetError:
            shutil.rmtree('files' + user, ignore_errors=True)
            s.close()
            break

def createPacket(type, msg, filesize):
    byteType = b'\xFF'
    if type == 0:           # приветствие c именем пользователя и временным отклонением от UTC
        byteType = b'\x00'
    elif type == 1:         # выход
        byteType = b'\x01'
    elif type == 2:         # сообщение с файлом
        byteType = b'\x02'
    elif type == 3:         # сообщение без файла
        byteType = b'\x03'
    elif type == 4:         # изменение имени
        byteType = b'\x04'
    if filesize == 0:
        return (byteType + msg.encode('utf8'))
    else:
        return (byteType + filesize.to_bytes(4, 'big') + msg.encode('utf8'))

def sendMsg(type, msg, filesize=0):
    global s
    bytesMsg = createPacket(type, msg, filesize)
    lenMsg = len(bytesMsg).to_bytes(2, 'big')
    s.send(lenMsg + bytesMsg)

def sendPacket(msg):
    global usernameApproved, user, s
    if thread.is_alive():
        if not usernameApproved:
            sendMsg(0, msg + ' ' + str(-time.timezone))
            user = msg
            try:
                os.mkdir('files' + user)
            except Exception:
                pass
        elif msg == '>>exit<<':
            shutil.rmtree('files' + user, ignore_errors=True)
            sendMsg(1, msg)
            s.close()
            exit()
        elif msg.split(' ')[0] == '>>chname<<':
            sendMsg(4, msg)
        elif msg.split(' ')[0] == '>>sendfile<<':
            lenFile = os.stat('files/' + msg.split(' ')[1]).st_size
            sendMsg(2, msg[13:], lenFile)
            time.sleep(2)
            with open('files/' + msg.split(' ')[1], 'rb') as f:
                d = f.read(4096)
                while d != b'':
                    s.send(d)
                    d = f.read(4096)
        else:
            sendMsg(3, msg)
    else:
        exit()

s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
user = ''
usernameApproved = False
s.connect(('localhost', 55555))
thread = threading.Thread(target=read_s)
thread.start()

while True:
    msg = input()
    sendPacket(msg)
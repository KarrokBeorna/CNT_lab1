import socket
import threading
import time
import os
import shutil

lenMsg = 0
filename = ''
def read_s():
    global usernameApproved, s, user, lenMsg, filename
    while True:
        buffer = ''
        try:
            data = s.recv(1024)
            if len(data) > 4:
                if data[0] == 0xaa and data[1] == 0xbb and data[2] == 0xcc:
                    i = 1
                    while data[i] != 0xaa:
                        i += 1
                    lenMsg = int(data[4:i].decode('utf8'))
                    if data[i+3] == 3:
                        buffer += data[i+4:].decode('utf8')
                        lenMsg -= 1024
                        while lenMsg > 0:
                            data = s.recv(1024)
                            buffer += data.decode('utf8')
                            lenMsg -= 1024
                    if data[i+3] == 6:
                        filename = data[i+4:].decode('utf8')
                    if data[i+3] == 5: # примем размер файла в байтах
                        lenFile = int(data[i+4:].decode('utf8'))
                        with open('files' + user + '/' + filename, 'wb') as f:
                            time.sleep(1)
                            while lenFile > 0:
                                datafile = s.recv(4096)
                                f.write(datafile)
                                lenFile -= 4096
        except ConnectionAbortedError:
            shutil.rmtree('files' + user, ignore_errors=True)
            s.close()
            break
        else:
            if buffer != '':
                if buffer[0:20] == 'Вы подключены к чату':
                    usernameApproved = True
                print(buffer)

def createPacket(type, msg):
    byteType = b'\xFF'
    if type == 0:           # приветствие c именем пользователя и временным отклонением от UTC
        byteType = b'\x00'
    elif type == 1:         # выход
        byteType = b'\x01'
    elif type == 2:         # сообщение с файлом
        byteType = b'\x02'
    elif type == 3:         # сообщение без файла
        byteType = b'\x03'
    elif type == 4:         # длина пакета
        byteType = b'\x04'
    elif type == 5:         # размер файла
        byteType = b'\x05'
    elif type == 6:         # имя файла
        byteType = b'\x06'
    return (b'\xAA\xBB\xCC' + byteType + msg.encode('utf8'))

def sendMsg(type, msg):
    global s
    bytesMsg = createPacket(type, msg)
    lenMsg = createPacket(4, str(len(bytesMsg)))
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
        elif msg.split(' ')[0] == '>>sendfile<<':
            if len(msg.split(' ')) > 2:
                sendMsg(2, msg)
            else:
                sendMsg(6, msg)
            time.sleep(2)
            with open('files/' + msg.split(' ')[1], 'rb') as f:
                lenFile = os.stat('files/' + msg.split(' ')[1]).st_size
                sendMsg(5, str(lenFile))
                time.sleep(2)
                d = f.read(4096)
                while d != b'':
                    s.send(d)
                    d = f.read(4096)
            print('Файл ' + msg.split(' ')[1] + ' отправлен')
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
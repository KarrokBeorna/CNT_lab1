import socket
import threading
import time

def hmTime(offset):
    timeSec = (int(time.time()) + offset) % 86400
    hours = int(timeSec / 3600 % 24)
    minutes = int(timeSec % 3600 / 60)
    return '<' + '%.2d' % hours + ':' + '%.2d' % minutes + '> '

def deleteUser(index, clientsocket):
    global sockets, users
    user = users[index]
    if user != '':
        sendMsg(clientsocket, 'Пользователь ' + user + ' покинул чат')
        print(hmTime(-time.timezone) + 'Пользователь ' + user + ' покинул чат')
    del users[index]
    del sockets[clientsocket]
    clientsocket.close()

def createPacket(type, msg):
    byteType = b'\xFF'
    if type == 3:           # простые сообщения
        byteType = b'\x03'
    elif type == 4:         # длина пакета
        byteType = b'\x04'
    elif type == 5:         # размер файла
        byteType = b'\x05'
    elif type == 6:         # имя файла
        byteType = b'\x06'
    return (b'\xAA\xBB\xCC' + byteType + msg.encode('utf8'))

def sendFile(clientsocket, datafile, size=False, name=False):
    global sockets, users
    if size or name:
        type = 0
        if size:
            type = 5
        else:
            type = 6
        for socket in sockets.keys():
            if clientsocket != socket and sockets[socket] != 1 and sockets[clientsocket] != 1:
                miniSendMsg(type, datafile, socket)
    else:
        for socket in sockets.keys():
            if clientsocket != socket and sockets[socket] != 1 and sockets[clientsocket] != 1:
                socket.send(datafile)

def sendMsg(clientsocket, msg, serverResponse=False):
    global sockets, users
    if serverResponse:
        miniSendMsg(3, msg, clientsocket)
    else:
        for socket in sockets.keys():
            if clientsocket != socket and sockets[socket] != 1 and sockets[clientsocket] != 1:
                miniSendMsg(3, hmTime(sockets[socket]) + msg, socket)

def miniSendMsg(type, msg, socket):
    bytesMsg = createPacket(type, msg)
    lenMsg = createPacket(4, str(len(bytesMsg)))
    socket.send(lenMsg + bytesMsg)

def handle_client(clientsocket):
    global sockets, users
    lenMsg = 0
    filename = ''
    while clientsocket in sockets.keys():
        buffer = ''
        try:
            data = clientsocket.recv(1024)
            if len(data) > 8:
                if data[0] == 0xaa and data[1] == 0xbb and data[2] == 0xcc:
                    i = 1
                    while data[i] != 0xaa:
                        i += 1
                    lenMsg = int(data[4:i].decode('utf8'))
                    print(lenMsg)
                    if data[i+3] == 0 or data[i+3] == 3:
                        if data[i+3] == 3:
                            buffer += '[' + users[list(sockets.keys()).index(clientsocket)] + '] '
                        buffer += data[i+4:].decode('utf8')
                        lenMsg -= 1024
                        while lenMsg > 0:
                            data = clientsocket.recv(1024)
                            buffer += data.decode('utf8')
                            lenMsg -= 1024
                        sendMsg(clientsocket,  buffer)
                    elif data[i+3] == 1:
                        deleteUser(list(sockets.keys()).index(clientsocket), clientsocket)
                    elif data[i+3] == 2:
                        filename = data[i+4:].decode('utf8').split(' ')[1]
                        sendFile(clientsocket, filename, name=True)
                        buffer += data[(i+17 + len(filename) + 1):].decode('utf8')
                        lenMsg -= 1024
                        while lenMsg > 0:
                            data = clientsocket.recv(1024)
                            buffer += data.decode('utf8')
                            lenMsg -= 1024
                        sendMsg(clientsocket, '[' + users[list(sockets.keys()).index(clientsocket)] + '] ' + buffer)
                    elif data[i+3] == 6:
                        filename = data[i+4:].decode('utf8').split(' ')[1]
                        sendFile(clientsocket, filename, name=True)
                    elif data[i+3] == 5:
                        lenFile = int(data[i+4:].decode('utf8'))
                        time.sleep(1)
                        sendFile(clientsocket, str(lenFile), True)
                        time.sleep(1)
                        while lenFile > 0:
                            datafile = clientsocket.recv(4096)
                            sendFile(clientsocket, datafile)
                            lenFile = lenFile - 4096
                        sendMsg(clientsocket, 'Пользователь ' + users[list(sockets.keys()).index(clientsocket)] +
                                ' отправил файл ' + filename)
        except ConnectionResetError:
            deleteUser(list(sockets.keys()).index(clientsocket), clientsocket)
        else:
            if buffer != '':
                if sockets[clientsocket] == 1:
                    newUser, timezone = buffer.split(' ')
                    if newUser not in users:
                        sockets[clientsocket] = int(timezone)
                        users[list(sockets.keys()).index(clientsocket)] = newUser
                        sendMsg(clientsocket, 'Вы подключены к чату \nДля выхода из чата напишите >>exit<< \n'
                                              'Для отправки файла используйте \'>>sendfile<< имя файла\' \n'
                                              'Файлы должны располагаться в директории скрипта, в папке files \n'
                                              'В названиях файлов не должно быть пробелов', True)
                        sendMsg(clientsocket, newUser + ' подключился к чату')
                    else:
                        sendMsg(clientsocket, 'Данное имя пользователя уже используется \nВведите другое имя пользователя:', True)

                if clientsocket in sockets:
                    if sockets[clientsocket] != 1:
                        print(hmTime(-time.timezone) + buffer)


serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
serversocket.bind(('', 55555))
serversocket.listen(100)
sockets = {}
users = []

while True:
    clientsocket, address = serversocket.accept()
    print('Connected by', address)

    if clientsocket not in sockets:
        sockets[clientsocket] = 1
        users.append('')
        sendMsg(clientsocket, 'Введите имя пользователя:',True)

    client_handler = threading.Thread(target=handle_client, args=(clientsocket, ))
    client_handler.start()
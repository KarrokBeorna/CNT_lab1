import socket
import threading
import time
import select
import errno

def hmTime(offset):
    timeSec = (int(time.time()) + offset) % 86400
    hours = int(timeSec / 3600 % 24)
    minutes = int(timeSec % 3600 / 60)
    return '<' + '%.2d' % hours + ':' + '%.2d' % minutes + '> '

def deleteUser(index, clientsocket):
    global sockets, users, readers, writers
    if clientsocket in readers:
        readers.remove(clientsocket)
    if clientsocket in writers:
        writers.remove(clientsocket)
    user = users[index]
    if user != '':
        sendMsg(clientsocket, b'\x03' + ('User ' + user + ' disconnected').encode('utf8'))
    del users[index]
    del sockets[clientsocket]

def sendFile(clientsocket, datafile):
    global sockets, users
    for socket in sockets.keys():
        if clientsocket != socket and sockets[socket] != 1 and sockets[clientsocket] != 1:
            while True:
                try:
                    socket.send(datafile)
                except BlockingIOError:
                    continue
                else:
                    break

def sendMsg(clientsocket, msg, serverResponse=False):
    global sockets, users
    if serverResponse:
        clientsocket.send(len(msg).to_bytes(2, 'big') + msg)
    else:
        for socket in sockets.keys():
            if clientsocket != socket and sockets[socket] != 1 and sockets[clientsocket] != 1:
                timeMsg = msg[0].to_bytes(1,'big') + (hmTime(sockets[socket])).encode('utf8') + msg[1:]
                while True:
                    try:
                        socket.send(len(timeMsg).to_bytes(2, 'big') + timeMsg)
                    except BlockingIOError:
                        continue
                    else:
                        break

def handle_client(clientsocket):
    global sockets, users, readers, writers
    lenMsg = 0
    if clientsocket not in sockets:
        sockets[clientsocket] = 1
        users.append('')
    buffer = b''
    try:
        data = clientsocket.recv(1024)
    except BlockingIOError:
        if clientsocket in readers:
            readers.remove(clientsocket)
        if clientsocket in writers:
            writers.remove(clientsocket)
    except Exception:
        deleteUser(list(sockets.keys()).index(clientsocket), clientsocket)
        clientsocket.close()
    else:
        if len(data) > 2:
            if clientsocket not in writers:
                writers.append(clientsocket)
            lenMsg = int.from_bytes(data[:2], 'big')
            if data[2] == 0 or data[2] == 2 or data[2] == 3:
                if data[2] == 2 or data[2] == 3:
                    if data[2] == 2:
                        buffer = b'\x02' + ('[' + users[list(sockets.keys()).index(clientsocket)] + ']').encode('utf8') + b'\xff'
                    else:
                        buffer = b'\x03' + ('[' + users[list(sockets.keys()).index(clientsocket)] + '] ').encode('utf8')
                buffer += data[3:]
                lenMsg -= 1022
                while lenMsg > 0:
                    data = clientsocket.recv(1024)
                    buffer += data
                    lenMsg -= 1024
                sendMsg(clientsocket,  buffer)

                if data[2] == 2:
                    lenFile = int.from_bytes(data[3:7], 'big')
                    split = data[7:].decode('utf8').split(' ')
                    if len(split) < 2:
                        filename = split[0]
                    else:
                        filename = split[0]
                    while lenFile > 0:
                        try:
                            datafile = clientsocket.recv(4096)
                        except BlockingIOError:
                            continue
                        else:
                            sendFile(clientsocket, datafile)
                            lenFile -= 4096
                        print(lenFile)
                    sendMsg(clientsocket, b'\x03' + ('User ' + users[list(sockets.keys()).index(clientsocket)] +
                                           ' uploaded file ' + filename).encode('utf8'))
            elif data[2] == 1:
                deleteUser(list(sockets.keys()).index(clientsocket), clientsocket)
                clientsocket.close()
            elif data[2] == 4:
                user = data[14:].decode('utf8').split(' ')[0]
                if user not in users:
                    sendMsg(clientsocket, b'\x04' + ('Username changed to ' + user).encode('utf8'), True)
                    sendMsg(clientsocket, b'\x03' + ('User [' + users[list(sockets.keys()).index(clientsocket)] +
                                                     '] changed username to [' + user + ']').encode('utf8'))
                    users[list(sockets.keys()).index(clientsocket)] = user
                else:
                    sendMsg(clientsocket, b'\x03' + ('The name is already in use').encode('utf8'), True)
        if buffer != b'':
            if clientsocket in sockets.keys():
                if sockets[clientsocket] == 1:
                    newUser, timezone = buffer.decode('utf8').split(' ')
                    if newUser not in users:
                        sockets[clientsocket] = int(timezone)
                        users[list(sockets.keys()).index(clientsocket)] = newUser
                        sendMsg(clientsocket, b'\x00' + ('Commands: >>exit<<, >>sendfile<< \'filename\', >>chname<< \'name\'').encode('utf8'), True)
                        sendMsg(clientsocket, b'\x03' + (newUser + ' connected').encode('utf8'))
                    else:
                        sendMsg(clientsocket, b'\x03' + ('The name is already in use').encode('utf8'), True)


serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
serversocket.setblocking(0)
serversocket.bind(('', 55555))
serversocket.listen(100)
readers = [serversocket]
writers = []
sockets = {}
users = []

while True:
    read, write, err = select.select(readers, writers, readers)
    for sock in read:
        if sock is serversocket:
            clientsocket, address = serversocket.accept()
            print('Connected by', address)
            clientsocket.setblocking(0)
            readers.append(clientsocket)
        else:
            handle_client(sock)
        print(read, write, err)
        print(readers, writers, sockets)
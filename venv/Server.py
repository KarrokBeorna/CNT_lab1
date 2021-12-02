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
        sendMsg(clientsocket, b'\x03' + ('User ' + user + ' disconnected').encode('utf8'))
    del users[index]
    del sockets[clientsocket]
    clientsocket.close()

def sendFile(clientsocket, datafile):
    global sockets, users
    for socket in sockets.keys():
        if clientsocket != socket and sockets[socket] != 1 and sockets[clientsocket] != 1:
            socket.send(datafile)

def sendMsg(clientsocket, msg, serverResponse=False):
    global sockets, users
    if serverResponse:
        clientsocket.send(len(msg).to_bytes(2, 'big') + msg)
    else:
        for socket in sockets.keys():
            if clientsocket != socket and sockets[socket] != 1 and sockets[clientsocket] != 1:
                timeMsg = msg[0].to_bytes(1,'big') + (hmTime(sockets[socket])).encode('utf8') + msg[1:]
                socket.send(len(timeMsg).to_bytes(2, 'big') + timeMsg)

def handle_client(clientsocket):
    global sockets, users
    lenMsg = 0
    if clientsocket not in sockets:
        sockets[clientsocket] = 1
        users.append('')
    while clientsocket in sockets.keys():
        buffer = b''
        try:
            data = clientsocket.recv(1024)
            if len(data) > 2:
                lenMsg = int.from_bytes(data[:2], 'big')
                if data[2] == 0 or data[2] == 2 or data[2] == 3:
                    if data[2] == 2 or data[2] == 3:
                        if data[2] == 2:
                            buffer = b'\x02' + ('[' + users[list(sockets.keys()).index(clientsocket)] + ']').encode('utf8') + b'\xff'
                        else:
                            buffer = b'\x03' + ('[' + users[list(sockets.keys()).index(clientsocket)] + '] ').encode('utf8')
                    if data[2] == 2:
                        lenFile = int.from_bytes(data[3:7], 'big')
                        split = data[7:].decode('utf8').split(' ')
                        if len(split) < 2:
                            filename = split[0]
                        else:
                            filename = split[0]
                    buffer += data[3:]
                    lenMsg -= 1022
                    while lenMsg > 0:
                        data = clientsocket.recv(1024)
                        buffer += data
                        lenMsg -= 1024
                    sendMsg(clientsocket,  buffer)

                    if data[2] == 2:
                        while lenFile > 0:
                            datafile = clientsocket.recv(4096)
                            sendFile(clientsocket, datafile)
                            lenFile -= 4096

                        sendMsg(clientsocket, b'\x03' + ('User ' + users[list(sockets.keys()).index(clientsocket)] +
                                               ' uploaded file ' + filename).encode('utf8'))
                elif data[2] == 1:
                    deleteUser(list(sockets.keys()).index(clientsocket), clientsocket)
                elif data[2] == 4:
                    user = data[14:].decode('utf8').split(' ')[0]
                    if user not in users:
                        sendMsg(clientsocket, b'\x04' + ('Username changed to ' + user).encode('utf8'), True)
                        sendMsg(clientsocket, b'\x03' + ('User [' + users[list(sockets.keys()).index(clientsocket)] +
                                                         '] changed username to [' + user + ']').encode('utf8'))
                        users[list(sockets.keys()).index(clientsocket)] = user
                    else:
                        sendMsg(clientsocket, b'\x03' + ('The name is already in use').encode('utf8'), True)

        except ConnectionResetError:
            deleteUser(list(sockets.keys()).index(clientsocket), clientsocket)
        else:
            if buffer != b'':
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
serversocket.bind(('', 55555))
serversocket.listen(100)
sockets = {}
users = []

while True:
    clientsocket, address = serversocket.accept()
    print('Connected by', address)

    client_handler = threading.Thread(target=handle_client, args=(clientsocket, ))
    client_handler.start()
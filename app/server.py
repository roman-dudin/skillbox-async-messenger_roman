"""
Серверное приложение для соединений
"""
import asyncio
from asyncio import transports


class ClientProtocol(asyncio.Protocol):
    login: str
    server: 'Server'
    transport: transports.Transport
    history = []

    def __init__(self, server: 'Server'):
        self.server = server
        self.login = None

    def data_received(self, data: bytes):
        decoded = data.decode()
        print(decoded)

        if self.login is None:
            # login:User
            if decoded.startswith("login:"):
                new_login = decoded.replace("login:", "").replace("\r\n", "")
                exists = False
                for client in self.server.clients:
                    if client.login == new_login:
                        exists = True
                        break
                if exists:
                    self.transport.write(
                            f"Логин '{new_login}' занят, попробуйте другой".encode())
                    self.transport.close()
                else:
                    self.login = new_login
                    self.send_history(10)
                    self.transport.write(f"Привет, {self.login}!".encode())
                    self.send_to_all(f"Пользователь '{self.login}' подключился")
        else:
            self.save_to_history(self.send_message(decoded))

    def send_message(self, message):
        format_string = f"<{self.login}> {message}"
        self.send_to_all(format_string)

        return format_string

    def send_to_all(self, message):
        for client in self.server.clients:
            if client.login != self.login:
                client.transport.write(message.encode())

    def connection_made(self, transport: transports.Transport):
        self.transport = transport
        self.server.clients.append(self)
        print("Соединение установлено")

    def connection_lost(self, exception):
        self.server.clients.remove(self)
        print("Соединение разорвано")

    def save_to_history(self, message):
        self.history.append(f"{message} \r\n")

    def send_history(self, count):
        l: int = len(self.history)
        if l > 0:
            if l < count:
                count = l
            self.transport.write(f"Last {count} message(s)\r\n".encode())
            self.transport.write("-----------------------\r\n".encode())
            for i in range(-count, 0):
                self.transport.write(self.history[i].encode())
            self.transport.write("-----------------------\r\n".encode())
            self.transport.write(">>> End of history\r\n".encode())


class Server:
    clients: list

    def __init__(self):
        self.clients = []

    def create_protocol(self):
        return ClientProtocol(self)

    async def start(self):
        loop = asyncio.get_running_loop()

        coroutine = await loop.create_server(
            self.create_protocol,
            "127.0.0.1",
            8888
        )

        print("Сервер запущен ...")

        await coroutine.serve_forever()


process = Server()
try:
    asyncio.run(process.start())
except KeyboardInterrupt:
    print("Сервер остановлен вручную")

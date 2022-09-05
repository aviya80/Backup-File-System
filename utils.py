import os

DEBUG = True

def debug(message):
    if DEBUG:
        print(f'DEBUG: {message}')

class Constants:
    def __init__(self):
        self.ACTION_TYPE_FILE = 'ACTION_TYPE_FILE'
        self.ACTION_TYPE_DIR = 'ACTION_TYPE_DIR'
        self.ACTION_DELETE = 'ACTION_DELETE'
        self.ACTION_CREATE = 'ACTION_CREATE'
        self.NO_USER_ID = 'NO_USER_ID'
        self.NO_CLIENT_ID = 'NO_CLIENT_ID'
        self.RECEIVING_UPDATES = 'RECEIVING_UPDATES'
        self.SENDING_UPDATES = 'SENDING_UPDATES'
        self.ACTION_END = 'ACTION_END'

class NetworkHandler:
    def __init__(self, sock, local_dir):
        self.sock = sock
        self.local_dir = local_dir
        self.constants = Constants()

    def set_local_dir(self, path):
        self.local_dir = path

    def recv_fixed_len(self, length):
        ret = b''
        while length > 0:
            data = self.sock.recv(min(length, 512))
            if data:
                length -= len(data)
            else:
                break
            ret += data
        return ret

    def recv_msg_len(self):
        long_byte_length = 8
        msg_len_str = self.recv_fixed_len(long_byte_length)
        msg_len = int.from_bytes(msg_len_str, byteorder='big')
        return msg_len

    def send_number_val(self, val):
        long_byte_length = 8
        val_byte_format = val.to_bytes(long_byte_length, byteorder='big')
        debug(f'sent {val_byte_format}')
        self.sock.sendall(val_byte_format)

    def send_bytes(self, byte_msg):
        length = len(byte_msg)
        self.send_number_val(length)
        self.sock.sendall(byte_msg)
        debug(f'sent {byte_msg}')

    def send_msg(self, str_msg):
        self.send_bytes(str_msg.encode('utf-8'))

    def recv_msg(self):
        length = self.recv_msg_len()
        debug(f'received {length}')
        msg_bytes = self.recv_fixed_len(length)
        msg = msg_bytes.decode()
        debug(f'received {msg}')
        return msg

    def send_file(self, path):
        inside_path = os.path.relpath(path, self.local_dir)
        self.send_msg(inside_path)
        size = os.path.getsize(path)
        self.send_number_val(size)
        debug(f'send_file {size} {inside_path}')
        file = open(path, 'rb')
        while size > 0:
            data = file.read(512)
            if data:
                size -= len(data)
                self.sock.sendall(data)
            else:
                break
        file.close()

    def recv_file(self):
        inside_path = self.recv_msg()
        file_size = self.recv_msg_len()
        full_path = os.path.join(self.local_dir, inside_path)
        containing_dir = os.path.dirname(full_path)
        os.makedirs(containing_dir, exist_ok=True)
        debug(f'receive_file {file_size} {full_path}')
        file = open(full_path, 'wb')
        while file_size > 0:
            data = self.sock.recv(min(file_size, 512))
            if data:
                file_size -= len(data)
                file.write(data)
            else:
                break
        file.close()

    def send_dir(self, dir_path):
        inside_path = os.path.relpath(dir_path, self.local_dir)
        self.send_msg(inside_path)
        for subdir, _, files in os.walk(dir_path):
            for file in files:
                self.send_msg(self.constants.ACTION_TYPE_FILE)
                file_path = os.path.join(subdir, file)
                self.send_file(file_path)
        self.send_msg(self.constants.ACTION_END)

    def recv_dir(self):
        dir_path = self.recv_msg()
        full_path = os.path.join(self.local_dir, dir_path)
        os.makedirs(full_path, exist_ok=True)
        stop = False
        while not stop:
            msg = self.recv_msg()
            if msg != self.constants.ACTION_END:
                self.recv_file()
            else:
                stop = True

    def rm_dir(self, dir_path):
        for subdir, _, files in os.walk(dir_path, topdown=False):
            for file in files:
                file_path = os.path.join(subdir, file)
                os.remove(file_path)
            os.rmdir(subdir)

    def rm(self, full_path):
        is_dir = os.path.isdir(full_path)
        if os.path.exists(full_path):
            if is_dir:
                self.rm_dir(full_path)
            else:
                os.remove(full_path)

    def handle_update(self, action, action_type, path):
        if action == self.constants.ACTION_CREATE:
            if action_type == self.constants.ACTION_TYPE_DIR:
                self.recv_dir()
            else:
                self.recv_file()
        else:
            self.rm(path)

    def recv_events(self):
        events = []
        debug(f'receiving events')
        stop = False
        while not stop:
            msg = self.recv_msg()
            debug(f'receive_events="{msg}"')
            if msg != self.constants.ACTION_END:
                action, action_type, path = msg.split(' ', 2)
                events.append([action, action_type, path])
                full_path = os.path.join(self.local_dir, path)
                self.handle_update(action, action_type, full_path)
            else:
                stop = True
        return events

    def send_events(self, events):
        debug(f'sending {len(events)} updates')
        for event in events:
            event_str = ' '.join(event)
            self.send_msg(event_str)
            action, action_type, path = event
            full_path = os.path.join(self.local_dir, path)
            if action == self.constants.ACTION_CREATE:
                if action_type == self.constants.ACTION_TYPE_DIR:
                    self.send_dir(full_path)
                else:
                    self.send_file(full_path)
        self.send_msg(self.constants.ACTION_END)

    def close(self):
        self.sock.close()
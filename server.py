import socket
import sys
import random
import string
import os
from utils import Constants
from utils import NetworkHandler

enable_debug = sys.argv[-1] == 'DEBUG'

def debug(message):
    if enable_debug:
        print(f'DEBUG: {message}')

class Server:
    def __init__(self):
        self.port = int(sys.argv[1])
        self.local_dir = './cloud'
        os.makedirs(self.local_dir, exist_ok=True)
        self.client_dirs = {}
        self.constants = Constants()
    
    def get_ids(self, net_handler):
        user_id = net_handler.recv_msg()
        client_id = net_handler.recv_msg()
        return user_id, client_id

    def get_client_dir(self, user_id):
        return os.path.join(self.local_dir, user_id)

    def send_user_dir(self, ids):
        user_id, client_id = ids
        tasks = self.client_dirs[user_id][client_id]
        tasks.append([self.constants.ACTION_CREATE, self.constants.ACTION_TYPE_DIR, ''])

    def should_send_dir(self, ids):
        user_id, client_id = ids
        return self.has_user_id(user_id) and not self.has_client_id(client_id)

    def create_new_user_id(self):
        size = 128
        characters = string.ascii_lowercase + string.ascii_uppercase + string.digits
        random_list = random.choices(characters, k=size)
        return ''.join(random_list)

    def fill_missing_ids(self, net_handler, ids):
        user_id, client_id = ids
        if not self.has_user_id(user_id):
            user_id = self.create_new_user_id()
            net_handler.send_msg(user_id)
        self.init_user_entry(user_id)
        if not self.has_client_id(client_id):
            user_dict = self.client_dirs[user_id]
            size = len(user_dict)
            client_id = str(size)
            net_handler.send_msg(client_id)
        self.init_client_entry(user_id, client_id)
        return user_id, client_id

    def init_user_entry(self, user_id):
        if user_id not in self.client_dirs:
            self.client_dirs[user_id] = {}

    def init_client_entry(self, user_id, client_id):
        if client_id not in self.client_dirs[user_id]:
            self.client_dirs[user_id][client_id] = []
 
    def has_user_id(self, user_id):
        return user_id != self.constants.NO_USER_ID

    def has_client_id(self, client_id):
        return client_id != self.constants.NO_CLIENT_ID

    def start_receiving_clients(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(('', self.port))
            sock.listen()
            while True:
                client, addr = sock.accept()
                net_handler = NetworkHandler(client, self.local_dir)
                debug(f'Accepted: {addr}')
                self.handle_client(net_handler)
                net_handler.close()
                debug(f'Closed: {addr}')
    
    def add_events_to_all_pcs(self, ids, events):
        user_id, client_id = ids
        user_pcs = self.client_dirs[user_id]
        client_ids = [pc for pc in user_pcs if pc != client_id]
        for client_id in client_ids:
            user_pcs[client_id].extend(events)

    def handle_client_tasks(self, net_handler, ids):
        user_id, client_id = ids
        stop = False
        while not stop:
            task = net_handler.recv_msg()
            if task == self.constants.SENDING_UPDATES:
                events = net_handler.recv_events()
                debug(f'SUPPLY: {events}')
                self.add_events_to_all_pcs(ids, events)
            elif task == self.constants.RECEIVING_UPDATES:
                pc_tasks = self.client_dirs[user_id][client_id]
                debug(f'REQUEST: {pc_tasks}')
                net_handler.send_events(pc_tasks)
                pc_tasks.clear()
            else:
                stop = True    
    
    def handle_client(self, net_handler):
        ids = self.get_ids(net_handler)
        dir_required = self.should_send_dir(ids)
        ids = self.fill_missing_ids(net_handler, ids)

        client_dir = self.get_client_dir(ids[0])
        net_handler.set_local_dir(client_dir)

        debug(f'IDs:\n{ids}')
        if dir_required:
            self.send_user_dir(ids)
            debug(f'Sent initial dir')
        
        print(ids[0])

        self.handle_client_tasks(net_handler, ids)

try:    
    server = Server()
    server.start_receiving_clients()
except KeyboardInterrupt:
    pass

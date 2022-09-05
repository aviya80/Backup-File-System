from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import sys
import os
import socket
import time
from utils import Constants
from utils import NetworkHandler

enable_debug = sys.argv[-1] == 'DEBUG'
if enable_debug:
    sys.argv = sys.argv[:-1]

def debug(message):
    if enable_debug:
        print(f'DEBUG: {message}')

class Watchdog(FileSystemEventHandler):
    def __init__(self, local_dir):
        self.should_listen_for_updates = True
        self.local_dir = local_dir
        self.events = []
        self.observer = Observer()
        self.observer.schedule(self, self.local_dir, recursive=True)
        self.observer.start()
        self.constants = Constants()

    def set_update_state(self, state):
        self.should_listen_for_updates = state

    def add_event(self, event_type, is_dir, src):
        if not self.should_listen_for_updates:
            return
        action_type = self.constants.ACTION_TYPE_FILE
        if is_dir:
            action_type = self.constants.ACTION_TYPE_DIR
        inside_path = os.path.relpath(src, self.local_dir)
        debug(f'type={event_type} {action_type} src={inside_path}')
        self.events.append([event_type, action_type, inside_path])
        
    def has_events(self):
        return len(self.events) > 0

    def on_created(self, event):
        self.add_event(self.constants.ACTION_CREATE, event.is_directory, event.src_path)

    def on_deleted(self, event):
        self.add_event(self.constants.ACTION_DELETE, event.is_directory, event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self.add_event(self.constants.ACTION_DELETE, event.is_directory, event.src_path)
            self.add_event(self.constants.ACTION_CREATE, event.is_directory, event.src_path)

    def on_moved(self, event):
        self.add_event(self.constants.ACTION_CREATE, event.is_directory, event.dest_path)
        self.add_event(self.constants.ACTION_DELETE, event.is_directory, event.src_path)
        
    def fetch_events(self):
        ret = self.events.copy()
        self.events.clear()
        return ret

    def finish(self):
        self.observer.stop()
        self.observer.join()

class Client:
    def __init__(self):
        self.ip, self.port, self.local_dir, self.connection_delay = sys.argv[1:5]
        self.port = int(self.port)
        self.connection_delay = float(self.connection_delay)
        os.makedirs(self.local_dir, exist_ok=True)
        self.constants = Constants()
        self.user_id = self.constants.NO_USER_ID
        if len(sys.argv) > 5:
            self.user_id = sys.argv[5]
        self.client_id = self.constants.NO_CLIENT_ID
        self.watchdog = Watchdog(self.local_dir)
        
    def has_user_id(self):
        return self.user_id != self.constants.NO_USER_ID

    def has_client_id(self):
        return self.client_id != self.constants.NO_CLIENT_ID

    def start_communication(self, net_handler):
        net_handler.send_msg(self.user_id)
        net_handler.send_msg(self.client_id)

    def finish_communication(self, net_handler):
        net_handler.send_msg(self.constants.ACTION_END)
        net_handler.close()

    def send_events(self, net_handler):
        if self.watchdog.has_events():
            events = self.watchdog.fetch_events()
            net_handler.send_msg(self.constants.SENDING_UPDATES)
            net_handler.send_events(events)

    def receive_events(self, net_handler):
        self.watchdog.set_update_state(False)
        net_handler.send_msg(self.constants.RECEIVING_UPDATES)
        net_handler.recv_events()
        self.watchdog.set_update_state(True)

    def fill_missing_ids(self, net_handler):
        if not self.has_user_id():
            self.user_id = net_handler.recv_msg()
            self.watchdog.add_event(self.constants.ACTION_CREATE, self.constants.ACTION_TYPE_DIR, self.local_dir)
        if not self.has_client_id():
            self.client_id = net_handler.recv_msg()

    def communication_round(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((self.ip, self.port))
            net_handler = NetworkHandler(sock, self.local_dir)
            debug('start_communication')
            self.start_communication(net_handler)
            debug('fill_missing_ids')
            self.fill_missing_ids(net_handler)
            debug('send_events')
            self.send_events(net_handler)
            debug('receive_events')
            self.receive_events(net_handler)
            debug('finish_communication')
            self.finish_communication(net_handler)

    def finish(self):
        self.watchdog.finish()

    def loop(self):
        while True:
            self.communication_round()
            time.sleep(self.connection_delay)

client = Client()
try:
    client.loop()
except KeyboardInterrupt:
    client.finish()

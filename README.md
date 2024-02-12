# Backup-File-System

## Introduction
This project consists of two Python scripts: `client.py` and `server.py`. It is a system designed for monitoring and managing file updates between a client and a server in a distributed environment. The client script monitors local file system events using the Watchdog library and sends updates to the server. The server script receives these updates and propagates them to other connected clients.

## Client (client.py)
The `client.py` script is responsible for monitoring local directories for file system events such as file creations, deletions, and modifications. It establishes a connection with the server and sends these events for synchronization. The main functionalities of the client script include:
- Monitoring local directories using Watchdog library.
- Establishing a TCP connection with the server.
- Sending file system events to the server for synchronization.

## Server (server.py)
The `server.py` script acts as a central coordinator for file synchronization among multiple clients. It listens for incoming connections from clients, receives file system events, and distributes them to other connected clients. The main functionalities of the server script include:
- Listening for incoming client connections on a specified port.
- Receiving file system events from connected clients.
- Propagating received events to other connected clients for synchronization.

## Dependencies
Both scripts rely on the following dependencies:
- Watchdog: Used for monitoring file system events in the client script.
- Socket: Used for establishing TCP connections between the client and server.
- OS: Used for handling file system operations such as file creation, deletion, and modification.
- Utils: Contains utility functions and constants used by both client and server scripts.

## Usage
To use the Anomaly Detector System:
1. Run the `server.py` script on a designated server machine.
2. Run the `client.py` script on client machines that need to synchronize files with the server.
3. The client script will monitor local directories for file system events and send updates to the server.
4. The server script will receive these updates and distribute them to other connected clients for synchronization.

## Note
Make sure to set up the server IP address and port in the `client.py` script and specify the server port in the `server.py` script before running them.


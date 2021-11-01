# Server Server

The Server Server is an application to create, control, interact, and host multiple game servers 
from different games all through a single application.

![mine raft](https://i.ytimg.com/vi/Kwwl9jiJ1A4/maxresdefault.jpg)

## Server Server Guiding Guide

### Commands
The main way to interact with the Server Server is through commands within its own console 
or by connecting to it through the client application.

The main way to interact with the Server Server is through commands within its own console 
or by connecting to it through the client application. Commands can be defined in two different places.
The first place is in the base scope and that is within the ControllerManager.py file. The second place is
in the Controller files themselves. For example within the minecraft.py file. 

The base functions are intended to be
general functions that are needed for the Server Server to have core functionality. The commands within the Controller files
are intended to be used to control and interact with that specific Controller and its servers that it is hosting which is 
expanded upon in the "Controllers and Servers" section.

A few base commands include:
 - create_server
 - remove_server
 - list_servers
 - start_server

A list of all commands can be viewed by using the "commands" command and command 
info can be found by using the "help" command. Example:

    help create_server 

Commands in the server are just python functions and can be easily changed/added and reloaded 
without needing to restart the application

### Controllers and Servers

### Scope
What commands are available to the user depend on the users scope.
A users scope by default is the base scope. Meaning they can only execute commands 
in the base scope and not commands added from the different Controllers.

## Command List
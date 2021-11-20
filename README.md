# Server Server

The Server Server is an application to create, control, interact, and host multiple game servers 
from different games all through a single application.

## Server Server Guiding Guide

### Quickstart
In order to setup the ServerServer all that is required is to have a python 3 installation. 
Just download the code and it will run with the default config settings.
With the default config settings, the ServerServer's ip will be 127.0.0.1 and it will not attempt to do any automated routing.

All you need to do now is to create and start a server. To do this just use the "create_server" command and then the "start" command.
For example to create and start a Minecraft server of the most recent version you would use these commands:

    create_server Minecraft serverName
    
    start Minecraft serverName

Stopping the servers is simple. Just use the "stop" command:

    stop Minecraft serverName

To shutdown the Server Server just use the "shutdown" command:

    shutdown


### Commands
The main way to interact with the Server Server is through commands within its own console 
or by connecting to it through the client application.

The main way to interact with the Server Server is through commands within its own console 
or by connecting to it through the client application. Commands can be defined in two different places.
The first place is in the base scope and that is within the ControllerManager.py file. The second place is
in the Controller files themselves. For example within the minecraft.py file. 

The base functions are intended to be general functions that are needed for the Server Server to have core functionality. 
The commands within the Controller files are intended to be used to control and interact with that specific Controller 
and its servers that it is hosting which is expanded upon in the "Focus" section.

A few base commands include:
 - create_server
 - remove_server
 - list_servers
 - start
 - stop
 - shutdown

A list of all commands can be viewed by using the "commands" command and command 
info can be found by using the "help" command. Example:

    help create_server 

Commands in the server are just python functions and can be easily changed/added and reloaded 
without needing to restart the application

### Controllers and Servers

#### Controllers
Controllers refer to the class that is within the controller file.
"Controller" refers to the class that acts as an intermediary between the game server and the Server Server itself 
by implementing functions defined by the base controller it inherits from.
It is in charge of defining commands that can be used for itself and creating instances of servers.
Think of this as a factory that creates the servers
#### Servers
Servers refer to an instance of the controller class.
This is the wrapper for the game server itself and handles the IO between the Server Server and the game server

Servers can be created and by using the create_server and command. 
This command take in the Controller being used to create the server, the name of the new server and 
any arguments to be passed to the controller depending in the controller itself

    ->create_server Controller Server_Name *args

Servers can be removed with a similar command:

    -> remove_server Controller Server

Servers can be started and stopped with the "start" and "stop" commands:

    ->start Controller Server
    ->stop Controller Server

### Scope
What commands are available to the user depend on the users scope.
A users scope by default is the base scope. Meaning they can only execute commands 
in the base scope and not commands added from the different Controllers.

There are two ways to execute a command in a specific scope. 

The first way is to specify the scope in front of the command.
The scope can be the scope of a Controller or it can be the scope of a Server that is a member
of a Controller
    
    ->/Controller/Server:command
    ->/Controller:command
    
The second way to specify the scope of a command is to focus onto a specific scope.
When focused on a scope, every command entered is entered within that scope and any output from 
something not in that scope is not displayed. This can be done to focus on a Controller or just a specific server.
    
    ->focus Controller
    ->focus Controller Servers
To un-focus back to the base scope just use the "unfocus" command.

### Filtering
Filtering is similar to focusing on a scope because it limits the output of servers to the user.
Filtering can be used whitelist or blacklist certain Servers/Controllers.
Filtering can be enables and disabled as follows:

    ->filter on
    ->filter off
To set how the filter effects a Controller/Server that is not specified within the filter use the "default" argument as follows:
    
    ->filter default on
    ->filter default off
To add an entry to the filter use the "allow" or "disallow" arguments. Entries can be created for a Controller or a Server.
If an entry exists for both a Controller and a specific Server. The entry corresponding to the server will be used.
    
    //Allow entry
    ->filter allow Controller
    ->filter allow Controller Server
    
    //Disallow entry
    ->filter disallow Controller
    ->filter disallow Controller Server
Other arguments for the filter command include
 - view: lists all entries in the filter
 - reset: removes all entries in the filter

## Command List

### help

### commands

### status

### filter

### clear

### message

### shout

### shutdown

### focus

### un_focus

### set_permission

### reset_password

### get_permissions

### create_user

### remove_user

### list_users

### load_controllers

### get_controllers

### reload_controllers

### reload_controller

### reload_manager

### create_server

### remove_server

### save_servers

### list_servers

### server_info

### start

### setup

### stop
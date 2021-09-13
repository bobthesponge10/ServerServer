import os
import discord

TOKEN = "MjQxOTQ3MjI2NzQ0Njg0NTQ1.WBTA6g.lau4o_z20zg71MWwzEUUI9WrAFg"

client = discord.Client()


@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')


@client.event
async def on_message(message):
    if message.author == client.user:
        return


client.run(TOKEN)

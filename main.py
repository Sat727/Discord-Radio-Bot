from discord import app_commands
import discord, sqlite3
import yt_dlp as yt
from discord.ext import commands
from discord.ext.commands import has_permissions, MissingPermissions, HybridCommand
import asyncio
import os
import re
import random
from requests import get
from pprint import pprint
from pathlib import Path
#import threading
#import subprocess


database = sqlite3.connect("db/radio.db")
db = database.cursor()
db.execute("CREATE TABLE IF NOT EXISTS radios (ownerid, radio, private, path)")
class aclient(discord.Client):
    def __init__(self):
        super().__init__(command_prefix='!', intents=discord.Intents.all())
        self.synced = False
        self.servers = {}
        self.bot = discord
        
    async def on_ready(self):
        print('Logged in')
        print(self.guilds)
        #await tree.sync() # Should never need to unhash unless syncing fir first time
        for i in self.guilds:
            self.servers[i.id] = {'Host': None, 'Expires': 300, 'VoiceData': None, 'LastPlayed': None, 'Radio': None}
        print(self.servers)
        await self.wait_until_ready()

    

client = aclient()
tree = app_commands.CommandTree(client)

@tree.command(name= 'join', description= "Joins a voice channel and plays the given radio")
async def command(interaction: discord.Interaction, radio:str):
    data = db.execute("SELECT * FROM radios WHERE radio = ?", (radio,)).fetchall()
    if radio not in [i[1] for i in data if i[0] == interaction.user.id or i[2] != 1]:
        await interaction.response.send_message("This radio does not exist, or is private")
        return
    print([i[0] for i in data])
    if interaction.user.id in [i[0] for i in data]:
        path = f"./{interaction.user.id}/{radio}/"
    else:
        path = f"./{data[0][0]}/{radio}/"
    print(path)
    def cleandata():
        client.servers[interaction.guild.id]['VoiceData'] = None
        client.servers[interaction.guild.id]['Host'] = None
        client.servers[interaction.guild.id]['Expires'] = 300
        client.servers[interaction.guild.id]['LastPlayed'] = None
        client.servers[interaction.guild.id]['Radio'] = None
    try:
        vc = interaction.user.voice.channel
    except AttributeError:
        await interaction.response.send_message("You are not in a channel")
        return

    if vc:
        message = None
        print(client.voice_clients)
        await interaction.response.send_message(f"Joining {vc.name}")
        player = await vc.connect()
        if client.servers[interaction.guild.id]['Host'] == None:
            client.servers[interaction.guild.id]['Host'] = interaction.user.id
            #try:
            while True:
                if not player.is_playing():
                    if interaction.user.id in [i.id for i in vc.members]:
                        client.servers[interaction.guild.id]['Expires'] = 300
                    async def PickMusic():
                        s= []
                        for (dirpath, dirnames, filenames) in os.walk(path):
                            print(filenames)
                            s.append(filenames)
                        print(s)
                        s = random.choice([i for i in s[0]])
                        if s == client.servers[interaction.guild.id]['LastPlayed'] and len(filenames) >= 2 or s == None:
                            return await PickMusic()
                        else:
                            return s
                    song = await PickMusic()
                    client.servers[interaction.guild.id]['LastPlayed'] = song
                    print(path)
                    print(song)
                    player.play(discord.FFmpegPCMAudio(executable='./ffmpeg.exe', source=path+song))
                    if client.servers[interaction.guild.id]['VoiceData'] == None:
                        client.servers[interaction.guild.id]['VoiceData'] = player
                    ###
                    embed = discord.Embed(title=f"{interaction.user.name}'s Radio", description=f"**Only the host can interact with the bot this session.**\n\nCurrent Song: `{client.servers[interaction.guild.id]['LastPlayed'][:-4]}`\nCurrent Radio: `{client.servers[interaction.guild.id]['Radio']}`")
                    if message == None:
                        message = await interaction.original_response()
                        message = await client.get_channel(interaction.channel.id).fetch_message(message.id)
                    await message.edit(content=None, embed=embed)
                else:
                    if interaction.user.id not in [i.id for i in vc.members]:
                        client.servers[interaction.guild.id]['Expires'] -= 3
                    if client.servers[interaction.guild.id]['Expires'] <= 0:
                        await player.disconnect(), cleandata()
                        return
                    await asyncio.sleep(3)
            #except Exception as e:
            #    await player.disconnect(), cleandata()
            #    print("Unknown error, crashed"), print(e), cleandata()
            #    return False

@tree.command(name="leave",description='Do stuff')
async def leave(interaction:discord.Interaction):
    if client.servers[interaction.guild.id]['Host'] == interaction.user.id:
        await client.servers[interaction.guild.id]['VoiceData'].disconnect()
        await interaction.response.send_message("Disconnected")
        client.servers[interaction.guild.id]['VoiceData'] = None
        client.servers[interaction.guild.id]['Host'] = None
    else:
        await interaction.response.send_message("You are not the host")

@tree.command(name="skip",description='Do stuff')
async def skip(interaction:discord.Interaction):
    if client.servers[interaction.guild.id]['LastPlayed'] == None:
        await interaction.response.send_message("No song playing!")
    if client.servers[interaction.guild.id]['Host'] == interaction.user.id:
        client.servers[interaction.guild.id]['VoiceData'].stop()
        await interaction.response.send_message(f"Skipped {client.servers[interaction.guild.id]['LastPlayed'][:-3]}") #.split('-')[1:][0].replace('_','')}")
    else:
        await interaction.response.send_message("You are not the host")

@tree.command(name='sync', description='Owner only')
async def sync(interaction: discord.Interaction):
    if client.application.owner.id == interaction.user.id:
        await tree.sync()
        print('Command tree synced.')
    else:
        await interaction.response.send_message('You must be the owner of the bot to use this command!')

@tree.command(name='create', description='Create a radio')
async def create(interaction: discord.Interaction, name:str, private:bool):
    if re.compile(r'[a-zA-Z0-9]*$').match(name):
        if name == 'con' or len(name) > 20:
            if len(name) > 20:
                await interaction.response.send_message("Too long of a radio name, please retry")
            else:
                await interaction.response.send_message("Invalid name for radio, or too long")
            return
        data = db.execute("SELECT * FROM radios").fetchall()
        if len([i[0] for i in data if i[0] == interaction.user.id]) >= 5:
            await interaction.response.send_message("You already have the max amount of radios")
            return
        if name in [i[1] for i in data]:
            await interaction.response.send_message("Radio name already taken")
            return
        else:
            if not Path.exists(Path(f'./{interaction.user.id}')):
                os.makedirs(f'{interaction.user.id}')
                os.makedirs(f'{interaction.user.id}/{name}')
            elif not Path.exists(Path(f'./{interaction.user.id}')):
                os.makedirs(f'{interaction.user.id}/{name}')
            else:
                await interaction.response.send_message("That radio already exists. You should not be seeing this message, though. Please contact developer")
                return
            db.execute("INSERT INTO radios (ownerid, radio, private, path) VALUES (?, ?, ?, ?)", (interaction.user.id, name, private, f'./{interaction.user.id}/{name}'))
            database.commit()
            await interaction.response.send_message(f"**Successfully created {name} as a {'private' if private == True else 'public'} radio.**\n\n*Use /radio to add a song to it!*")
    else:
        await interaction.response.send_message("Invalid name for radio")

@app_commands.choices(action=[
        app_commands.Choice(name="Add", value=""),
        app_commands.Choice(name="Remove", value=""),
        ])
@tree.command(name='radio', description='Add/Remove song from radio')
async def radio(interaction: discord.Interaction, radio:str, action:app_commands.Choice[str], song:str):
        data = db.execute("SELECT * FROM radios").fetchall()
        if not Path.exists(Path(f'./{interaction.user.id}/{radio}')) or radio not in [i[1] for i in data if i[0] == interaction.user.id]:
            await interaction.response.send_message("That radio does not exist, or you do not own it")
        else:
            if action.name == 'Add':

                await interaction.response.defer()
                class ButtonView(discord.ui.View):
                    def __init__(self):
                        super().__init__(timeout=None)
                b = ButtonView()
                async def ytfunction(arg:str, download=False, interaction=interaction, ):
                    YDL_OPTIONS = {'format': 'bestaudio', 'noplaylist':'True', 'outtmpl': f'./{interaction.user.id}/{radio}/%(title)s.%(ext)s',
  "forceurl": True,
                   'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '0',
            }],}
                    with yt.YoutubeDL(YDL_OPTIONS) as ydl:

                        entries = []
                        try:
                            get(arg) 
                        except:
                            video = ydl.extract_info(f"ytsearch3:{arg}", download=download)['entries'][0:3]
                            c=1
                            for i in video:
                                if i['duration'] <= 330 and i['duration'] >= 61:
                                    async def downloadmusic(interaction):
                                        b.stop()
                                        await interaction.response.defer()
                                        await interaction.message.edit(view=None)
                                        async def asyncrequest():
                                            loop = asyncio.get_event_loop()
                                            return await loop.run_in_executor(None, ydl.extract_info, (str(list(entries[int(list(interaction.data.values())[0])-1].values())[0][0])), True)
                                        response = await asyncrequest()
                                        message = await interaction.original_response()
                                        message = await client.get_channel(interaction.channel.id).fetch_message(message.id)
                                        await message.edit(content=f"Completed the request to download {response['title']} to {radio}, {interaction.user.mention}",embed=None)
                                    button = discord.ui.Button()
                                    button.label = c
                                    button.custom_id = str(c)
                                    button.callback = downloadmusic
                                    entries.append({i['title']: [i['webpage_url'], i['duration']]})
                                    b.add_item(item=button)
                                    c+=1
                        else:
                            video = ydl.download(arg)
                    return entries

            entries = await ytfunction(arg=song)
            embed = discord.Embed(title="Search Results",description="Up to 3 top searches from the internet, please choose one to add to your radio", color=0x1B00FF)
            c = 1
            for i in entries:
                for key, value in i.items():
                    m, s = divmod(value[1], 60)
                    h, m = divmod(m, 60)
                    embed.add_field(name=f"{c}. {str(key[:50])}" if len(key) >= 30 else str(key), value=f'{f"{m}m" if m > 0 else ""} {f"{s}s" if s > 0 else ""}', inline=False)
                    c+=1
            if not entries:
                await interaction.followup.send("No eligible search results found. All result entries may exceed 5.5 minutes")
            else:
                await interaction.followup.send(embed=embed,view=b)


client.run('')
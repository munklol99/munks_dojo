# Import Dependencies
import discord
from discord.ext import commands
import re
import os
import json
from urllib.parse import quote
from bot_token import DISCORD_TOKEN
from mongo_helpers import create_new_user, delete_user, check_if_user_exists, get_user_data_by_name
from dojo_queue import Queue
import asyncio

bot = commands.Bot(command_prefix = '!', intents=discord.Intents.all())
# CONSTANT: Moderator Role
moderator_role = 1299607805380268082 # All Commands Require the "Moderator" Role.
# CONSTANTS: Channel IDs
registration_channel_id = 1299611607252602961 # Used to find the op.gg link
queue_channel_id = 1299617038846787665
bot_panel_id = 1299652549393256508
# CONSTANTS: Role IDs
registered_role_id = 1299615071131140116
in_queue_role_id = 1299617990513397771
in_game_role_id = 1299620439357788224

active_matches = {}

async def store_match(match):
    """Store the match in the active_matches dictionary."""
    match_id = len(active_matches) + 1  # Generate a unique match ID
    active_matches[match_id] = match
    print(f"Match {match_id} stored.")

channel = bot.get_channel(queue_channel_id)

match_queue = Queue(store_match_callback=store_match)

# Allows me to check if the bot is active in the server
@bot.command()
@commands.has_role(moderator_role)
async def test(ctx):
    await ctx.send("Ready for testing! Fire away. :sunglasses:")

# Wipe last X messages, including the command
@bot.command()
@commands.has_role(moderator_role)
async def wipe(ctx, amount: int):
    # Ensure the amount is positive and reasonable
    if amount <= 0:
        await ctx.send("Please enter a positive number of messages to delete.")
        return

    # Attempt to delete the specified number of messages
    try:
        await ctx.channel.purge(limit=amount)
        print(f"{amount} messages deleted by {ctx.author}.")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")
        print(f"Error deleting messages: {e}")

# Send welcome message with instructions to register
@bot.event
async def on_member_join(member):
    try:
        await member.send(
        f"Welcome {member.display_name}, to the {member.guild.name}! 🎉 We're so glad to have you here.\n\n"
        "Please head over to https://discord.com/channels/1297951377317826570/1297952199187497100 to get your roles assigned in our matchmaking system so you can partipicate in our games!")
        print(f"Sent welcome message to {member.display_name}!")
    except Exception as e:
        print(f"Failed to send DM to {member.display_name}: They probably do not allow direct messages from server members enabled{e}")

#### BEGIN REGISTRATION !!!

# Extract player name from the OP.GG URL
def extract_profile_name(opgg_url):
    match = re.search(r"summoners/[^/]+/(.+)", opgg_url)
    if match:
        return match.group(1).replace('%20', ' ').replace('-', ' #')
    return None

@bot.command()
async def register(ctx):
    if ctx.channel.id != registration_channel_id:
        await ctx.send("Please use the registration channel for this command.")
        return

    await ctx.send(f"{ctx.author.mention}, please insert your OP.GG link!")

    def check(msg):
        return msg.author == ctx.author and msg.channel == ctx.channel

    try:
        msg = await bot.wait_for("message", check=check, timeout=60.0)
        profile_name = extract_profile_name(msg.content)

        if profile_name:
            await ctx.author.edit(nick=profile_name)

            registered_role = ctx.guild.get_role(registered_role_id)
            if registered_role:
                await ctx.author.add_roles(registered_role)

                # Load and update the registration data
                # ctx.author.id is the discord id
                
                create_new_user(disc_username=ctx.author.name, lol_username=profile_name)

                # Save the data and update the leaderboard
                # await save_data(data, bot)

                await ctx.send(f"{ctx.author.mention}, your registration was successful!")
            else:
                await ctx.send("The registered role could not be found.")
        else:
            await ctx.send("Invalid OP.GG link format. Please try again.")
    except discord.Forbidden:
        await ctx.send("I don't have permission to change your nickname or assign roles.")
    except discord.HTTPException as e:
        await ctx.send(f"An error occurred: {e}")
    except TimeoutError:
        await ctx.send("You took too long to respond. Please re-type !register to try again.")

@bot.command()
@commands.has_role(moderator_role)
async def register_remove(ctx, *, discord_name: str):
    """Remove a user's registration and queue data by their Discord name."""
    if ctx.channel.id != bot_panel_id:
        await ctx.send("Please use the bot panel for this command.")
        return

    # Load registration and queue data properly
    result = delete_user(discord_name)
    await ctx.send(result)

    try:
        # Fetch the member using the user ID
        member = discord.utils.get(ctx.guild.members, name=discord_name)

        if member:
            # Remove the registered and in-queue roles
            registered_role = ctx.guild.get_role(registered_role_id)
            in_queue_role = ctx.guild.get_role(in_queue_role_id)

            if registered_role and registered_role in member.roles:
                await member.remove_roles(registered_role)

            if in_queue_role and in_queue_role in member.roles:
                await member.remove_roles(in_queue_role)

            # Reset the user's nickname
            await member.edit(nick=None)

        await ctx.send(f"Registration data for **{discord_name}** has been removed.")

    except discord.NotFound:
        await ctx.send(f"Member **{discord_name}** not found in the guild.")
    except discord.Forbidden:
        await ctx.send("I don't have permission to change nicknames or remove roles.")
    except discord.HTTPException as e:
        await ctx.send(f"An error occurred: {e}")
#### END REGISTRATION !!!

#### BEGIN QUEUE !!!
roles = {"top", "jungle", "mid", "adc", "support"}

# Command: !join {primary role} {secondary role}
@bot.command()
async def join(ctx, primary_role: str = None, secondary_role: str = None):
    if ctx.channel.id != queue_channel_id:
        await ctx.send(f"{ctx.author.mention}, please use the queue channel for this command.")
        return

    if not primary_role or not secondary_role:
        await ctx.send(
            f"{ctx.author.mention}, please try again with the following format:\n\n"
            f"`!join {{primary role}} {{secondary role}}`\n\n"
            f"For example: `!join top support`"
        )
        return

    primary_role = primary_role.lower()
    secondary_role = secondary_role.lower()

    if primary_role not in roles or secondary_role not in roles:
        await ctx.send(f"{ctx.author.mention}, both roles must be one of: {', '.join(roles)}.")
        return

    # # Allow same role only if both are "fill"
    # TODO: Implement Fill option

    # Check if the user is registered before assigning the role
    user_exists = check_if_user_exists(ctx.author.name)
    if not user_exists:
        await ctx.send(f"{ctx.author.mention}, you are not registered. Please register before joining the queue.")
        return

    member_data = get_user_data_by_name(ctx.author.name)
    # Assign the in-queue role only if the user is registered
    queue_role = ctx.guild.get_role(in_queue_role_id)
    if queue_role:
        await ctx.author.add_roles(queue_role)

        player = {
            'discord_id': ctx.author.id,
            'discord_name': member_data["Discord Username"],
            'player_name': member_data["Username"],
            'primary_role': primary_role,
            'secondary_role': secondary_role,
            'elo': member_data['Current ELO']
        }
        await match_queue.enqueue(player)

        await ctx.send(
            f"{ctx.author.mention}, you have joined the queue as **Primary:** {primary_role.capitalize()} "
            f"**/** **Secondary:** {secondary_role.capitalize()}!"
        )
    else:
        await ctx.send("The queue role could not be found.")

# Command: !leave
@bot.command()
async def leave(ctx):
    if ctx.channel.id != queue_channel_id:
        await ctx.send(f"{ctx.author.mention}, please use the queue channel for this command.")
        return

    queue_role = ctx.guild.get_role(in_queue_role_id)
    if queue_role:
        await ctx.author.remove_roles(queue_role)

        await match_queue.leave_queue(ctx.author.name)

        await ctx.send(f"{ctx.author.mention}, you have left the queue.")
    else:
        await ctx.send("The queue role could not be found.")

# Command: !view - View all players in queue
@bot.command()
async def view(ctx):
    if ctx.channel.id != queue_channel_id:
        await ctx.send(f"{ctx.author.mention}, please use the queue channel for this command.")
        return

    if not len(match_queue):
        await ctx.send("The queue is currently empty.")
        return

    message_lines = ["__**Players in Queue:**__"]
    for user_data in match_queue:
        # Create a URL to the player's OP.GG profile
        player_name_url = quote(user_data['player_name'].replace('#', '-'))
        opgg_url = f"https://www.op.gg/summoners/na/{player_name_url}"

        # Add player info with a clickable URL
        message_lines.append(
            f"- **Player:** {user_data['discord_name']} | "
            f"**Primary Role:** {user_data['primary_role'].capitalize()} | "
            f"**Secondary Role:** {user_data['secondary_role'].capitalize()} | "
            f"**ELO:** {user_data['elo']} | **OP.GG:** <{opgg_url}>"
        )

    # Join all message lines into one string and send it
    message = "\n".join(message_lines)
    await ctx.send(message)

@bot.command()
@commands.has_role(moderator_role)
async def remove(ctx, *, discord_name: str):
    # Ensure the command is used in the correct channel
    if ctx.channel.id != bot_panel_id:
        await ctx.send("Please use the bot panel for this command.")
        return

    # Search for the player by their Discord name
    player_to_remove = None
    for user_data in match_queue:
        if user_data['discord_name'].lower() == discord_name.lower():
            player_to_remove = user_data['discord_id']
            break

    await match_queue.leave_queue(discord_name)

    if player_to_remove:
        # Get the member object from the guild using the user ID
        member = ctx.guild.get_member(int(player_to_remove))
        if member:
            # Remove the specified role from the member
            role = ctx.guild.get_role(in_queue_role_id)  # Replace with your role ID
            if role:
                await member.remove_roles(role)
            else:
                await ctx.send("Role not found.")

        await ctx.send(f"Player **{discord_name}** has been removed from the queue.")
    else:
        await ctx.send(f"No player with the name **{discord_name}** found in the queue.")

@bot.command()
async def end_match(ctx):
    if ctx.channel.id != queue_channel_id:
        await ctx.send(f"{ctx.author.mention}, please use the queue channel for this command.")
        return

    await match_queue.end_match()

@bot.command()
async def ready(ctx):
    await match_queue.ready_up(ctx.author.name, ctx.author)

@bot.event
async def on_ready():
    channel = await bot.fetch_channel(queue_channel_id)
    await match_queue.setup(channel, bot)

#### END QUEUE !!!

if __name__ == '__main__':
    async def main():
        print("Starting bot..." )
        # Always the last step
        await bot.start(DISCORD_TOKEN)

    asyncio.run(main())

# if __name__ == '__main__':
#     async def main():
#         await match_queue.enqueue({
#             'player_name': 'con.r',
#             'discord_name': 'con.r',
#             'primary_role': 'Jungle',
#             'secondary_role': 'Mid',
#             'elo': 800,
#             'discord_id': 123456789
#         })
#         await asyncio.sleep(2)
#         await match_queue.enqueue({
#             'player_name': 'munk',
#             'discord_name': 'munk', 
#             'primary_role': 'Jungle',
#             'secondary_role': 'Mid',
#             'elo': 800,
#             'discord_id': 234567890
#         })
#         await asyncio.sleep(2)
#         await match_queue.enqueue({
#             'player_name': 'munk1',
#             'discord_name': 'munk1',
#             'primary_role': 'Jungle', 
#             'secondary_role': 'Mid',
#             'elo': 800,
#             'discord_id': 345678901
#         })
#         await asyncio.sleep(2)
#         await match_queue.enqueue({
#             'player_name': 'munk2',
#             'discord_name': 'munk2',
#             'primary_role': 'Jungle',
#             'secondary_role': 'Mid',
#             'elo': 800,
#             'discord_id': 456789012
#         })
#         await asyncio.sleep(2)
#         await match_queue.enqueue({
#             'player_name': 'munk3',
#             'discord_name': 'munk3',
#             'primary_role': 'Jungle',
#             'secondary_role': 'Mid',
#             'elo': 800,
#             'discord_id': 567890123
#         })
#         await match_queue.enqueue({
#             'player_name': 'munk4',
#             'discord_name': 'munk4',
#             'primary_role': 'Jungle',
#             'secondary_role': 'Mid',
#             'elo': 800,
#             'discord_id': 678901234
#         })
#         await match_queue.enqueue({
#             'player_name': 'munk5',
#             'discord_name': 'munk5',
#             'primary_role': 'Jungle',
#             'secondary_role': 'Mid',
#             'elo': 800,
#             'discord_id': 789012345
#         })
#         await asyncio.sleep(2)
#         await match_queue.enqueue({
#             'player_name': 'munk6',
#             'discord_name': 'munk6',
#             'primary_role': 'Jungle',
#             'secondary_role': 'Mid',
#             'elo': 800,
#             'discord_id': 890123456
#         })
#         await match_queue.enqueue({
#             'player_name': 'munk7',
#             'discord_name': 'munk7',
#             'primary_role': 'Jungle',
#             'secondary_role': 'Mid',
#             'elo': 800,
#             'discord_id': 901234567
#         })
#         await match_queue.enqueue({
#             'player_name': 'munk8',
#             'discord_name': 'munk8',
#             'primary_role': 'Jungle',
#             'secondary_role': 'Mid',
#             'elo': 800,
#             'discord_id': 123456780
#         })
#         await match_queue.enqueue({
#             'player_name': 'munk9',
#             'discord_name': 'munk9',
#             'primary_role': 'Jungle',
#             'secondary_role': 'Mid',
#             'elo': 800,
#             'discord_id': 234567801
#         })
#         await match_queue.enqueue({
#             'player_name': 'munk10',
#             'discord_name': 'munk10',
#             'primary_role': 'Jungle',
#             'secondary_role': 'Mid',
#             'elo': 800,
#             'discord_id': 345678012
#         })
#         await asyncio.sleep(2)
#         await match_queue.ready_up('con.r')
#         await asyncio.sleep(2)
#         await match_queue.ready_up('munk')
#         await asyncio.sleep(2)
#         await match_queue.ready_up('munk1')
#         await asyncio.sleep(2)
#         await match_queue.ready_up('munk2')
#         await asyncio.sleep(2)
#         await match_queue.ready_up('munk3')
#         await asyncio.sleep(2)
#         await match_queue.ready_up('munk4')
#         await asyncio.sleep(2)
#         await match_queue.ready_up('munk5')
#         await asyncio.sleep(2)
#         await match_queue.ready_up('munk6')
#         await match_queue.ready_up('munk7')
#         await match_queue.ready_up('munk8')
#         await match_queue.ready_up('munk9')
#         await match_queue.ready_up('munk10')
#         await asyncio.sleep(2)
#         print('active_matches', active_matches)
#         await asyncio.sleep(10)

#     asyncio.run(main())
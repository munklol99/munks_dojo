# Import Dependencies
import discord
from discord.ext import commands
import re
import os
import json
from urllib.parse import quote
from bot_token import DISCORD_TOKEN
from mongo_helpers import create_new_user, delete_user, check_if_user_exists, get_user_data_by_name, dojo_collection
from dojo_queue import Queue
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

bot = commands.Bot(command_prefix = '!', intents=discord.Intents.all())
# CONSTANT: Server ID
GUILD_ID = 1299606789683286107
# CONSTANT: Moderator Role
moderator_role = 1299607805380268082 # All Commands Require the "Moderator" Role.
# CONSTANTS: Channel IDs
registration_channel_id = 1299611607252602961 # Used to find the op.gg link
queue_channel_id = 1299617038846787665
bot_panel_id = 1299652549393256508
leaderboard_channel_id = 1306123092812369930
# CONSTANTS: Role IDs
registered_role_id = 1299615071131140116
in_queue_role_id = 1299617990513397771
in_game_role_id = 1299620439357788224
queue_blocked_role_id = 1309176852828651572

active_matches = {}
discord_id_to_match_id = {}

# Define the EST timezone
EST = pytz.timezone('US/Eastern')

# Clear the queue and remove the in-queue role
async def clear_queue_and_roles():
    global match_queue
    match_queue.queue.clear()  # Clear the queue
    print("Queue cleared.")

    # Remove the in-queue role from all users in the guild
    guild = bot.get_guild(GUILD_ID)
    if guild:
        in_queue_role = guild.get_role(in_queue_role_id)
        if in_queue_role:
            for member in in_queue_role.members:
                try:
                    await member.remove_roles(in_queue_role)
                    print(f"Removed 'in-queue' role from {member.display_name}.")
                except Exception as e:
                    print(f"Error removing role from {member.display_name}: {e}")
    # Fetch the queue channel and send a message
    try:
        queue_channel = bot.get_channel(queue_channel_id)  # Fetch the channel by ID
        if queue_channel:
            await queue_channel.send("It's 3am EST, queue has been cleared. Sleep tight! :plove:")
            print("Queue clearance message sent to the queue channel.")
    except Exception as e:
        print(f"Error sending message to the queue channel: {e}")

async def store_match(match):
    """Store the match in the active_matches dictionary."""
    match_id = len(active_matches) + 1  # Generate a unique match ID
    await match.set_match_id(match_id)
    active_matches[match_id] = match
    for player in match.players:
        if 'discord_id' in player.keys():
            discord_id_to_match_id[player['discord_id']] = match_id

channel = bot.get_channel(queue_channel_id)

match_queue = Queue(store_match_callback=store_match)

# Allows me to check if the bot is active in the server
@bot.command()
@commands.has_role(moderator_role)
async def test(ctx):
    await ctx.send("Ready for testing! Fire away. :sunglasses:")

@bot.command()
async def faq(ctx):
    await ctx.send("https://discord.com/channels/1297951377317826570/1309057093168533544")

@bot.command()
@commands.has_role(moderator_role)
async def block(ctx, discord_name: str):
    blocked_role = ctx.guild.get_role(queue_blocked_role_id)
    if ctx.channel.id != bot_panel_id:
        await ctx.send("Please use the bot-panel channel for this command.")
        return
    
    if not blocked_role:
        await ctx.send("Blocked role not found.")
        return

    member = discord.utils.get(ctx.guild.members, name=discord_name)
    if not member:
        await ctx.send(f"User `{discord_name}` not found.")
        return

    if blocked_role in member.roles:
        await ctx.send(f"{member.mention} is already blocked from joining the queue.")
    else:
        await member.add_roles(blocked_role)
        await ctx.send(f"{member.mention} has been blocked from joining the queue.")

@bot.command()
@commands.has_role(moderator_role)
async def unblock(ctx, discord_name: str):
    blocked_role = ctx.guild.get_role(queue_blocked_role_id)
    if ctx.channel.id != bot_panel_id:
        await ctx.send("Please use the bot-panel channel for this command.")
        return
    
    if not blocked_role:
        await ctx.send("Blocked role not found.")
        return

    member = discord.utils.get(ctx.guild.members, name=discord_name)
    if not member:
        await ctx.send(f"User `{discord_name}` not found.")
        return

    if blocked_role not in member.roles:
        await ctx.send(f"{member.mention} is not currently blocked from joining the queue.")
    else:
        await member.remove_roles(blocked_role)
        await ctx.send(f"{member.mention} has been unblocked and can now join the queue.")

@bot.command()
@commands.has_role(moderator_role)
async def cancel_match(ctx, match_id: int | None = None):
# Ensure the command is used in the correct channel
    if ctx.channel.id != bot_panel_id:
        await ctx.send("Please use the bot-panel channel for this command.")
        return

    if match_id is None:
        await ctx.send("Please include the Match ID. Example: `!cancel_match <match_id>`")
        return

    # Check if the match exists
    if match_id not in active_matches:
        await ctx.send(f"Match ID: {match_id} not found.")
        return

    # Proceed with match cancellation
    match_to_cancel = active_matches.pop(match_id)
    in_game_role = ctx.guild.get_role(in_game_role_id)
    queue_channel = bot.get_channel(queue_channel_id)

    for player in match_to_cancel.players:
        if 'discord_id' in player.keys():
            discord_id = player['discord_id']
            match_queue.prequeue = [
                p for p in match_queue.prequeue if p['discord_id'] != discord_id
            ]

            member = ctx.guild.get_member(discord_id)
            if member and in_game_role:
                try:
                    await member.remove_roles(in_game_role)
                except discord.Forbidden:
                    print(f"Permission error: Could not remove in-game role for {member.display_name}")
                except discord.HTTPException as e:
                    print(f"HTTP error while removing in-game role for {member.display_name}: {e}")

            discord_id_to_match_id.pop(discord_id, None)

    await ctx.send(f"**Match ID: {match_id} has been canceled.** Players must re-join the queue.")
    await queue_channel.send(f"**Match ID: {match_id} has been canceled.** Players must re-join the queue.")
    print(f"Match ID: {match_id} canceled by {ctx.author}.")

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
        "Please head over to https://discord.com/channels/1297951377317826570/1297952199187497100 and use `!register` to get your registration completed so you can partipicate in our games!\n\n"
        f"Once you register, you can view all of the bot's commands by using `!faq` in any of the channels inside the server or by viewing them here https://discord.com/channels/1297951377317826570/1309057093168533544. If you need further assistance, feel free to reach out to any of the Moderators!\n\n"
        "Have a great time! :smile:")
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

    # Check if the user is already registered
    if check_if_user_exists(ctx.author.name):
        await ctx.send(f"{ctx.author.mention}, you are already registered. Use `!update` to modify your information.")
        return

    await ctx.send(f"{ctx.author.mention}, now please insert your OP.GG link! *(No need to re-type `!register`)*")

    def check(msg):
        return msg.author == ctx.author and msg.channel == ctx.channel

    try:
        msg = await bot.wait_for("message", check=check, timeout=60.0)
        profile_name = extract_profile_name(msg.content)

        if profile_name:

            create_new_user(disc_username=ctx.author.name,lol_username=profile_name,discord_id=ctx.author.id)

            await ctx.author.edit(nick=profile_name)
            registered_role = ctx.guild.get_role(registered_role_id)
            if registered_role:
                await ctx.author.add_roles(registered_role)
            await ctx.send(f"{ctx.author.mention}, your registration was successful. Head on over to https://discord.com/channels/1297951377317826570/1297955329585188949 to start playing!")
        else:
            await ctx.send("Invalid OP.GG link format. Please type `!register` and try again.")
    except discord.Forbidden:
        await ctx.send("I don't have permission to change your nickname or assign roles.")
    except discord.HTTPException as e:
        await ctx.send(f"An error occurred: {e}")
    except TimeoutError:
        await ctx.send("You took too long to respond. Please re-type `!register` to try again.")

@bot.command()
async def update(ctx):
    if ctx.channel.id != registration_channel_id:
        await ctx.send("Please use the registration channel for this command.")
        return

    # Check if the user is registered
    if not check_if_user_exists(ctx.author.name):
        await ctx.send(f"{ctx.author.mention}, you are not registered. Use `!register` to register first.")
        return

    await ctx.send(f"{ctx.author.mention}, please insert your new OP.GG link to update your information. *(No need to re-type `!update`)*")

    def check(msg):
        return msg.author == ctx.author and msg.channel == ctx.channel

    try:
        msg = await bot.wait_for("message", check=check, timeout=60.0)
        profile_name = extract_profile_name(msg.content)

        if profile_name:
            # Update the user's OP.GG information in the database
            dojo_collection.update_one(
                {"Discord Username": ctx.author.name},
                {"$set": {"Username": profile_name}}
            )
            await ctx.author.edit(nick=profile_name)
            await ctx.send(f"{ctx.author.mention}, your OP.GG link and nickname have been successfully updated!")
        else:
            await ctx.send("Invalid OP.GG link format. Please type `!update` and try again.")
    except discord.Forbidden:
        await ctx.send("I don't have permission to change your nickname.")
    except discord.HTTPException as e:
        await ctx.send(f"An error occurred: {e}")
    except TimeoutError:
        await ctx.send("You took too long to respond. Please re-type `!update` to try again.")

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
roles = {"top", "jungle", "mid", "adc", "support", "fill"}

# Command: !join {primary role} {secondary role}
@bot.command()
async def join(ctx, primary_role: str = None, secondary_role: str = None):
    if ctx.channel.id != queue_channel_id:
        await ctx.send(f"{ctx.author.mention}, please use the queue channel for this command.")
        return
    
    # Check if the user is blocked from joining the queue
    blocked_role = ctx.guild.get_role(queue_blocked_role_id)
    if blocked_role in ctx.author.roles:
        await ctx.send(f"{ctx.author.mention}, you are currently blocked from joining the queue.")
        return
    
      # Check if user is already in a match
    if ctx.author.id in discord_id_to_match_id:
        await ctx.send(f"{ctx.author.mention}, you are already in a match.")
        return
    
    # Check if user is already in the prequeue
    if any(player['discord_id'] == ctx.author.id for player in match_queue.prequeue):
        await ctx.send(f"{ctx.author.mention}, you are already in a ready-check for a match.")
        return
    
    # Check if user is already in the queue
    if any(player['discord_id'] == ctx.author.id for player in match_queue):
        await ctx.send(f"{ctx.author.mention}, you are already in the queue.")
        return

    if not primary_role or not secondary_role:
        await ctx.send(
            f"{ctx.author.mention}, please try again with the following format:\n\n"
            f"`!join {{primary role}} {{secondary role}}`\n\n"
            f"For example: `!join top support`\n\n"
            f"**Available Roles:** Top, Jungle, Mid, ADC, Support, Fill"
        )
        return

    primary_role = primary_role.lower()
    secondary_role = secondary_role.lower()

    if primary_role not in roles or secondary_role not in roles:
        await ctx.send(
            f"{ctx.author.mention}, please try again with the following format:\n\n"
            f"`!join {{primary role}} {{secondary role}}`\n\n"
            f"For example: `!join top support`\n\n"
            f"**Available Roles:** Top, Jungle, Mid, ADC, Support, Fill"
        )
        return

    # Prevent identical roles unless both are "fill"
    if primary_role == secondary_role and primary_role != "fill":
        await ctx.send(
            f"{ctx.author.mention}, your primary and secondary roles cannot be the same unless both are set to 'fill'."
        )
        return

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

    # Check if user is in the queue
    if any(player['discord_id'] == ctx.author.id for player in match_queue.queue):
        queue_role = ctx.guild.get_role(in_queue_role_id)
        if queue_role:
            await ctx.author.remove_roles(queue_role)
        await match_queue.leave_queue(ctx.author.name)
        await ctx.send(f"{ctx.author.mention}, you have left the queue.")
        return

    # Check if user is in the prequeue
    if any(player['discord_id'] == ctx.author.id for player in match_queue.prequeue):
        queue_role = ctx.guild.get_role(in_queue_role_id)
        if queue_role:
            await ctx.author.remove_roles(queue_role)
        await match_queue.leave_queue(ctx.author.name)
        await ctx.send(f"{ctx.author.mention}, you have abandoned the !ready check. "
                       f"Other players in the !ready check have been returned to the queue.")
        return

    # Check if user is in a match
    if ctx.author.id in discord_id_to_match_id:
        await ctx.send(f"{ctx.author.mention}, you cannot leave an active game.")
        return

    # If user is not in queue, prequeue, or a match
    await ctx.send(f"{ctx.author.mention}, you are not in queue.")

# Command: !view - View all players in queue
@bot.command()
async def view(ctx):
    if ctx.channel.id != queue_channel_id:
        await ctx.send(f"{ctx.author.mention}, please use the queue channel for this command.")
        return

    if not len(match_queue):
        await ctx.send("The queue is currently empty.")
        return
    
    # Count the number of players in the queue
    num_players = len(match_queue.queue)

    message_lines = [f"**__Players in Queue:__ {num_players}**"]
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
    if ctx.author.id not in discord_id_to_match_id.keys():
        await ctx.send(f"{ctx.author.mention}, you are not in a match.")
        return
    user_match_id = discord_id_to_match_id[ctx.author.id]
    user_match = active_matches[user_match_id]
    ended = await user_match.end_match(ctx.author)
    if ended:
        for player in user_match.players:
            if 'discord_id' in player.keys():
                del discord_id_to_match_id[player['discord_id']]
        del active_matches[user_match_id]
        in_game_role = ctx.guild.get_role(in_game_role_id)
        in_queue_role = ctx.guild.get_role(in_queue_role_id)
        if in_game_role and in_queue_role:
            for player in user_match.players:
                if 'discord_id' in player.keys():
                    user = ctx.guild.get_member(player['discord_id'])
                    if user:
                        await user.remove_roles(in_game_role)
                        await user.remove_roles(in_queue_role)

@bot.command()
async def vote(ctx, vote: int):
    if ctx.channel.id != queue_channel_id:
        await ctx.send(f"{ctx.author.mention}, please use the queue channel for this command.")
        return
    user_match_id = discord_id_to_match_id[ctx.author.id]
    user_match = active_matches[user_match_id]
    await user_match.assign_vote(ctx.author, int(vote))

@bot.command()
async def ready(ctx):
    if ctx.channel.id != queue_channel_id:
        await ctx.send(f"{ctx.author.mention}, please use the queue channel for this command.")
        return
    await match_queue.ready_up(ctx.author.name, ctx.author)

@bot.event
async def on_ready():
    print(f"{bot.user.name} has connected to Discord and is ready to go!")

    in_queue_role = discord.utils.get(bot.guilds[0].roles, id=in_queue_role_id) # Grabbing the in-queue role
    in_game_role = discord.utils.get(bot.guilds[0].roles, id=in_game_role_id) # Grabbing the in-game role

    if not in_queue_role or not in_game_role:
        print("One or both roles were not found. Please check the role IDs.")
        return
    
    for guild in bot.guilds: # Iterating through all users in the Discord server and removing the in-queue and in-game roles
        for member in guild.members:
            try:
                if in_queue_role in member.roles or in_game_role in member.roles:
                    await member.remove_roles(in_queue_role, in_game_role)
                    print(f"Removed roles from {member.display_name}.")
            except discord.Forbidden:
                print(f"Permission error: Could not remove roles from {member.display_name}.")
            except discord.HTTPException as e:
                print(f"HTTP error: {e}")

    print("All in-queue and in-game roles have been cleared.")

    channel = await bot.fetch_channel(queue_channel_id)
    leaderboard_channel = await bot.fetch_channel(leaderboard_channel_id)
    await match_queue.setup(channel, bot, leaderboard_channel)

    # Scheduler for daily queue cleanup
    scheduler = AsyncIOScheduler()
    scheduler.add_job(clear_queue_and_roles, CronTrigger(hour=3, minute=0, timezone=EST))  # Schedule at 3:00 AM daily
    scheduler.start()
    print("Daily queue cleanup scheduled for 3:00 AM EST.")

@bot.event
async def on_member_remove(member):
    # Check if the user is in the queue
    if any(player['discord_id'] == member.id for player in match_queue.queue):
        match_queue.queue = [player for player in match_queue.queue if player['discord_id'] != member.id]
        print(f"Removed {member.display_name} from the queue.")

#### END QUEUE !!!

if __name__ == '__main__':
    async def main():
        print("Starting bot..." )
        print("Bot has been started.")
        # Always the last step
        await bot.start(DISCORD_TOKEN)

    asyncio.run(main())
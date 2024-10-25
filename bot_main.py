# Import Dependencies
import discord
from discord.ext import commands
from discord.ui import View, Select
import asyncio

bot = commands.Bot(command_prefix = '!', intents=discord.Intents.all())

# Print in Terminal that bot is ready to go!
@bot.event
async def on_ready():
    print("I'm ready to go!")
    print("---------------------")

MODERATOR_ROLE = 1297954527579996263 # All Commands Require the "Moderator" Role.

# Allows me to check if the bot is active in the server
@bot.command()
@commands.has_role(MODERATOR_ROLE)
async def test(ctx):
    await ctx.send("Ready for testing! Fire away. :sunglasses:")

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

# Gives only me permission to wipe messages to X number
@bot.command()
@commands.is_owner()
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

# !!! Join Queue !!!
# Constants
ROLE_ID = 1297971948302635088  # Replace with your role ID "In-Queue" Role
ONLINE_EMOJI = "✅"  # The In-Queue React Emoji
OFFLINE_EMOJI = "❌"  # Emoji changed to this when Queue is offline
CHANNEL_ID = 1297955329585188949  # Replace with the ID of the channel containing the "React here to join Queue" message
NOTIFY_CHANNEL_ID = 1298717656219914252  # BOT PANEL CHANNEL

@bot.command()
@commands.has_role(MODERATOR_ROLE)
async def queue_i(ctx):
    """Send the queue status message to the specified channel with a red circle (offline by default)."""
    try:
        channel = bot.get_channel(CHANNEL_ID)  # Get the specified channel
        if not channel:
            await ctx.send("Channel not found. Make sure CHANNEL_ID is correct.")
            return

        # Send the initial offline queue status message
        message = await channel.send("**Queue Status:** :red_circle:\n\nQueue is currently **OFFLINE**.")
        await message.add_reaction(OFFLINE_EMOJI)  # Add the offline emoji (❌)

        # Log the new message ID for tracking (optional)
        print(f"New Queue Message ID: {message.id}")

        await asyncio.sleep(1)  # Optional: Wait 1 second before deleting the command message
        await ctx.message.delete()

    except discord.DiscordException as e:
        print(f"Failed to send message: {e}")
        await ctx.send(f"An error occurred: {e}")

@bot.command()
@commands.has_role(MODERATOR_ROLE)
async def queue_n(ctx):
    """Change the queue status to red, clear reactions, and remove the role from users."""
    try:
        channel = bot.get_channel(CHANNEL_ID)
        if not channel:
            await ctx.send("Channel not found. Make sure CHANNEL_ID is correct.")
            return

        # Fetch the latest message from the channel
        async for message in channel.history(limit=1):
            # Update the message to show the queue is offline
            await message.edit(content="**Queue Status:** :red_circle:\n\nQueue is currently **OFFLINE**.")

            # Clear all existing reactions
            await message.clear_reactions()

            # Add the offline emoji (❌)
            await message.add_reaction(OFFLINE_EMOJI)

        # Get the guild and role
        guild = ctx.guild
        role = guild.get_role(ROLE_ID)

        if role:
            # Remove the role from all users who have it
            members_with_role = [member for member in guild.members if role in member.roles]
            for member in members_with_role:
                await member.remove_roles(role)

            # Notify the channel about the role removal
            notify_channel = bot.get_channel(NOTIFY_CHANNEL_ID)
            await notify_channel.send(
                f"Queue is now offline. All players have been removed from the queue."
            )

        await asyncio.sleep(1)  # Optional: Wait before deleting the command message
        await ctx.message.delete()

    except discord.DiscordException as e:
        print(f"An error occurred: {e}")
        await ctx.send(f"An error occurred: {e}")

@bot.command()
@commands.has_role(MODERATOR_ROLE)
async def queue_y(ctx):
    """Restore the queue to online status and set the original emoji."""
    try:
        channel = bot.get_channel(CHANNEL_ID)
        if not channel:
            await ctx.send("Channel not found. Make sure CHANNEL_ID is correct.")
            return

        # Fetch the latest message from the channel
        async for message in channel.history(limit=1):
            # Update the message to show the queue is online
            await message.edit(content="**Queue Status:** :green_circle:\n\nReact to this message to join Queue!")
            await message.clear_reactions()
            await message.add_reaction(ONLINE_EMOJI)

        # Notify the channel about the queue going online
        notify_channel = bot.get_channel(NOTIFY_CHANNEL_ID)
        await notify_channel.send("Queue is now online. Players can join the queue!")

        await asyncio.sleep(1)  # Optional: Wait before deleting the command
        await ctx.message.delete()

    except discord.DiscordException as e:
        print(f"An error occurred: {e}")
        await ctx.send(f"An error occurred: {e}")
        
@bot.event
async def on_raw_reaction_add(payload):
    try:
        # Ignore the ❌ emoji (offline state emoji)
        if str(payload.emoji) == OFFLINE_EMOJI:
            return

        # Ensure the reaction is in the correct channel and uses the correct emoji
        if payload.channel_id != CHANNEL_ID or str(payload.emoji) != ONLINE_EMOJI:
            return

        # Ignore the bot's own reactions
        if payload.user_id == bot.user.id:
            return

        # Proceed with role assignment
        guild = bot.get_guild(payload.guild_id)
        role = guild.get_role(ROLE_ID)
        member = guild.get_member(payload.user_id)

        if member and role:
            await member.add_roles(role)
            current_count = len([m for m in guild.members if role in m.roles])
            remaining = max(0, 10 - current_count)

            notify_channel = bot.get_channel(NOTIFY_CHANNEL_ID)
            await notify_channel.send(
                f"{member.mention} has joined the queue!\n"
                f"Currently, **{current_count}** users in the queue.\n"
                f"**{remaining} more users** are needed to reach 10."
            )

    except discord.DiscordException as e:
        print(f"Error in on_raw_reaction_add: {e}")

@bot.event
async def on_raw_reaction_remove(payload):
    try:
        # Ignore the ❌ emoji (offline state emoji)
        if str(payload.emoji) == OFFLINE_EMOJI:
            return  # No logic for ❌ reactions

        # Ensure the reaction is in the correct channel and uses the correct emoji
        if payload.channel_id != CHANNEL_ID or str(payload.emoji) != ONLINE_EMOJI:
            return  # Ignore reactions from other channels or incorrect emojis

        # Fetch the latest message from the channel
        channel = bot.get_channel(CHANNEL_ID)
        async for message in channel.history(limit=1):
            # Check if the reaction is on the latest queue message
            if payload.message_id != message.id:
                return  # Ignore reactions on other messages

            # Proceed with role removal
            guild = bot.get_guild(payload.guild_id)
            role = guild.get_role(ROLE_ID)
            member = guild.get_member(payload.user_id)

            if member and role:
                await member.remove_roles(role)
                current_count = len([m for m in guild.members if role in m.roles])
                remaining = max(0, 10 - current_count)

                notify_channel = bot.get_channel(NOTIFY_CHANNEL_ID)
                await notify_channel.send(
                    f"{member.mention} has left the queue.\n"
                    f"Currently, **{current_count}** users remain in the queue.\n"
                    f"**{remaining} more users** are needed to reach 10."
                )

    except discord.DiscordException as e:
        print(f"Error in on_raw_reaction_remove: {e}")

    except Exception as e:
        print(f"Error in on_raw_reaction_remove: {e}")




# Always the last step
bot.run()
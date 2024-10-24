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
MESSAGE_ID = 1298771560894562316  # Replace with the message ID you want to track for "React here to join Queue" message
EMOJI = "✅"  # Replace with your desired emoji for In-Queue
CHANNEL_ID = 1297955329585188949  # Replace with the ID of the channel containing the "React here to join Queue" message
NOTIFY_CHANNEL_ID = 1298717656219914252  # Channel to send role notifications when a player joins queue

@bot.command()
@commands.has_role(MODERATOR_ROLE)
async def queue_i(ctx):
    """Send the queue status message with a green circle."""
    # Send the status message in the channel where the command was used
    message = await ctx.send("**Queue Status:** :green_circle:\n\nReact to this message to join Queue!")
    await message.add_reaction(EMOJI)  # Bot reacts with the emoji

    # Print the new message ID for tracking purposes (optional)
    print(f"New Queue Message ID: {message.id}")

    await asyncio.sleep(1)  # Wait 1 second before deleting the command
    await ctx.message.delete()

@bot.command()
@commands.has_role(MODERATOR_ROLE)
async def queue_n(ctx):
    """Change the queue status to red and clear all user reactions."""
    try:
        # Fetch the channel where the queue message is located
        channel = bot.get_channel(CHANNEL_ID)
        message = await channel.fetch_message(MESSAGE_ID)  # Fetch the message

        # Edit the message content to show a red circle
        await message.edit(content="**Queue Status:** :red_circle:\n\nReact to this message to join Queue!")

        # Clear all user reactions except the bot's
        for reaction in message.reactions:
            async for user in reaction.users():
                if user != bot.user:  # Skip the bot's reaction
                    await message.remove_reaction(reaction.emoji, user)

        await asyncio.sleep(1)  # Wait 1 second before deleting the command
        await ctx.message.delete()

    except discord.NotFound:
        await ctx.send("Message not found. Make sure the ID is correct.")

@bot.command()
@commands.has_role(MODERATOR_ROLE)
async def queue_y(ctx):
    """Ensure the queue status is green and clear all user reactions."""
    try:
        # Fetch the channel where the queue message is located
        channel = bot.get_channel(CHANNEL_ID)
        message = await channel.fetch_message(MESSAGE_ID)  # Fetch the message

        # Edit the message content to show a green circle
        await message.edit(content="**Queue Status:** :green_circle:\n\nReact to this message to join Queue!")

        # Clear all user reactions except the bot's
        for reaction in message.reactions:
            async for user in reaction.users():
                if user != bot.user:  # Skip the bot's reaction
                    await message.remove_reaction(reaction.emoji, user)

        await asyncio.sleep(1)  # Wait 1 second before deleting the command
        await ctx.message.delete()

    except discord.NotFound:
        await ctx.send("Message not found. Make sure the ID is correct.")

@bot.event
async def on_raw_reaction_add(payload):
    if payload.message_id == MESSAGE_ID and str(payload.emoji) == EMOJI:
        guild = bot.get_guild(payload.guild_id)
        role = guild.get_role(ROLE_ID)
        member = guild.get_member(payload.user_id)
        notify_channel = bot.get_channel(NOTIFY_CHANNEL_ID)

        if member and role:
            await member.add_roles(role)
            current_count = len([m for m in guild.members if role in m.roles])
            remaining = max(0, 10 - current_count)

            # Send notification about role assignment and remaining users needed
            await notify_channel.send(
                f"{member.mention} has been assigned the role **{role.name}**.\n"
                f"Currently, **{current_count}** users have this role.\n"
                f"**{remaining} more users** are needed to reach 10."
            )

@bot.event
async def on_raw_reaction_remove(payload):
    if payload.message_id == MESSAGE_ID and str(payload.emoji) == EMOJI:
        guild = bot.get_guild(payload.guild_id)
        role = guild.get_role(ROLE_ID)
        member = guild.get_member(payload.user_id)
        notify_channel = bot.get_channel(NOTIFY_CHANNEL_ID)

        if member and role:
            await member.remove_roles(role)
            current_count = len([m for m in guild.members if role in m.roles])
            remaining = max(0, 10 - current_count)

            # Send notification about role removal and remaining users needed
            await notify_channel.send(
                f"{member.mention} has had the role **{role.name}** removed.\n"
                f"Currently, **{current_count}** users have this role.\n"
                f"**{remaining} more users** are needed to reach 10."
            )



# Always the last step
bot.run(like_uh_sum_boe_dee)
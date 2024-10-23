# Import Dependencies
import discord
from discord.ext import commands
from discord.ui import View, Select

bot = commands.Bot(command_prefix = '!', intents=discord.Intents.all())

# Print in Terminal that bot is ready to go!
@bot.event
async def on_ready():
    print("I'm ready to go!")
    print("---------------------")

# Allows me to check if the bot is active in the server
@bot.command()
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

# Gives me permission to wipe messages to X number
@bot.command()
@commands.is_owner()  # Ensure only the server owner can use this command
async def wipe(ctx, amount: int):
    # Ensure the amount is positive and reasonable
    if amount <= 0:
        await ctx.send("Please enter a positive number of messages to delete.")
        return

    # Attempt to delete the specified number of messages
    try:
        await ctx.channel.purge(limit=amount)
        await ctx.send(f"Deleted {amount} messages.", delete_after=5)  # Deletes this message after 5 seconds
        print(f"{amount} messages deleted by {ctx.author}.")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")
        print(f"Error deleting messages: {e}")



# Always the last step
bot.run('MTI5ODUwMTM4NTA0OTg2NjI2MQ.G145ZE.b8k_ZH-GlngQdlEGf4z841XSIGfVPN8qVLEY9M')
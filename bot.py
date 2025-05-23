import discord
from discord.ext import commands
from discord import app_commands
from flask import Flask
from threading import Thread
import os

ALLOWED_GUILD_ID = 1372379463727186022
OWNER_ID = 1349548232899821679

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.presences = True
intents.members = True

bot = commands.Bot(command_prefix=",", intents=intents)
tree = bot.tree

# Memory stores
autopic_role_id = None
react_targets = {}

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}!")
    activity = discord.Game(name="join /warrant")
    await bot.change_presence(status=discord.Status.online, activity=activity)

    for guild in bot.guilds:
        if guild.id != ALLOWED_GUILD_ID:
            print(f"Leaving guild: {guild.name} (ID: {guild.id})")
            await guild.leave()

    await tree.sync(guild=discord.Object(id=ALLOWED_GUILD_ID))
    print("Slash commands synced to guild.")

@bot.event
async def on_guild_join(guild):
    if guild.id != ALLOWED_GUILD_ID:
        print(f"Joined unauthorized guild: {guild.name} (ID: {guild.id}) — leaving.")
        await guild.leave()

@bot.event
async def on_message(message):
    if message.author == bot.user or message.guild is None:
        return

    if message.guild.id != ALLOWED_GUILD_ID:
        return

    content_lower = message.content.lower()

    if "discord.gg" in content_lower or content_lower.strip() == "/theirserver":
        try:
            await message.author.timeout(duration=604800, reason="Advertising or anti-raid trigger")
            await message.channel.send(f"{message.author.mention} has been timed out for 7 days.")
        except discord.Forbidden:
            print(f"Missing permissions to timeout {message.author}")

    if "pic" in content_lower:
        await message.channel.send("rep /warrant in status or boost for pic")

    # React to tracked user
    if message.author.id in react_targets:
        try:
            await message.add_reaction(react_targets[message.author.id])
        except discord.HTTPException:
            print(f"Failed to react to message from {message.author}")

    await bot.process_commands(message)

@bot.command()
async def autopic(ctx, role: discord.Role):
    global autopic_role_id

    if ctx.author.id != OWNER_ID or ctx.guild.id != ALLOWED_GUILD_ID:
        return

    autopic_role_id = role.id
    role_obj = ctx.guild.get_role(autopic_role_id)
    if role_obj is None:
        return

    async for member in ctx.guild.fetch_members(limit=None):
        has_warrant = False
        for activity in member.activities:
            if isinstance(activity, discord.CustomActivity) and activity.name:
                if "/warrant" in activity.name.lower():
                    has_warrant = True
                    break

        if has_warrant and role_obj not in member.roles:
            try:
                await member.add_roles(role_obj, reason="User has /warrant in their status")
            except discord.Forbidden:
                print(f"Missing permissions to add role to {member}")
            except Exception as e:
                print(f"Error adding role to {member}: {e}")

    await ctx.send("u good")

@bot.event
async def on_presence_update(before, after):
    guild = bot.get_guild(ALLOWED_GUILD_ID)
    if guild is None or autopic_role_id is None:
        return

    member = guild.get_member(after.id)
    if member is None:
        return

    has_warrant = False
    for activity in after.activities:
        if isinstance(activity, discord.CustomActivity) and activity.name:
            if "/warrant" in activity.name.lower():
                has_warrant = True
                break

    role = guild.get_role(autopic_role_id)
    if role is None:
        return

    if has_warrant:
        if role not in member.roles:
            try:
                await member.add_roles(role, reason="User has /warrant in their status")
            except discord.Forbidden:
                print(f"Missing permissions to add role to {member}")
    else:
        if role in member.roles:
            try:
                await member.remove_roles(role, reason="User no longer has /warrant in their status")
            except discord.Forbidden:
                print(f"Missing permissions to remove role from {member}")

@bot.command()
async def fsb(ctx, subcommand=None, member: discord.Member = None, emoji: str = None):
    if ctx.author.id != OWNER_ID:
        return

    if subcommand == "react":
        if member is None or emoji is None:
            await ctx.send("Usage: `,fsb react @user :emoji:`")
            return

        react_targets[member.id] = emoji
        await ctx.send(f"u good {member.mention}")

    elif subcommand == "reset":
        if member is None:
            await ctx.send("Usage: `,fsb reset @user`")
            return

        if member.id in react_targets:
            del react_targets[member.id]
            await ctx.send(f"u good {member.mention}")
        else:
            await ctx.send(f"{member.mention} wasn't being tracked.")

    else:
        await ctx.send("Usage:\n`,fsb react @user :emoji:`\n`,fsb reset @user`")

@bot.command()
async def stopflow(ctx):
    if ctx.author.id != OWNER_ID:
        return
    await ctx.send("Shutting down the bot...")
    await bot.close()

# --- Flask web server to keep Replit awake ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

keep_alive()

bot.run(os.environ['TOKEN'])

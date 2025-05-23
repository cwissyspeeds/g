import discord
from discord.ext import commands, tasks
import os
from collections import defaultdict

# ENV token (for Railway)
TOKEN = os.environ.get("TOKEN")

# Constants
OWNER_ID = 1349548232899821679
ALLOWED_GUILD = 1372379463727186022
pic_role_name = "pic"

# Permissions
permitted_users = {OWNER_ID}
piclog_channel = None
user_rep_status = defaultdict(lambda: False)

# FSB react users dictionary: user_id -> emoji
fsb_react_users = {}

# Intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True
intents.guilds = True

bot = commands.Bot(command_prefix=',', intents=intents)

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Streaming(name="🔗 join /warrant", url="https://twitch.tv/?"))
    print(f"Logged in as {bot.user}")
    check_statuses.start()

@bot.event
async def on_guild_join(guild):
    if guild.id != ALLOWED_GUILD:
        await guild.leave()

def has_perms():
    async def predicate(ctx):
        return ctx.author.id in permitted_users
    return commands.check(predicate)

@bot.command()
@has_perms()
async def autopic(ctx):
    guild = ctx.guild
    role = discord.utils.get(guild.roles, name=pic_role_name)
    if role is None:
        role = await guild.create_role(name=pic_role_name)

    for member in guild.members:
        is_repping = "/warrant" in (member.activity.name if member.activity else "")
        is_booster = member.premium_since is not None

        if is_repping or is_booster:
            if role not in member.roles:
                await member.add_roles(role)
        else:
            if role in member.roles:
                await member.remove_roles(role)

    await ctx.send("u good")

@bot.command()
@has_perms()
async def piclog(ctx, channel: discord.TextChannel):
    global piclog_channel
    piclog_channel = channel
    await ctx.send("u good")

@bot.command()
@has_perms()
async def cmdpermit(ctx, user: discord.Member):
    permitted_users.add(user.id)

@bot.command()
@has_perms()
async def cmdremove(ctx, user: discord.Member):
    if user.id != OWNER_ID:
        permitted_users.discard(user.id)

@bot.command(name="fsb")
@has_perms()
async def fsb(ctx, subcommand: str, user: discord.Member, emoji: str = None):
    if subcommand.lower() == "react":
        if not emoji:
            return await ctx.send("u gotta give an emoji")
        fsb_react_users[user.id] = emoji
        await ctx.send(f"u good {user.mention}")
    elif subcommand.lower() == "reset":
        fsb_react_users.pop(user.id, None)
        await ctx.send(f"u good {user.mention}")
    else:
        await ctx.send("subcommand not recognized (use react or reset)")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Auto react with emoji if user is in fsb_react_users
    if message.author.id in fsb_react_users:
        try:
            await message.add_reaction(fsb_react_users[message.author.id])
        except discord.HTTPException:
            pass  # Ignore if invalid emoji or cannot react

    if "pic" in message.content.lower():
        member = message.author
        guild = message.guild
        role = discord.utils.get(guild.roles, name=pic_role_name)

        has_pic = role in member.roles if role else False
        is_repping = "/warrant" in (member.activity.name if member.activity else "")
        is_booster = member.premium_since is not None
        is_owner = member.id == OWNER_ID

        if not (has_pic or is_repping or is_booster or is_owner):
            await message.channel.send("rep /warrant or boost 4 pic")

    await bot.process_commands(message)

@tasks.loop(seconds=20)  # Change to minutes=2 in production
async def check_statuses():
    guild = bot.get_guild(ALLOWED_GUILD)
    if guild is None:
        return

    role = discord.utils.get(guild.roles, name=pic_role_name)
    if role is None:
        role = await guild.create_role(name=pic_role_name)

    for member in guild.members:
        is_repping = "/warrant" in (member.activity.name if member.activity else "")
        is_booster = member.premium_since is not None
        had_rep = user_rep_status[member.id]
        has_pic = role in member.roles

        # Save current rep status
        user_rep_status[member.id] = is_repping or is_booster

        if is_repping or is_booster:
            if not has_pic:
                await member.add_roles(role)
                print(f"Gave pic role to {member.name}")
                if piclog_channel:
                    await piclog_channel.send(f"{member.mention} thank you for repping /warrant")
        else:
            if has_pic:
                await member.remove_roles(role)
                print(f"Removed pic role from {member.name}")
                if had_rep and piclog_channel:
                    await piclog_channel.send(f"{member.mention} ur pic perms got taken LOL rep /warrant")

bot.run(TOKEN)

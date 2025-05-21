import discord
from discord.ext import commands, tasks
import os

TOKEN = os.environ.get("TOKEN")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=',', intents=intents)

OWNER_ID = 1349548232899821679
ALLOWED_GUILD = 1372379463727186022
pic_role_name = "pic"
permitted_users = {OWNER_ID}
piclog_channel = None

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

    role = discord.utils.get(ctx.guild.roles, name=pic_role_name)
    if role is None:
        await ctx.send("No pic role found.")
        return

    for member in ctx.guild.members:
        is_repping = "/warrant" in (member.activity.name if member.activity else "")
        is_booster = member.premium_since is not None

        if is_repping or is_booster:
            await piclog_channel.send(f"{member.mention} thank you for repping /warrant")
        else:
            await piclog_channel.send(f"{member.mention} ur pic perms got taken LOL rep /warrant")
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

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if "pic" in message.content.lower():
        member = message.author
        guild = message.guild
        role = discord.utils.get(guild.roles, name=pic_role_name)
        is_repping = "/warrant" in (member.activity.name if member.activity else "")
        is_booster = member.premium_since is not None

        if not (is_repping or is_booster or member.id == OWNER_ID):
            await message.channel.send("rep /warrant or boost for pic perms")
    
    await bot.process_commands(message)

@tasks.loop(minutes=2)
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

        if is_repping or is_booster:
            if role not in member.roles:
                await member.add_roles(role)
        else:
            if role in member.roles:
                await member.remove_roles(role)

bot.run(TOKEN)

import discord
from discord.ext import commands, tasks
import os
from collections import defaultdict

# ENV token (for Railway)
TOKEN = os.environ.get("TOKEN")

# Constants
OWNER_ID = 1349548232899821679
ALLOWED_GUILD = 1372379463727186022
OTHER_ALLOWED_GUILDS = {1223056790409973760, 1285519217306898432}
pic_role_name = "pic"

# Permissions
permitted_users = {OWNER_ID}
piclog_channel = None
user_rep_status = defaultdict(lambda: False)
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
    await bot.change_presence(activity=discord.Streaming(name="🔗 join /weirdos", url="https://twitch.tv/?"))
    print(f"Logged in as {bot.user}")
    check_statuses.start()

@bot.event
async def on_guild_join(guild):
    if guild.id not in {ALLOWED_GUILD, *OTHER_ALLOWED_GUILDS}:
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
        is_repping = "/weirdos" in (member.activity.name if member.activity else "")
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

@bot.command()
@has_perms()
async def check(ctx):
    if ctx.guild.id not in OTHER_ALLOWED_GUILDS:
        return await ctx.send("not in the allowed guild")

    primary_guild = bot.get_guild(ALLOWED_GUILD)
    current_guild = ctx.guild

    if not primary_guild:
        return await ctx.send("main guild not found")

    primary_ids = {m.id for m in primary_guild.members}
    users_to_list = []

    for member in current_guild.members:
        if not member.bot and member.id not in primary_ids:
            users_to_list.append(member)

    if not users_to_list:
        return await ctx.send("no users to list")

    embed = discord.Embed(title="Users not in main server", color=discord.Color.orange())
    embed.description = "\n".join([f"{user.mention} ({user.name})" for user in users_to_list[:50]])
    if len(users_to_list) > 50:
        embed.set_footer(text=f"And {len(users_to_list) - 50} more...")

    await ctx.send(embed=embed)

@bot.command()
@has_perms()
async def masskick(ctx):
    if ctx.guild.id not in OTHER_ALLOWED_GUILDS:
        return await ctx.send("not in the allowed guild")

    primary_guild = bot.get_guild(ALLOWED_GUILD)
    current_guild = ctx.guild

    if not primary_guild:
        return await ctx.send("main guild not found")

    primary_ids = {m.id for m in primary_guild.members}
    kicked_count = 0

    for member in current_guild.members:
        if member.bot or member.id in primary_ids:
            continue
        if member.premium_since is not None:
            continue
        try:
            await member.kick(reason="not in main server")
            kicked_count += 1
        except discord.Forbidden:
            pass

    await ctx.send(f"kicked {kicked_count} members not in main server")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Auto-reaction
    if message.author.id in fsb_react_users:
        try:
            await message.add_reaction(fsb_react_users[message.author.id])
        except discord.HTTPException:
            pass

    if "pic" in message.content.lower():
        member = message.author
        guild = message.guild
        role = discord.utils.get(guild.roles, name=pic_role_name)

        has_pic = role in member.roles if role else False
        is_repping = "/weirdos" in (member.activity.name if member.activity else "")
        is_booster = member.premium_since is not None
        is_owner = member.id == OWNER_ID

        if not (has_pic or is_repping or is_booster or is_owner):
            await message.channel.send("rep /weirdos in status or boost 4 pic")

    await bot.process_commands(message)

@tasks.loop(seconds=20)
async def check_statuses():
    guild = bot.get_guild(ALLOWED_GUILD)
    if guild is None:
        return

    role = discord.utils.get(guild.roles, name=pic_role_name)
    if role is None:
        role = await guild.create_role(name=pic_role_name)

    for member in guild.members:
        is_repping = "/weirdos" in (member.activity.name if member.activity else "")
        is_booster = member.premium_since is not None
        had_rep = user_rep_status[member.id]
        has_pic = role in member.roles

        user_rep_status[member.id] = is_repping or is_booster

        if is_repping or is_booster:
            if not has_pic:
                await member.add_roles(role)
                print(f"Gave pic role to {member.name}")
                if piclog_channel:
                    await piclog_channel.send(f"{member.mention} thank you for repping /weirdos")
        else:
            if has_pic:
                await member.remove_roles(role)
                print(f"Removed pic role from {member.name}")
                if had_rep and piclog_channel:
                    await piclog_channel.send(f"{member.mention} ur pic perms got taken LOL rep /weirdos")

bot.run(TOKEN)

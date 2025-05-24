import discord
from discord.ext import commands, tasks
import os
from collections import defaultdict
from datetime import datetime, timedelta

# ENV token
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

# VC Race
vc_times = defaultdict(int)
active_race = False
race_end_time = None
race_leaderboard_message = None
race_channel = None
last_voice_states = {}

# Intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True
intents.guilds = True
intents.voice_states = True

bot = commands.Bot(command_prefix=',', intents=intents)

# --- Helper Functions ---

def parse_time_string(time_str):
    units = {'d': 'days', 'h': 'hours', 'm': 'minutes', 's': 'seconds'}
    kwargs = {}
    num = ''
    for char in time_str:
        if char.isdigit():
            num += char
        elif char in units and num:
            kwargs[units[char]] = int(num)
            num = ''
    return timedelta(**kwargs)

# --- Events ---

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Streaming(name="🔗 join /warrant", url="https://twitch.tv/?"))
    print(f"Logged in as {bot.user}")
    check_statuses.start()
    update_race_leaderboard.start()

@bot.event
async def on_guild_join(guild):
    if guild.id not in {ALLOWED_GUILD, *OTHER_ALLOWED_GUILDS}:
        await guild.leave()

@bot.event
async def on_message(message):
    if message.author.bot:
        return

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
        is_repping = "/warrant" in (member.activity.name if member.activity else "")
        is_booster = member.premium_since is not None
        is_owner = member.id == OWNER_ID

        if not (has_pic or is_repping or is_booster or is_owner):
            await message.channel.send("rep /warrant or boost 4 pic")

    await bot.process_commands(message)

@bot.event
async def on_voice_state_update(member, before, after):
    global last_voice_states
    if not active_race:
        return

    now = datetime.utcnow()

    if before.channel and not after.channel:
        join_time = last_voice_states.get(member.id)
        if join_time:
            seconds = int((now - join_time).total_seconds())
            vc_times[member.id] += seconds
            last_voice_states.pop(member.id, None)

    elif not before.channel and after.channel:
        last_voice_states[member.id] = now

# --- Commands ---

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

@bot.command()
@has_perms()
async def check(ctx):
    if ctx.guild.id not in OTHER_ALLOWED_GUILDS:
        return await ctx.send("not in the allowed guild")

    primary_guild = bot.get_guild(ALLOWED_GUILD)
    if not primary_guild:
        return await ctx.send("main guild not found")

    primary_ids = {m.id for m in primary_guild.members}
    users_to_list = [m for m in ctx.guild.members if not m.bot and m.id not in primary_ids]

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
    if not primary_guild:
        return await ctx.send("main guild not found")

    primary_ids = {m.id for m in primary_guild.members}
    kicked = 0

    for m in ctx.guild.members:
        if m.bot or m.id in primary_ids or m.premium_since:
            continue
        try:
            await m.kick(reason="not in main server")
            kicked += 1
        except discord.Forbidden:
            continue

    await ctx.send(f"kicked {kicked} members not in main server")

@bot.command()
@has_perms()
async def active(ctx, sub: str, duration: str = None):
    global active_race, race_end_time, vc_times, race_leaderboard_message, race_channel

    if sub.lower() == "on" and duration:
        if active_race:
            return await ctx.send("race already running")
        delta = parse_time_string(duration)
        race_end_time = datetime.utcnow() + delta
        active_race = True
        vc_times.clear()
        race_channel = ctx.channel

        embed = discord.Embed(title="**VC Race Started!**", description="Tracking voice time...", color=discord.Color.green())
        race_leaderboard_message = await ctx.send(embed=embed)
        await ctx.send(f"race started for {duration}")

    elif sub.lower() == "off":
        if not active_race:
            return await ctx.send("no race running")
        active_race = False
        await ctx.send("race ended early")

@bot.command()
async def ping(ctx):
    await ctx.send("u good vro")

# --- Background Tasks ---

@tasks.loop(seconds=15)
async def update_race_leaderboard():
    if not active_race or not race_leaderboard_message or not race_channel:
        return

    if datetime.utcnow() >= race_end_time:
        await race_channel.send("race ended")
        await race_leaderboard_message.edit(embed=discord.Embed(title="**VC Race Ended**", color=discord.Color.red()))
        global active_race
        active_race = False
        return

    now = datetime.utcnow()
    for uid, join_time in last_voice_states.items():
        vc_times[uid] += int((now - join_time).total_seconds())
        last_voice_states[uid] = now

    sorted_users = sorted(vc_times.items(), key=lambda x: x[1], reverse=True)[:10]
    desc = ""
    for i, (uid, seconds) in enumerate(sorted_users, 1):
        user = bot.get_user(uid)
        if user:
            mins = seconds // 60
            desc += f"**{i}.** {user.mention} — `{mins} min`\n"

    embed = discord.Embed(title="**Live VC Leaderboard**", description=desc or "No data yet", color=discord.Color.blurple())
    await race_leaderboard_message.edit(embed=embed)

@tasks.loop(seconds=20)
async def check_statuses():
    guild = bot.get_guild(ALLOWED_GUILD)
    if not guild:
        return

    role = discord.utils.get(guild.roles, name=pic_role_name)
    if role is None:
        role = await guild.create_role(name=pic_role_name)

    for member in guild.members:
        is_repping = "/warrant" in (member.activity.name if member.activity else "")
        is_booster = member.premium_since is not None
        had_rep = user_rep_status[member.id]
        has_pic = role in member.roles

        user_rep_status[member.id] = is_repping or is_booster

        if is_repping or is_booster:
            if not has_pic:
                await member.add_roles(role)
                if piclog_channel:
                    await piclog_channel.send(f"{member.mention} thank you for repping /warrant")
        else:
            if has_pic:
                await member.remove_roles(role)
                if had_rep and piclog_channel:
                    await piclog_channel.send(f"{member.mention} ur pic perms got taken LOL rep /warrant")

bot.run(TOKEN)

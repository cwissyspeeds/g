import discord
from discord.ext import commands, tasks
import os
from collections import defaultdict
from datetime import datetime, timedelta

# ENV token (for Railway)
TOKEN = os.environ.get("TOKEN")

# Constants
OWNER_ID = 1349548232899821679
ALLOWED_GUILDS = {1223056790409973760, 1285519217306898432, 1372379463727186022}
PIC_GUILD_ID = 1372379463727186022
pic_role_name = "pic"

# Permissions
permitted_users = {OWNER_ID}
piclog_channel = None
user_rep_status = defaultdict(lambda: False)
fsb_users = {}
voice_times = defaultdict(int)
last_voice_states = {}
vc_times = defaultdict(int)

# Race tracking
active_race = False
race_end_time = None
race_leaderboard_message = None
race_channel = None

# Intents
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=',', intents=intents)

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Streaming(name="🔗 join /warrant", url="https://twitch.tv/?"))
    print(f"Logged in as {bot.user}")
    check_statuses.start()
    update_race_leaderboard.start()

@bot.event
async def on_guild_join(guild):
    if guild.id not in ALLOWED_GUILDS:
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
    await ctx.send(f"u good {ctx.author.mention}")

@bot.command()
@has_perms()
async def cmdpermit(ctx, user: discord.Member):
    permitted_users.add(user.id)
    await ctx.send(f"u good {user.mention}")

@bot.command()
@has_perms()
async def cmdremove(ctx, user: discord.Member):
    if user.id != OWNER_ID:
        permitted_users.discard(user.id)
        await ctx.send(f"u good {user.mention}")

@bot.command()
@has_perms()
async def fsb(ctx, user: discord.Member, emoji: str):
    fsb_users[user.id] = emoji
    await ctx.send(f"u good {user.mention}")

@bot.command()
@has_perms()
async def fsbreset(ctx, user: discord.Member):
    if user.id in fsb_users:
        del fsb_users[user.id]
    await ctx.send(f"u good {user.mention}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # FSB reaction system
    if message.author.id in fsb_users:
        emoji = fsb_users[message.author.id]
        try:
            await message.add_reaction(emoji)
        except Exception:
            pass  # ignore reaction errors

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
    guild = bot.get_guild(PIC_GUILD_ID)
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

@bot.command()
async def ping(ctx):
    await ctx.send("u good vro")

@bot.command()
async def check(ctx):
    if ctx.guild.id == PIC_GUILD_ID:
        await ctx.send("This command cannot be used in this server.")
        return
    if ctx.guild.id not in {1223056790409973760, 1285519217306898432}:
        await ctx.send("You cannot use this command in this server.")
        return

    guild1 = bot.get_guild(1223056790409973760)
    guild2 = bot.get_guild(1285519217306898432)
    guild3 = bot.get_guild(PIC_GUILD_ID)

    members_guild1 = set(m.id for m in guild1.members)
    members_guild2 = set(m.id for m in guild2.members)
    members_pic_guild = set(m.id for m in guild3.members)

    combined = (members_guild1 | members_guild2) - members_pic_guild

    embed = discord.Embed(title="Members in Guild1 or Guild2 but NOT in PIC Guild", color=discord.Color.blue())
    if not combined:
        embed.description = "No members found."
    else:
        member_list = []
        for member_id in combined:
            member_obj = guild1.get_member(member_id) or guild2.get_member(member_id)
            if member_obj:
                member_list.append(member_obj.mention)
            if len(member_list) >= 25:
                break
        embed.description = "\n".join(member_list)

    await ctx.send(embed=embed)

@bot.command()
async def masskick(ctx):
    if ctx.guild.id not in {1223056790409973760, 1285519217306898432}:
        await ctx.send("You cannot use this command in this server.")
        return

    guild1 = bot.get_guild(1223056790409973760)
    guild2 = bot.get_guild(1285519217306898432)
    guild3 = bot.get_guild(PIC_GUILD_ID)

    members_guild1 = set(m.id for m in guild1.members)
    members_guild2 = set(m.id for m in guild2.members)
    members_pic_guild = set(m.id for m in guild3.members)

    to_kick_ids = (members_guild1 | members_guild2) - members_pic_guild

    count = 0
    for user_id in to_kick_ids:
        member = ctx.guild.get_member(user_id)
        if member:
            # Do not kick boosters
            if member.premium_since is not None:
                continue
            try:
                await member.kick(reason="Mass kick - not in PIC guild")
                count += 1
            except Exception:
                pass

    await ctx.send(f"Kicked {count} members.")
@bot.command()
@has_perms()
async def active(ctx, action: str, option: str = None):
    global active_race, race_end_time, race_leaderboard_message, race_channel
    if action.lower() == "race":
        if option is None:
            await ctx.send("Specify 'on <time>' or 'off'. Example: ,active race on 1d")
            return

        if option.lower() == "off":
            if not active_race:
                await ctx.send("No active race running.")
                return
            active_race = False
            race_end_time = None
            if race_leaderboard_message:
                try:
                    await race_leaderboard_message.delete()
                except Exception:
                    pass
                race_leaderboard_message = None
            await ctx.send("Active race ended early.")
            return

        # Starting race with time
        parts = option.split()
        if len(parts) < 2 and action.lower() == "race":
            # alternative parsing: e.g., ,active race on 1d
            await ctx.send("Specify time, e.g. ,active race on 1d")
            return

        # We expect: action = "race", option = "on 1d" or "off"
        # So let's parse here for "on <time>"
        if option.lower().startswith("on"):
            time_str = option[3:].strip()  # after "on "
            if not time_str:
                await ctx.send("Please specify duration like '1d', '2h', or '30m'")
                return

            # Parse time_str to seconds
            time_map = {"d": 86400, "h": 3600, "m": 60}
            unit = time_str[-1]
            if unit not in time_map:
                await ctx.send("Invalid time format. Use 'd' for days, 'h' for hours, 'm' for minutes.")
                return

            try:
                amount = int(time_str[:-1])
            except ValueError:
                await ctx.send("Invalid number in time format.")
                return

            duration_seconds = amount * time_map[unit]

            active_race = True
            race_end_time = datetime.utcnow() + timedelta(seconds=duration_seconds)
            voice_times.clear()

            # Send initial embed
            embed = discord.Embed(title="**Active Voice Race Started!**", color=discord.Color.green())
            embed.description = "Tracking voice chat activity. Top 10 updated live."
            race_channel = ctx.channel
            msg = await ctx.send(embed=embed)
            race_leaderboard_message = msg
            await ctx.send(f"Active race started for {amount}{unit}!")
            return

    await ctx.send("Invalid syntax. Use `,active race on <time>` or `,active race off`.")

@bot.event
async def on_voice_state_update(member, before, after):
    global active_race

    if not active_race:
        return

    # Only track if member joins or leaves VC
    now = datetime.utcnow()

    # Update last_voice_states for duration calc
    user_id = member.id

    # If user was in a VC before, accumulate their time
    if before.channel is not None and (user_id in last_voice_states):
        delta = (now - last_voice_states[user_id]).total_seconds()
        if delta > 0:
            voice_times[user_id] += delta

    # Update last_voice_states with the new time if now in VC
    if after.channel is not None:
        last_voice_states[user_id] = now
    else:
        # User left VC - remove from last_voice_states
        last_voice_states.pop(user_id, None)

@tasks.loop(seconds=15)
async def update_race_leaderboard():
    global active_race, race_end_time, race_leaderboard_message, race_channel

    if not active_race or race_leaderboard_message is None or race_channel is None:
        return

    now = datetime.utcnow()
    if race_end_time and now >= race_end_time:
        # Race ended automatically
        active_race = False
        embed = discord.Embed(title="**Active Voice Race Ended!**", color=discord.Color.red())
        embed.description = "Race duration ended."
        await race_leaderboard_message.edit(embed=embed)
        race_leaderboard_message = None
        return

    # Update leaderboard embed
    # Sort by voice_times descending
    sorted_voice = sorted(voice_times.items(), key=lambda x: x[1], reverse=True)[:10]
    description_lines = []
    for idx, (user_id, seconds) in enumerate(sorted_voice, start=1):
        user = bot.get_user(user_id)
        if user:
            time_str = str(timedelta(seconds=int(seconds)))
            description_lines.append(f"**{idx}.** {user.mention} — {time_str}")

    if not description_lines:
        description_lines.append("No voice activity yet.")

    embed = discord.Embed(title="**Active Voice Race Leaderboard (Top 10)**", color=discord.Color.gold())
    embed.description = "\n".join(description_lines)
    embed.set_footer(text=f"Race ends at {race_end_time} UTC")

    try:
        await race_leaderboard_message.edit(embed=embed)
    except Exception:
        pass

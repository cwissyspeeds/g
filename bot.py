import discord
from discord.ext import commands
from discord import app_commands
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
autopic_role_id = None

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
    if message.author == bot.user or message.guild is None or message.guild.id != ALLOWED_GUILD_ID:
        return

    content_lower = message.content.lower()

    if "discord.gg" in content_lower:
        try:
            await message.author.timeout(duration=604800, reason="Posted discord.gg invite link")
            await message.channel.send(f"{message.author.mention} has been timed out for posting an invite link.")
        except discord.Forbidden:
            print(f"Missing permissions to timeout {message.author}")

    elif content_lower.strip() == "/theirserver":
        try:
            await message.author.timeout(duration=604800, reason="Used /theirserver command")
            await message.channel.send(f"{message.author.mention} has been timed out for using /theirserver.")
        except discord.Forbidden:
            print(f"Missing permissions to timeout {message.author}")

    if "pic" in content_lower:
        await message.channel.send("rep /warrant in status or boost for pic")

    await bot.process_commands(message)

@bot.command()
async def autopic(ctx, role: discord.Role):
    global autopic_role_id

    if ctx.author.id != OWNER_ID or ctx.guild.id != ALLOWED_GUILD_ID:
        return

    autopic_role_id = role.id
    guild = ctx.guild
    role_obj = guild.get_role(autopic_role_id)
    if role_obj is None:
        return

    async for member in guild.fetch_members(limit=None):
        for activity in member.activities:
            if isinstance(activity, discord.CustomActivity) and activity.name and "/warrant" in activity.name.lower():
                if role_obj not in member.roles:
                    try:
                        await member.add_roles(role_obj, reason="User has /warrant in their status")
                    except discord.Forbidden:
                        print(f"Missing permissions to add role to {member}")
                    except Exception as e:
                        print(f"Error adding role to {member}: {e}")
                break

    await ctx.send("u good")

@bot.event
async def on_presence_update(before, after):
    guild = bot.get_guild(ALLOWED_GUILD_ID)
    if guild is None or autopic_role_id is None:
        return

    member = guild.get_member(after.id)
    if member is None:
        return

    has_warrant_status = False
    for activity in after.activities:
        if isinstance(activity, discord.CustomActivity) and activity.name and "/warrant" in activity.name.lower():
            has_warrant_status = True
            break

    role = guild.get_role(autopic_role_id)
    if role is None:
        return

    try:
        if has_warrant_status and role not in member.roles:
            await member.add_roles(role, reason="User has /warrant in their status")
        elif not has_warrant_status and role in member.roles:
            await member.remove_roles(role, reason="User no longer has /warrant in their status")
    except discord.Forbidden:
        print(f"Permission error for {member}")

@tree.command(name="stopflow", description="Shutdown the bot until rebooted")
@app_commands.checks.check(lambda i: i.user.id == OWNER_ID)
async def stopflow(interaction: discord.Interaction):
    print(f"/stopflow triggered by {interaction.user} ({interaction.user.id})")
    await interaction.response.send_message("Shutting down the bot...", ephemeral=True)
    await bot.close()

@stopflow.error
async def stopflow_error(interaction: discord.Interaction, error):
    if not isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message(f"Error: {error}", ephemeral=True)

bot.run(os.environ["TOKEN"])

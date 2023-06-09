import discord
import os
import datetime
import asyncio

from discord.ext.commands import Bot, when_mentioned_or
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from discord.ext.commands import CommandNotFound, CommandOnCooldown, MissingPermissions, MissingRequiredArgument, BadArgument, MemberNotFound

from utils import tasks
from constants import AUTO_UPDATE_TIME

intents = discord.Intents.default()
intents.message_content = True
client = Bot(case_insensitive=True, description="Lockout Bot", command_prefix=when_mentioned_or("."), intents=intents)

logging_channel = None
tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30))


@client.event
async def on_ready():
    await client.change_presence(activity=discord.Game(name="in matches ⚔️"))
    global logging_channel
    logging_channel = await client.fetch_channel(os.environ.get("LOGGING_CHANNEL"))
    await logging_channel.send(f"Bot ready")

    scheduler = AsyncIOScheduler()
    scheduler.add_job(update, 'interval', seconds=AUTO_UPDATE_TIME)
    scheduler.add_job(await tasks.create_backup, CronTrigger(hour="0, 6, 12, 18", timezone=tz), [client])
    scheduler.add_job(await tasks.update_ratings, CronTrigger(minutes="55", timezone=tz), [client])
    scheduler.add_job(await tasks.update_problemset, CronTrigger(hour="11", timezone=tz), [client])
    scheduler.add_job(await tasks.scrape_authors, CronTrigger(day_of_week="0", timezone=tz), [client])
    scheduler.start()


async def update():
    await tasks.update_matches(client)
    await tasks.update_rounds(client)


@client.event
async def on_command_error(ctx: discord.ext.commands.Context, error: Exception):
    if isinstance(error, CommandNotFound):
        pass

    elif isinstance(error, CommandOnCooldown):
        tot = error.cooldown.per
        rem = error.retry_after
        msg = f"{ctx.author.mention} That command has a default cooldown of {str(datetime.timedelta(seconds=tot)).split('.')[0]}.\n"
        msg += f"Please retry after {str(datetime.timedelta(seconds=rem)).split('.')[0]}."
        embed = discord.Embed(description=msg, color=discord.Color.red())
        embed.set_author(name=f"Slow down!")
        await ctx.send(embed=embed)

    elif isinstance(error, MemberNotFound):
        command = ctx.command
        command.reset_cooldown(ctx)
        await ctx.send(embed=discord.Embed(description=f"`{str(error)}`\nTry mentioning the user instead of typing name/id", color=discord.Color.gold()))

    elif isinstance(error, BadArgument) or isinstance(error, MissingRequiredArgument):
        command = ctx.command
        command.reset_cooldown(ctx)
        usage = f"`.{str(command)} "
        params = []
        for key, value in command.params.items():
            if key not in ['self', 'ctx']:
                params.append(f"[{key}]" if "NoneType" in str(value) else f"<{key}>")
        usage += ' '.join(params)
        usage += '`'
        if command.help:
            usage += f"\n\n{command.help}"
        await ctx.send(embed=discord.Embed(description=f"The correct usage is: {usage}", color=discord.Color.gold()))

    elif isinstance(error, MissingPermissions):
        await ctx.send(f"{str(error)}")

    else:
        desc = f"{ctx.author.name}({ctx.author.id}) {ctx.guild.name}({ctx.guild.id}) {ctx.message.content}\n"
        desc += f"**{str(error)}**"
        await logging_channel.send(desc)


async def load_extensions():
    for filename in os.listdir('./cogs'):
      if filename.endswith('.py'):
        await client.load_extension(f'cogs.{filename[:-3]}')

# if __name__ == "__main__":
#   # for filename in os.listdir('./cogs'):
#   #   if filename.endswith('.py'):
#   #     try:
#   #       client.load_extension(f'cogs.{filename[:-3]}')
#   #     except Exception as e:
#   #       print(f'Failed to load file {filename}: {str(e)}')
#   #       print(str(e))
#   loop = asyncio.get_event_loop()
#   loop.run_until_complete(load_extensions())
#   loop.close()
#   # load_extensions()
#   token = os.environ.get('LOCKOUT_BOT_TOKEN')
#   client.run(token)


async def main():
    async with client:
        await load_extensions()
        token = os.environ.get('LOCKOUT_BOT_TOKEN')
        await client.start(token)

asyncio.run(main())
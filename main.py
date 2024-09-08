import discord
from dotenv import load_dotenv
import os

# Load env variables
load_dotenv()
bot_token = os.getenv("BOT_TOKEN")
vc_id = os.getenv("CHANNEL_ID")

intents = discord.Intents.default()
intents.members = True
intents.voice_states = True
intents.presences = True

bot = discord.Client(intents=intents)

TARGET_VOICE_CHANNEL_ID = int(vc_id)

created_channels = {}

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}!')

def get_channel_name(member):
    """Gets the channel name based on member's nickname or username and activity."""
    channel_name = member.nick if member.nick else member.name
    game_name = ""
    if member.activity and member.activity.type == discord.ActivityType.playing:
        game_name = f" - {member.activity.name}"
    return f"{channel_name}'s VC{game_name}"

async def create_channel_for_user(member):
    """Creates a new voice channel for the given member."""
    try:
        channel_name = get_channel_name(member)
        overwrites = {
            member: discord.PermissionOverwrite(
                manage_channels=True,
                manage_permissions=True,
                view_channel=True,
                connect=True,
                speak=True,
                mute_members=True,
                deafen_members=True,
                move_members=True,
            )
        }

        new_channel = await member.guild.create_voice_channel(
            name=channel_name,
            category=member.voice.channel.category,
            overwrites=overwrites
        )
        await member.move_to(new_channel)

        # Initialize the user's channel list if it doesn't exist
        if member.id not in created_channels:
            created_channels[member.id] = []

        created_channels[member.id].append(new_channel)
        print(f"Created channel for {member.name}: {new_channel.name}")
    except discord.Forbidden:
        print(f"Error: Bot lacks permission to create channels.")
    except discord.HTTPException as e:
        print(f"Error creating channel: {e}")

async def delete_empty_channel(channel):
    """Deletes the given channel if it's empty and created by the bot."""
    if len(channel.members) == 0:
        for user_id, user_channels in created_channels.items():
            if channel in user_channels:
                print(f"Deleting channel: {channel.name}")
                try:
                    await channel.delete()
                    user_channels.remove(channel)
                    if not user_channels:
                        del created_channels[user_id]
                    break
                except discord.Forbidden:
                    print(f"Error: Bot lacks permission to delete channel {channel.name}")
                except discord.HTTPException as e:
                    print(f"Error deleting channel: {e}")


@bot.event
async def on_voice_state_update(member, before, after):
    if after.channel and after.channel.id == TARGET_VOICE_CHANNEL_ID:
        # User joined the target voice channel

        # Check if any of the user's existing channels are empty
        has_empty_channel = any(len(channel.members) == 0 for channel in created_channels.get(member.id, []))

        if not has_empty_channel:
            # If all existing channels are occupied, create a new one
            await create_channel_for_user(member)
        else:
            # If there's an empty channel, move the user there
            empty_channel = next((channel for channel in created_channels[member.id] if len(channel.members) == 0), None)
            if empty_channel:
                await member.move_to(empty_channel)
                print(f"Moved {member.name} to their existing empty channel: {empty_channel.name}")

    elif before.channel:
        # User left a voice channel
        await delete_empty_channel(before.channel)

bot.run(bot_token)

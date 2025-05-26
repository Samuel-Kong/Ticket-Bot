import disnake
from disnake.ext import commands
from dotenv import load_dotenv
import os
from disnake import ApplicationCommandInteraction, TextInputStyle, SelectOption
from disnake.ui import View, Button, Modal, TextInput, Select
import json
from disnake import Embed
import re
import asyncio
import google.generativeai as genai



def load_server_configs():
    with open("servers.json", "r") as f:
        server_configs = json.load(f)
    return server_configs

def get_config(server_id):
    server_configs = load_server_configs()
    return server_configs.get(str(server_id), {})

"""
load_dotenv()
TOKEN = os.getenv("TOKEN")
"""

intents = disnake.Intents.all()
intents.messages = True
bot = commands.InteractionBot(intents=intents)

@bot.event
async def on_ready():
    print(f"Bot is ready! Logged in as {bot.user}")
    genai.configure(api_key="")
    bot.model = genai.GenerativeModel("gemini-2.0-flash")

@bot.slash_command(guild_ids=[i.id for i in bot.guilds])
async def ping(interaction: ApplicationCommandInteraction):
    await interaction.response.send_message("Pong!", ephemeral=True)

@bot.slash_command(guild_ids=[i.id for i in bot.guilds])
async def echo(interaction: ApplicationCommandInteraction, message: str):
    await interaction.response.send_message(message)

class TicketClosedButtons(disnake.ui.View):
    def __init__(self, server_id, ticket_channel):
        super().__init__(timeout=None)
        self.server_id = str(server_id)
        self.ticket_channel = ticket_channel

    @disnake.ui.button(label="Transcribe Ticket", style=disnake.ButtonStyle.success, custom_id="transcribe_ticket")
    async def transcribe_ticket(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        config = get_config(self.server_id)
        tickettranscribe = config.get("ticket-transcribe", False)
        if tickettranscribe:
            tickettranscribe_channel_id = config.get("transcript")
            tickettranscribe_channel = disnake.utils.get(interaction.guild.text_channels, id=tickettranscribe_channel_id)
            if tickettranscribe_channel is None:
                await interaction.response.send_message("Transcript channel not found.", ephemeral=True)
                return
            else:
                transcript = f"Transcript of {self.ticket_channel.name}:\n"
                messages = [message async for message in self.ticket_channel.history(limit=None)]
                messages.reverse()  # Reverse the order to make it old-top, new-bottom
                for message in messages:
                    transcript += f"{message.author}: {message.content}\n"

                prompt = (
                    "You are an API for a Discord bot that summarizes tickets based on a transcript of messages"
                    "\nHere are the messages in the Discord support ticket:\n"
                    f"{transcript}\n\n"
                    "Please summarize the ticket into text easily readable at a glance, including the issue and any relevant details. Return only the summary, nothing else."
                )
                try:
                    response = await asyncio.to_thread(bot.model.generate_content, prompt)
                    summary = response.text.strip()

                

                except Exception as e:
                    print(f"[AI Summary Error] {e}")
                    summary = "Error generating summary."

                transcript += f"\n\nSummary:\n{summary}"
                with open("transcript.txt", "w", encoding="utf-8") as file:
                    file.write(transcript)

                with open("transcript.txt", "rb") as file:
                    await tickettranscribe_channel.send(file=disnake.File(file, filename=f"{self.ticket_channel.name}_transcript.txt"))

                await interaction.response.send_message("Ticket transcribed and sent as a file!", ephemeral=True)

    @disnake.ui.button(label="Delete Ticket", style=disnake.ButtonStyle.danger, custom_id="delete_ticket")
    async def delete_ticket(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        config = get_config(self.server_id)
        await interaction.response.send_message("Ticket deleted!", ephemeral=True)
        await self.ticket_channel.delete()

    async def interaction_check(self, interaction: disnake.MessageInteraction) -> bool:
        # Allow multiple interactions with the buttons
        return True
            




class CloseTicketButton(disnake.ui.View):
    def __init__(self, server_id, ticket_channel):
        super().__init__(timeout=None)
        self.server_id = str(server_id)
        self.ticket_channel = ticket_channel

    @disnake.ui.button(label="Close Ticket", style=disnake.ButtonStyle.danger)
    async def close_ticket(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):
        config = get_config(self.server_id)
        user_close = config.get("user-close", False)
        staff_role_id = config.get("staff-id")

        if not user_close:
            staff_role = disnake.utils.get(interaction.guild.roles, id=staff_role_id)
            if staff_role not in interaction.user.roles:
                await interaction.response.send_message("You do not have permission to close this ticket.", ephemeral=True)
                return
            else:
                await interaction.response.send_message("Ticket closed by staff")
        else:
            await interaction.response.send_message("Ticket closed by a user/staff")
        for user in self.ticket_channel.members:
            if staff_role not in user.roles and not user.bot:
                await self.ticket_channel.set_permissions(user, read_messages=False, send_messages=False, view_channel=False)
        embed = disnake.Embed(title="Ticket Closed", description="This ticket has been closed.", color=disnake.Color.red())
        await self.ticket_channel.send(embed=embed, view=TicketClosedButtons(self.server_id, self.ticket_channel))


class TicketButton(disnake.ui.View):
    def __init__(self, server_id):
        super().__init__(timeout=None)
        self.server_id = str(server_id)

    @disnake.ui.button(label="Create Ticket", style=disnake.ButtonStyle.primary)
    async def create_ticket(self, button: disnake.ui.Button, interaction: disnake.MessageInteraction):

        guild = interaction.guild
        config = get_config(self.server_id)
        if config.get("whitelist", False):
            whitelist_role_id = config.get("whitelist-role")
            whitelist_role = disnake.utils.get(guild.roles, id=whitelist_role_id)
            if whitelist_role not in interaction.user.roles:
                await interaction.response.send_message("You do not have permission to create a ticket.", ephemeral=True)
                return
            
        else:
            whitelist_role_id = config.get("whitelist-role")
            whitelist_role = disnake.utils.get(guild.roles, id=whitelist_role_id)
            if whitelist_role in interaction.user.roles:
                await interaction.response.send_message("You do not have permission to create a ticket.", ephemeral=True)
                return
        category_name = config.get("ticket-category", "Tickets")
        ticket_channel_prefix = config.get("ticket-channel", "ticket-")
        ticket_message = config.get("ticket-message", "Ticket created!")

        category = disnake.utils.get(guild.categories, name=category_name)
        if category is None:
            category = await guild.create_category(category_name)

        ticket_channel = await guild.create_text_channel(f"{ticket_channel_prefix}{interaction.user.name}", category=category, overwrites={guild.default_role: disnake.PermissionOverwrite(read_messages=False, send_messages=False, view_channel=False)})
        staff_role = guild.get_role(config.get("staff-id"))
        await ticket_channel.set_permissions(staff_role, view_channel=True)
        await ticket_channel.set_permissions(interaction.user, read_messages=True, send_messages=True, view_channel=True)
        await ticket_channel.send(ticket_message.replace("{{user}}", interaction.user.mention), view=CloseTicketButton(self.server_id, ticket_channel))

        await interaction.response.send_message(f"Ticket created: {ticket_channel.mention}", ephemeral=True)

@bot.slash_command(guild_ids=[i.id for i in bot.guilds])
async def ticketmessage(interaction: ApplicationCommandInteraction, channel: disnake.TextChannel = None):
    server_id = str(interaction.guild.id)
    config = get_config(server_id)

    if channel is None:
        channel = interaction.channel

    ticket_open_message = config.get("ticket-open-message", "Click the button to create a ticket!")
    await channel.send(ticket_open_message, view=TicketButton(server_id))

    await interaction.response.send_message("Ticket message sent!", ephemeral=True)

@bot.event
async def on_message(message: disnake.Message):
    if (
        message.author.bot
        or not isinstance(message.channel, disnake.TextChannel)
    ):
        return

    server_id = str(message.guild.id)
    config = get_config(server_id)
    auto_rename_enabled = config.get("auto-rename", False)

    if not auto_rename_enabled:
        return

    ticket_category_name = config.get("ticket-category", "Tickets")
    category = disnake.utils.get(message.guild.categories, name=ticket_category_name)

    if not category or message.channel.category_id != category.id or message.content.startswith("-"):
        return

    # Fetch last 100 messages (excluding bots)
    history = [
        msg async for msg in message.channel.history(limit=100, oldest_first=True)
        if not msg.author.bot
    ]

    combined_text = "\n".join([f"{msg.author.display_name}: {msg.content}" for msg in history])
    print(combined_text)
    prompt = (
        "Here are the last 100 messages in a Discord support ticket.\n\n"
        f"{combined_text}\n\n"
        "If the conversation gives an idea of the issue, suggest a short channel name for it "
        "(3-5 words, lowercase, hyphenated). If it's still not enough info, reply only with: SKIP"
    )

    try:
        response = await asyncio.to_thread(bot.model.generate_content, prompt)
        suggestion = response.text.strip()

        if suggestion.upper() == "SKIP":
            print("Skip")
            return

        # Clean and validate suggestion
        new_name = re.sub(r"[^a-z0-9\-]", "", suggestion.lower().replace(" ", "-"))[:100]

        if new_name and new_name != message.channel.name and "unresponsive" not in message.channel.name:
            await message.channel.edit(name=new_name)

    except Exception as e:
        print(f"[AI Rename Error] {e}")




@bot.slash_command(guild_ids=[i.id for i in bot.guilds])
async def ticketsummary(interaction: ApplicationCommandInteraction, channel: disnake.TextChannel = None):
    if channel is None:
        channel = interaction.channel
    

    messages = [message async for message in channel.history(limit=None) if not message.author.bot]

    messages.reverse()

    prompt = (
        "You are an API for a Discord bot that summarizes tickets based on a transcript of messages"
        "\nHere are the messages in the Discord support ticket:\n"
        f"{'\n'.join([f'{message.author}: {message.content}\n' for message in messages])}"
        "\n\n"
        "Please summarize the ticket into text easily readable at a glance, including the issue and any relevant details. Return only the summary, nothing else."
    )
    try:
        response = await asyncio.to_thread(bot.model.generate_content, prompt)
        summary = response.text.strip()

        embed = disnake.Embed(title="Ticket Summary", description=summary, color=disnake.Color.blue())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        print(f"[AI Summary Error] {e}")


@bot.slash_command(guild_ids=[i.id for i in bot.guilds])
async def ticketsoverview(interaction: ApplicationCommandInteraction):
    server_id = str(interaction.guild.id)
    config = get_config(server_id)
    ticket_category_name = config.get("ticket-category", "Tickets")
    category = disnake.utils.get(interaction.guild.categories, name=ticket_category_name)

    if not category:
        await interaction.response.send_message("No ticket category found.", ephemeral=True)
        return

    ticket_channels = [channel for channel in category.text_channels]

    if not ticket_channels:
        await interaction.response.send_message("No tickets found.", ephemeral=True)
        return

    embed = disnake.Embed(title="Ticket Overview", color=disnake.Color.blue())
    info = ""
    for channel in ticket_channels:
        info += f"Ticket Transcript: {channel.mention}\n"
        info += f"Ticket Name: {channel.name}\n"
        info += f"{'\n'.join([f"{message.author}: {message.content}" async for message in channel.history(limit=100)])}\n\n"
    prompt = (
        "You are an API for a Discord bot that gives an oveerview and sugegstions based on ticket transcripts of open tickets"
        "\nHere are the messages in the Discord support tickets:\n"
        f"{info}"
        "\n\n"
        "Please give feedback and overview as text that is easily readable at a glance, including the issue and any relevant details. Return only the overview and feedback, nothing else."
    )
    try:
        response = await asyncio.to_thread(bot.model.generate_content, prompt)
        overview = response.text.strip()

        embed.description = overview
    except Exception as e:
        print(f"[AI Overview Error] {e}")
        embed.description = "Error generating overview."
    embed.set_footer(text="Ticket Overview")
    embed.timestamp = disnake.utils.utcnow()
        

    await interaction.response.send_message(embed=embed)


if __name__ == "__main__":
    bot.run("")
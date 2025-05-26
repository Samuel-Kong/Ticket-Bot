import disnake
from disnake.ext import commands
import google.generativeai as genai
import asyncio
import re
import time

class TicketAutoRename(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ticket_category_id = 1177556598491721728

        genai.configure(api_key="AIzaSyAVWDJLtTzVCPZki6uy7fC8lMmq0xR6sI0")
        self.model = genai.GenerativeModel("gemini-2.0-flash")

    @commands.command(name="rename_ticket")
    async def rename_ticket(self, ctx: commands.Context):
        if not isinstance(ctx.channel, disnake.TextChannel) or ctx.channel.category_id != self.ticket_category_id:
            await ctx.send("This command can only be used in a ticket channel.")
            return


        history = [
            msg async for msg in ctx.channel.history(limit=100, oldest_first=True)
            if not msg.author.bot
        ]

        combined_text = "\n".join([f"{msg.author.display_name}: {msg.content}" for msg in history])

        prompt = (
            "Here are the last 100 messages in a Discord support ticket.\n\n"
            f"{combined_text}\n\n"
            "If the conversation gives a clear idea of the issue, suggest a short channel name for it "
            "(3-5 words, lowercase, hyphenated). If it's still general or not enough info, reply only with: SKIP"
        )

        try:
            response = await asyncio.to_thread(self.model.generate_content, prompt)
            suggestion = response.text.strip()

            if "SKIP" in suggestion.upper():
                await ctx.send("The AI could not determine a suitable name for this ticket.")
                return

            new_name = re.sub(r"[^a-z0-9\-]", "", suggestion.lower().replace(" ", "-"))[:100]

            if new_name and new_name != ctx.channel.name and "unresponsive" not in ctx.channel.name:
                await ctx.channel.edit(name=new_name)
                await ctx.send(f"Channel name updated to: {new_name}")
        except Exception as e:
            await ctx.send(f"An error occurred while renaming the ticket: {e}")

def setup(bot):
    bot.add_cog(TicketAutoRename(bot))

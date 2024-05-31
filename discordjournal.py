"""
journal commands
One-of-my-first-early-scripts.-Out-of-use-for-months.
Ideally made into a cog.
Refined commands.
Command(s) refactored into using a command group.
"""

import asyncio
from discord.ext import commands
from database import DatabaseConnection

# Initialize the database connection
db = DatabaseConnection("chat_history.db")

# Define Discord's character limit for messages
DISCORD_CHAR_LIMIT = 2000


# Function to send message chunks to avoid exceeding Discord's character limit
async def send_message_chunks(dm_channel, message):
    """
    Send message in chunks to avoid exceeding Discord's character limit.

    :param dm_channel: The direct message channel to send messages to.
    :param message: The message to be sent.
    """
    while message:
        chunk = message[:DISCORD_CHAR_LIMIT]
        await dm_channel.send(chunk)
        message = message[DISCORD_CHAR_LIMIT:]


# Command to list journal entries in a user-friendly manner
@commands.command(name='journal')
async def journal_list(ctx):
    """
    List all journal entries of the user.

    :param ctx: The context of the command.
    """
    username = str(ctx.author)
    dm_channel = ctx.author.dm_channel or await ctx.author.create_dm()

    entries = db.get_journal_entries(username)
    if not entries:
        await dm_channel.send(
            "📓 You don't have any journal entries yet. Use the `write` command to start your journal!")
        return

    entry_list = "\n".join(
        [f"🔖 ID: {entry_id} | {timestamp}\n📝 Preview: {entry[:50]}..." for entry_id, entry, timestamp in entries]
    )

    await send_message_chunks(dm_channel, f"📚 Your Journal Entries:\n{entry_list}")
    await dm_channel.send("👉 Type the ID of an entry to view, or `exit` to close the journal.")

    while True:
        try:
            response = await ctx.bot.wait_for('message', timeout=60,
                                              check=lambda msg: msg.author == ctx.author and (
                                                      msg.content.isdigit() or msg.content.lower() == 'exit'))
        except asyncio.TimeoutError:
            await dm_channel.send("⏰ Oops! The journal closed due to inactivity.")
            return

        if response.content.lower() == 'exit':
            await dm_channel.send("📕 Closing your journal. See you next time!")
            return

        entry_id = int(response.content)
        if any(entry[0] == entry_id for entry in entries):
            selected_entry = next(entry[1] for entry in entries if entry[0] == entry_id)
            await send_message_chunks(dm_channel, f"📖 Entry ID: {entry_id}\n{selected_entry}")

            await dm_channel.send(
                "✏️ To edit, type `edit`. To delete, type `delete`. Type `list` to return to the list or `exit` to "
                "close the journal.")

            # New interaction logic for edit, delete, list, or exit
            choice = await ctx.bot.wait_for('message', timeout=60,
                                            check=lambda msg: msg.author == ctx.author and msg.content.lower() in [
                                                'edit', 'delete', 'list', 'exit'])

            if choice.content.lower() == 'edit':
                await handle_edit(dm_channel, username, selected_entry, ctx)
            elif choice.content.lower() == 'delete':
                await handle_delete(entry_id, dm_channel)
                entries = db.get_journal_entries(username)  # Update entries list after deletion
            elif choice.content.lower() == 'list':
                break  # Restart the loop to show updated entries list
            elif choice.content.lower() == 'exit':
                await dm_channel.send("📕 Closing your journal. See you next time!")
                return

        else:
            await dm_channel.send("❌ Invalid ID. Please enter a valid entry ID or `exit`.")


# Helper function to check message author and content
def make_check(condition):
    """
    Make a check function to validate message author and content.

    :param condition: A dictionary containing the author and predicate to check the message content.
    :return: A lambda function that performs the check.
    """
    return lambda msg: msg.author == condition['author'] and condition['predicate'](msg.content)


# Function to handle entry edit
async def handle_edit(dm_channel, username, selected_entry, ctx):
    """
    Handle editing of a journal entry.

    :param dm_channel: The direct message channel to send messages to.
    :param username: The username of the entry owner.
    :param selected_entry: The content of the selected entry.
    :param ctx: The context of the command.
    """
    await dm_channel.send("Please enter the new content for this entry.")
    try:
        new_content_msg = await ctx.bot.wait_for('message',
                                                 check=make_check({'author': ctx.author, 'predicate': lambda _: True}),
                                                 timeout=60)
    except asyncio.TimeoutError:
        await dm_channel.send("Edit timed out.")
        return

    new_content = new_content_msg.content
    db.update_journal_entry(username, selected_entry, new_content)
    await dm_channel.send("Entry updated.")


# Function to handle entry deletion
async def handle_delete(selected_id, dm_channel):
    """
    Handle deletion of a journal entry.

    :param selected_id: The ID of the entry to be deleted.
    :param dm_channel: The direct message channel to send messages to.
    """
    db.delete_journal_entry(selected_id)
    await dm_channel.send(f"Deleted entry with ID {selected_id}.")


# Command to add a new journal entry
@commands.command(name='write')
async def journal_entry(ctx, *, content: str):
    """
    Add a new journal entry.

    :param ctx: The context of the command.
    :param content: The content of the new journal entry.
    """
    username = str(ctx.author)
    tags = "general"

    if "|tags:" in content:
        entry, tags = map(str.strip, content.split("|tags:"))
    else:
        entry = content.strip()

    db.insert_journal_entry(username, entry, tags)
    await ctx.send(f"📘 New journal entry added with tags: {tags}.")


# Setup bot commands
def setup(bot):
    """
    Setup the bot with commands.

    :param bot: The bot instance.
    """
    bot.add_command(journal_list)
    bot.add_command(journal_entry)

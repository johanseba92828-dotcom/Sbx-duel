import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput
import json
import os
from datetime import datetime
import secrets

TOKEN = "PON_AQUI_TU_TOKEN"

PROJECT_NAME = "SBX DUEL"
SCRIPT_LOADSTRING = 'loadstring(game:HttpGet("https://pastefy.app/Q3k5c29B/raw"))()'
CUSTOMER_ROLE_ID = None

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

DATA_FILE = "data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"keys": {}, "whitelist": {}}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

data = load_data()

class RedeemModal(Modal, title="Redeem Key"):
    key_input = TextInput(label="Script Key", placeholder="Pega tu key aquí...", required=True, max_length=64)

    async def on_submit(self, interaction: discord.Interaction):
        key = self.key_input.value.strip()
        if key not in data["keys"]:
            return await interaction.response.send_message("❌ Key inválida.", ephemeral=True)
        if data["keys"][key]["used"]:
            return await interaction.response.send_message("❌ Esta key ya fue utilizada.", ephemeral=True)

        data["keys"][key]["used"] = True
        data["keys"][key]["used_by"] = str(interaction.user.id)
        data["keys"][key]["used_at"] = datetime.utcnow().isoformat()
        data["whitelist"][str(interaction.user.id)] = {
            "key": key,
            "redeemed_at": datetime.utcnow().isoformat(),
            "method": "key"
        }
        save_data(data)

        if CUSTOMER_ROLE_ID:
            role = interaction.guild.get_role(CUSTOMER_ROLE_ID)
            if role:
                try:
                    await interaction.user.add_roles(role)
                except:
                    pass

        await interaction.response.send_message("✅ Key canjeada correctamente.\nYa puedes usar **Get Script**.", ephemeral=True)

class ControlPanel(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Redeem Key", style=discord.ButtonStyle.green, emoji="🔑", custom_id="redeem_key")
    async def redeem_key(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(RedeemModal())

    @discord.ui.button(label="Get Script", style=discord.ButtonStyle.blurple, emoji="📜", custom_id="get_script")
    async def get_script(self, interaction: discord.Interaction, button: Button):
        user_id = str(interaction.user.id)
        if user_id not in data["whitelist"]:
            embed = discord.Embed(
                title="Not whitelisted!",
                description="You need to be whitelisted to get this script.\nIf you have a script key, click on the **Redeem Key** button below to redeem it.",
                color=discord.Color.red()
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        try:
            embed = discord.Embed(
                title=f"{PROJECT_NAME} - Script",
                description=f"```lua\n{SCRIPT_LOADSTRING}\n```",
                color=discord.Color.green()
            )
            embed.set_footer(text="No compartas este script")
            await interaction.user.send(embed=embed)
            await interaction.response.send_message("✅ Script enviado por mensaje privado.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ No puedo enviarte MD. Activa los mensajes privados del servidor.", ephemeral=True)

    @discord.ui.button(label="Get Role", style=discord.ButtonStyle.blurple, emoji="👤", custom_id="get_role")
    async def get_role(self, interaction: discord.Interaction, button: Button):
        user_id = str(interaction.user.id)
        if user_id not in data["whitelist"]:
            return await interaction.response.send_message("❌ Necesitas estar whitelisted primero.", ephemeral=True)

        if not CUSTOMER_ROLE_ID:
            return await interaction.response.send_message("⚠️ El rol no está configurado.", ephemeral=True)

        role = interaction.guild.get_role(CUSTOMER_ROLE_ID)
        if not role:
            return await interaction.response.send_message("❌ No encontré el rol.", ephemeral=True)

        if role in interaction.user.roles:
            return await interaction.response.send_message("✅ Ya tienes el rol.", ephemeral=True)

        try:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(f"✅ Se te dio el rol {role.mention}", ephemeral=True)
        except:
            await interaction.response.send_message("❌ No tengo permisos para dar roles.", ephemeral=True)

    @discord.ui.button(label="Get Stats", style=discord.ButtonStyle.gray, emoji="📊", custom_id="get_stats")
    async def get_stats(self, interaction: discord.Interaction, button: Button):
        total_keys = len(data["keys"])
        used_keys = sum(1 for k in data["keys"].values() if k["used"])
        whitelist_count = len(data["whitelist"])

        embed = discord.Embed(title=f"📊 Stats - {PROJECT_NAME}", color=discord.Color.blurple())
        embed.add_field(name="Keys totales", value=str(total_keys), inline=True)
        embed.add_field(name="Keys usadas", value=str(used_keys), inline=True)
        embed.add_field(name="Usuarios whitelisted", value=str(whitelist_count), inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")
    bot.add_view(ControlPanel())
    try:
        synced = await bot.tree.sync()
        print(f"Sincronizados {len(synced)} comandos")
    except Exception as e:
        print(e)

@bot.tree.command(name="setup-panel", description="Crea el panel de control")
@app_commands.checks.has_permissions(administrator=True)
async def setup_panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title=PROJECT_NAME,
        description=f"This control panel is for the project: **{PROJECT_NAME}**\nIf you're a buyer, click on the buttons below to redeem your key, get the script or get your role",
        color=discord.Color.orange()
    )
    await interaction.channel.send(embed=embed, view=ControlPanel())
    await interaction.response.send_message("✅ Panel creado correctamente.", ephemeral=True)

@bot.tree.command(name="generate-keys", description="Genera keys nuevas")
@app_commands.describe(cantidad="Cantidad de keys (máximo 50)")
@app_commands.checks.has_permissions(administrator=True)
async def generate_keys(interaction: discord.Interaction, cantidad: int = 5):
    if cantidad < 1 or cantidad > 50:
        return await interaction.response.send_message("❌ Solo puedes generar entre 1 y 50 keys.", ephemeral=True)

    nuevas = []
    for _ in range(cantidad):
        key = secrets.token_hex(8).upper()
        data["keys"][key] = {
            "used": False,
            "created_at": datetime.utcnow().isoformat(),
            "used_by": None,
            "used_at": None
        }
        nuevas.append(key)
    save_data(data)

    texto = "\n".join(nuevas)
    await interaction.response.send_message(f"✅ {cantidad} keys generadas:\n```\n{texto}\n```", ephemeral=True)

@bot.tree.command(name="whitelist", description="Dar acceso a Get Script sin key")
@app_commands.describe(usuario="Usuario al que le das acceso")
@app_commands.checks.has_permissions(administrator=True)
async def whitelist(interaction: discord.Interaction, usuario: discord.Member):
    user_id = str(usuario.id)
    if user_id in data["whitelist"]:
        return await interaction.response.send_message(f"⚠️ {usuario.mention} ya está whitelisted.", ephemeral=True)

    data["whitelist"][user_id] = {
        "key": None,
        "redeemed_at": datetime.utcnow().isoformat(),
        "method": "manual"
    }
    save_data(data)

    if CUSTOMER_ROLE_ID:
        role = interaction.guild.get_role(CUSTOMER_ROLE_ID)
        if role:
            try:
                await usuario.add_roles(role)
            except:
                pass

    await interaction.response.send_message(f"✅ {usuario.mention} ahora puede usar **Get Script**.", ephemeral=True)

@bot.tree.command(name="unwhitelist", description="Quitar acceso a Get Script")
@app_commands.describe(usuario="Usuario al que le quitas el acceso")
@app_commands.checks.has_permissions(administrator=True)
async def unwhitelist(interaction: discord.Interaction, usuario: discord.Member):
    user_id = str(usuario.id)
    if user_id not in data["whitelist"]:
        return await interaction.response.send_message(f"⚠️ {usuario.mention} no está whitelisted.", ephemeral=True)

    del data["whitelist"][user_id]
    save_data(data)
    await interaction.response.send_message(f"✅ Se le quitó el acceso a {usuario.mention}.", ephemeral=True)

bot.run(TOKEN)

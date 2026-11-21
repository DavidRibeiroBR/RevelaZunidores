 <div align="center">

<h1>RevelaZunidores</h1>

<p><strong>Collectible Finder for Atomic Heart (Base Game + All DLCs)</strong></p>

<p>
  <a href="https://davidribeirobr.github.io/RevelaZunidores/">
    <img src="https://img.shields.io/badge/🌐_OPEN_PROJECT_PAGE-Guides_%26_Interactive_Docs_(EN_%2F_PT--BR)-d9383a?style=for-the-badge" alt="Open Project Page" height="42">
  </a>
</p>

<p>
  <a href="https://www.nexusmods.com/atomicheart/mods/277">
    <img src="https://img.shields.io/badge/Nexus_Mods-Download-da8e35?style=for-the-badge&logo=nexusmods&logoColor=white" alt="Nexus Mods" height="28">
  </a>
  &nbsp;&nbsp;
  <a href="https://github.com/DavidRibeiroBR/RevelaZunidores/tags">
    <img src="https://img.shields.io/badge/GitHub-Tags_%26_Source-181717?style=for-the-badge&logo=github&logoColor=white" alt="GitHub Tags" height="28">
  </a>
</p>

</div>

> **💡 Tip:** Visit the **[Interactive Project Page](https://davidribeirobr.github.io/RevelaZunidores/)** for installation guides, keybinds, changelog, and instant **EN / PT-BR** language switching.

---

Collectible finder for **Atomic Heart** (base game + DLCs). It displays the locations of collectibles on the current map, including Chirpers, talking corpses, Testing Ground crates, weapon blueprints, Limbo apples and coins, DLC4 statuettes, and more.

English is the default language. Portuguese (Brazil) is also available.

## Parts

| Folder / File | Description |
|---|---|
| `RevelaZunidores/` | UE4SS Lua mod (`Scripts/`) and an optional desktop menu window (`menu/`, Python) |
| `reshade_addon/` | ReShade add-on (`RevelaZunidores.addon64`) for the in-game overlay, including its C++ source |
| `MemberVariableLayout.ini` | UE4SS member layout for Atomic Heart's modified UE 4.27 |
| `UE4SS_Signatures/` | Signature overrides for UE4SS (ConsoleManager, StaticConstructObject) |
| `UE4SS-settings.ini` | UE4SS configuration for Atomic Heart (`FExecVTableOffsetInLocalPlayer = 0x30`, hot reload and console settings) |

## Requirements

- [UE4SS](https://github.com/UE4SS-RE/RE-UE4SS) v4.0.0
- [ReShade](https://reshade.me/) with add-on support (tested with 6.8.0 Addon) — required for the overlay
- Python 3 — required only for the optional desktop menu window

---

# 📖 Installation Guide — RevelaZunidores

## 🎥 Installation Video

[▶️ Watch the installation tutorial on YouTube](https://youtu.be/NxZAhpDcAh0)

---

<details>
<summary><strong>📥 STEP 0 — Downloads & Preparation</strong></summary>

<br>

1. Download and extract the **RevelaZunidores** mod ZIP from GitHub.
2. Download and extract the **UE4SS** ZIP from GitHub.
3. Install **ReShade 6.8.0** using the **Full Add-on Support** version. Run `ReShade_Setup_6.8.0_Addon.exe`, select `AtomicHeart-Win64-Shipping.exe`, and click **Next** until the installation is complete.

</details>

---

<details>
<summary><strong>⚙️ STEP 1 — Installing UE4SS v4.0.0</strong></summary>

<br>

1. Open the extracted `UE4SS_v4.0.0` folder and copy all the files inside it.
2. Paste everything into the game's `Win64` folder:

   ```text
   Atomic Heart\AtomicHeart\Binaries\Win64
   ```

</details>

---

<details>
<summary><strong>🛠️ STEP 2 — Mod Setup (RevelaZunidores)</strong></summary>

<br>

### 📌 Part 1 — Configuration Files

1. Inside the extracted mod folder, copy the following files and folder:

   - `MemberVariableLayout.ini`
   - `UE4SS-settings.ini`
   - `UE4SS_Signatures` (folder)

2. Navigate to the `ue4ss` folder inside your game directory:

   ```text
   Atomic Heart\AtomicHeart\Binaries\Win64\ue4ss
   ```

3. Paste the copied files and folder into this directory.
4. Select **Replace the files in the destination** when prompted.

---

### 📌 Part 2 — Enabling the Mod

1. Inside the extracted `RevelaZunidores-1.0.1` folder, locate and copy the `RevelaZunidores` folder.
2. Navigate to the UE4SS `Mods` folder:

   ```text
   Atomic Heart\AtomicHeart\Binaries\Win64\ue4ss\Mods
   ```

3. Paste the `RevelaZunidores` folder inside.
4. Open the newly copied `RevelaZunidores` folder and create an empty file named `enabled.txt`.

</details>

---

<details>
<summary><strong>🖥️ STEP 3 — On-Screen Icons (ReShade Add-on)</strong></summary>

<br>

1. Go back to the extracted `RevelaZunidores-1.0.1` folder.
2. Open the `reshade_addon` folder.
3. Copy the `RevelaZunidores.addon64` file.
4. Paste it into the game's `Win64` folder:

   ```text
   Atomic Heart\AtomicHeart\Binaries\Win64
   ```

</details>

---

<details>
<summary><strong>⚠️ Troubleshooting</strong></summary>

<br>

If the mod does not work correctly, double-check that:

- UE4SS was installed in the correct directory.
- The configuration files were replaced correctly.
- The `RevelaZunidores` folder is inside `ue4ss\Mods`.
- The `enabled.txt` file was created correctly.
- The ReShade add-on was copied into the game's `Win64` folder.

</details>

---

<sub>Enjoy using RevelaZunidores!</sub>

---

## 🎮 In-Game Controls

| Key | Action |
|---|---|
| F5 | Switch between categories |
| F6 | Export the map's actor classes to `classes.txt` |
| F7 | Export the selected category's items to `encontrados.txt` and the console |
| F8 | Teleport to the next item in the selected category |
| Ctrl+R | Reload all UE4SS mods |

## ⚙️ Settings

Edit `RevelaZunidores/Scripts/config.lua`:

- `IDIOMA = "en"` (default) or `"pt-BR"`.
- `DISTANCIA_PADRAO_M`: default display distance in meters. Each category can override it using `distancia`. Set to `0` for unlimited distance.
- Categories, class keywords, and reference counts can also be configured.

Distance and language can be changed at runtime through the desktop menu window and the ReShade overlay.

## 🔨 Building the ReShade Add-on

Requires Visual Studio 2022 Build Tools with C++ support.

- Build: `reshade_addon/compilar.bat`
- Tests: `reshade_addon/teste/testar.bat`

## 📋 Changelog

### 1.0.1

- **Steam overlay compatibility:** Shift+Tab works again. The bundled `UE4SS-settings.ini` no longer opens the UE4SS debug window (`GuiConsoleEnabled = 0`), which previously interfered with the Steam overlay.
- **Category-specific marker limits:** Marker and compass limits can now be configured per category. This prevents categories with many nearby items (such as Limbo apples) from hiding other selected categories.
- **Faster marker initialization:** Markers appear within seconds of loading a save. The mod repeats the full scan every 3 seconds while the level is loading instead of waiting 60 seconds.
- **ReShade distance fallback:** The ReShade add-on uses a 500 m distance limit when the mod does not provide a category-specific distance, instead of using unlimited distance.

### 1.0.0

- First release.

## 📦 Third-Party Files

`reshade_addon/sdk/` contains headers from:

- [ReShade SDK](https://github.com/crosire/reshade) — BSD 3-Clause License
- [Dear ImGui](https://github.com/ocornut/imgui) — MIT License

These components are distributed under their respective licenses.

---

## 🇧🇷 Português (Brasil)

Localizador de colecionáveis para **Atomic Heart** (jogo base + DLCs). Exibe a localização dos colecionáveis do mapa atual, incluindo Chirpers, cadáveres falantes, caixas dos Testing Grounds, projetos de armas, maçãs e moedas do Limbo, estatuetas do DLC4 e muito mais.

O inglês é o idioma padrão. O português (Brasil) também está disponível.

Para utilizar o mod em português, defina `IDIOMA = "pt-BR"` no arquivo `config.lua`, ou altere o idioma diretamente pela janela de menu ou pelo overlay do ReShade.

Acesse a [página interativa do projeto](https://davidribeirobr.github.io/RevelaZunidores/) para consultar os guias de instalação, controles, changelog e alternar instantaneamente entre EN e PT-BR.

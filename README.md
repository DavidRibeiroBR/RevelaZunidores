# RevelaZunidores

Collectible finder for **Atomic Heart** (base game + DLCs). It shows where the collectibles of the current map are: Chirpers, talking corpses, Testing Ground crates, weapon blueprints, Limbo apples and coins, DLC4 statuettes and more.

English is the default language. Portuguese (Brazil) is available as an option.

## Download
| Platform | Package |
| :--- | :--- |
| [Nexus Mods](https://www.nexusmods.com/atomicheart/mods/277) | Ready-to-install `.zip` |
| [GitHub Releases](https://github.com/DavidRibeiroBR/RevelaZunidores/releases/latest) | Ready-to-install `.zip` |

*(Ready-to-install `.zip` archives)*

## Parts

| Folder | What it is |
|---|---|
| `RevelaZunidores/` | UE4SS Lua mod (`Scripts/`) and an optional desktop menu window (`menu/`, Python) |
| `reshade_addon/` | ReShade add-on (`RevelaZunidores.addon64`) that draws the in-game overlay, plus its C++ source |
| `MemberVariableLayout.ini` | UE4SS member layout for Atomic Heart's modified UE 4.27 |
| `UE4SS_Signatures/` | Signature overrides for UE4SS (ConsoleManager, StaticConstructObject) |
| `UE4SS-settings.ini` | UE4SS settings for Atomic Heart (`FExecVTableOffsetInLocalPlayer = 0x30`, hot reload and console on) |

## Requirements

- [UE4SS](https://github.com/UE4SS-RE/RE-UE4SS) v4.0.0
- [ReShade](https://reshade.me) with add-on support (tested with 6.8.0 Addon), for the overlay
- Python 3, only for the optional menu window

## Install

All paths are relative to `AtomicHeart/Binaries/Win64/`.

1. Install UE4SS in the game.
2. Copy `MemberVariableLayout.ini`, `UE4SS-settings.ini` and the `UE4SS_Signatures` folder into the UE4SS folder (next to `UE4SS.dll`). If you keep your own settings file, set `FExecVTableOffsetInLocalPlayer = 0x30`.
3. Copy the `RevelaZunidores` folder into UE4SS's `Mods/` folder and enable it (`mods.txt` or an `enabled.txt` file inside the mod folder).
4. Optional: install ReShade (add-on version) for the game and copy `reshade_addon/RevelaZunidores.addon64` next to the game executable.
5. Optional: open the menu with `RevelaZunidores/menu/Abrir menu.bat`.

## Keys in game

| Key | Action |
|---|---|
| F5 | Switch category |
| F6 | List the map's actor classes in `classes.txt` |
| F7 | List the category's items in `encontrados.txt` and the console |
| F8 | Teleport to the next item of the category |
| Ctrl+R | Reload all mods (UE4SS) |

## Settings

Edit `RevelaZunidores/Scripts/config.lua`:

- `IDIOMA = "en"` (default) or `"pt-BR"`.
- `DISTANCIA_PADRAO_M`: default display distance in meters. Each category can override it with `distancia`. `0` means no limit.
- Categories, class keywords and reference counts.

Distance and language can also be changed live in the menu window and in the ReShade overlay.

## Building the ReShade add-on

Needs Visual Studio 2022 Build Tools with C++. Run `reshade_addon/compilar.bat`. Tests: `reshade_addon/teste/testar.bat`.

## Changelog

**1.0.1**
- Steam overlay (Shift+Tab) works again: the bundled `UE4SS-settings.ini` no longer opens the UE4SS debug window (`GuiConsoleEnabled = 0`), which took over the overlay.
- Markers and compass are limited per category ("Max. markers per category"), so a category with many nearby items (Limbo apples) no longer hides the other checked categories.
- Markers show up seconds after loading a save: the mod repeats the full scan every 3 s while the level is still loading, instead of waiting 60 s.
- The ReShade add-on uses 500 m, never "no limit", when the mod does not send a category distance.

**1.0.0**
- First release.

## Third-party files

`reshade_addon/sdk/` contains headers from the [ReShade SDK](https://github.com/crosire/reshade) (BSD 3-Clause) and [Dear ImGui](https://github.com/ocornut/imgui) (MIT), under their own licenses.

---

## Português (Brasil)

Localizador de colecionáveis para **Atomic Heart** (jogo base + DLCs). Mostra onde estão os colecionáveis do mapa atual. A instalação segue os passos acima. Para usar em português, defina `IDIOMA = "pt-BR"` no `config.lua`, ou troque o idioma na janela de menu ou no ReShade.

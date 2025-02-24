# No Mans Sky Base Builder

<p align="center" style="font-size:26px">
  <img src="https://raw.githubusercontent.com/djmonkeyuk/nms-base-builder/master/images/CommunityBadge.png" alt="No Mans Sky"  width="50%">
  <br />
A plugin for Blender to build bases in No Mans Sky.<br />
<span style="font-size:18">Community Discord: <a href="https://discord.gg/kpGVRKPn5W">https://discord.gg/kpGVRKPn5W</a></span>
</p>



<p align="center">
  <a href="#key-features">Key Features</a> •
  <a href="#requirements">Requirements</a> •
  <a href="#how-to-use">Installation & How To Use</a> •
  <a href="#credits">Credits & Support</a> •
  <a href="#screenshots">Screenshots</a> •
  <a href="#community_screenshots">Community Showcase</a>
</p>

<a name="key-features"></a>
## Key Features

* Build bases for No Mans Sky using proxy representations for building parts.
* Translate, rotate and scale any base part to any position and any size!
* Define presets to build complex items quickly. Share or download presets online.
* Save and Load bases to disk (.json format).
* Import and Export back and forth from the game using the No Mans Sky Save Editor.
* Snapping features help with the placement of base parts. Similar to the snapping features in-game.
* A Power and Logic UI panel helps manage electricity and switches.
* An asset browser for searching and locating base parts.

<p align="center" style="font-size:26px">
<img src="https://raw.githubusercontent.com/djmonkeyuk/nms-base-builder/master/images/AssetBrowser.jpg" alt="No Mans Sky"  width="75%">
</p>


<a name="requirements"></a>
## Requirements

* Latest Base Builder Release
    * https://github.com/djmonkeyuk/nms-base-builder/releases
* No Mans Sky Save Editor
    * https://nomansskymods.com/mods/no-mans-sky-save-editor
* Blender
    * https://www.blender.org
* The Latest Python 3 version.
    * Install using Windows Store, or from https://www.python.org
* bpy_externall addon. Installed and enabled in Blender.
    * https://github.com/djmonkeyuk/bpy_externall/tree/blender4-patch

<br />


<a name="how-to-use"></a>

## Installation and How To Use

### Videos
* **Installation** Video: https://youtu.be/TZKMGhNNFJQ
* **Getting started** video: https://www.youtube.com/watch?v=qXcguoROM-A
* How to use **presets** video: https://www.youtube.com/watch?v=BFIvRH5-S0I&t
* How to do **snapping** video: https://youtu.be/1I3KDRiSTW8
* How to manage **power and electricity** video: https://www.youtube.com/watch?v=jDascUR4NPA
* Frontiers update and using the **Asset Browser** video : https://youtu.be/TZKMGhNNFJQ

### Installation Steps

See video above for installation guide, otherwise follow these steps.

1. Download and install all the necessary requirements from the Requirements section.
2. Download the latest release. (https://github.com/djmonkeyuk/nms-base-builder/releases)
3. Open "User Preferences" in Blender.
4. Go to the Add-ons tab.
5. Click "Install Add-on from File..." at the bottom of the window.
6. Select the downloaded zip file.
7. Enable the Addon in the list.
7. In the right side panel of the viewport, click the "No Man's Sky" tab. If this is not visible then clicking the tiny triangle will expand the panel.


## Preset Location

Presets are stored in your "**%USERPROFILE%\NoMansSkyBaseBuilder\presets**" directory.
These can be downloaded and shared with other people.

View the Preset directory to downlaod and share your own creations.
https://djmonkeyuk.github.io/nms-base-builder-presets/

## Technical Dependencies

Casual users may ignore this section. These Python dependencies are installed automatically on execution of the Asset Browser UI.
(Fallback dependencies, in parentheses, won't be.)

* PySide6 (or PySide2)
* PyYAML

For Linux users, the corresponding packages (for Debian-like systems) are:

* python3-pyside6 (or python3-pyside2)
* python3-yaml

## Mod Compatibility

The tool is designed towards supporting the vanilla game as much as possible, however
any additional base parts introduced by mods will display as cubes but will still be able to import/export to the game.

You can introduce your own OBJ's by adding them to your user directory folder. The layout for this should be...

* %USERPROFILE%\NoMansSkyBaseBuilder\
  * mods
    * mod_name
      * models
        * category
          * MOD_WALLA.obj
          * MOD_WALLB.obj
        * category_b
          * MOD_FLOORA.obj
          * MOD_FLOORB.obj

The names of categories is up to the user.

The obj file name should reflect the name of the part in-game.

<a name="credits"></a>

## Credits & Support

Created and maintained by DjMonkey. You can reach out via various social media channels:

* Discord: <a href="https://discord.gg/kpGVRKPn5W">https://discord.gg/kpGVRKPn5W</a>
* Threads: <a href="https://www.threads.net/@dancingmoongame" target="_blank">@dancingmoongame</a>
* Twitter/X: <a href="https://www.x.com/@dancingmoongame" target="_blank">@DancingMoonGame</a> or <a href="https://www.x.com/@charliebanks" target="_blank">@charliebanks</a>
* BlueSky: <a href="https://bsky.app/profile/djmonkeyuk.bsky.social" target="_blank">@djmonkeyuk.bsky.social</a>

## Play my Indie Game!

If you have enjoyed using my tools, consider playing my very own indie game! It is the best way you can support me!

> <i>'Tales from the Dancing Moon' is a life-sim RPG set in a parallel universe inspired by UK culture and fantasy novels. After the events of a shadow-beast invasion on a seaside town, complete villager quests and collect hidden diaries to understand your role in this mysterious character-driven story.</i>

There is a <a href="https://store.steampowered.com/app/1782420/Tales_from_The_Dancing_Moon/" target="_blank">FREE demo</a> and an Early Access version. You would help me a lot by either wishlisting it, trying it out, or even sharing it with your friends!

Click the image below to be taken to the Steam page!

<p align="center">
  <a href="https://store.steampowered.com/app/1782420/Tales_from_The_Dancing_Moon/" target="_blank"><img src="https://raw.githubusercontent.com/djmonkeyuk/nms-base-builder/master/images/SteamDemoBanner.png" alt="Tales from The Dancing Moon Steam Store Page" width="50%"></a>
</p>


<a name="screenshots"></a>
## Screenshots

<p align="center">
  <img src="https://raw.githubusercontent.com/djmonkeyuk/nms-base-builder/feature/blender2.8/images/blender_showcase.png" alt="NMS1" width="100%">
</p>

<a name="community_screenshots"></a>
## Community Showcase

**/u/ashfacta**
<p align="center">
  <img src="https://raw.githubusercontent.com/djmonkeyuk/nms-base-builder/feature/blender2.8/images/casino.jpg" alt="Casino" width="24%">
  <img src="https://raw.githubusercontent.com/djmonkeyuk/nms-base-builder/feature/blender2.8/images/airship.jpg" alt="Air Ship" width="24%">
  <img src="https://raw.githubusercontent.com/djmonkeyuk/nms-base-builder/feature/blender2.8/images/drop_ship.jpg" alt="Drop Ship" width="24%">
  <img src="https://raw.githubusercontent.com/djmonkeyuk/nms-base-builder/feature/blender2.8/images/skygate.jpg" alt="Sky Gate" width="24%">
</p>

**/u/258100**
<p align="center">
  <img src="https://raw.githubusercontent.com/djmonkeyuk/nms-base-builder/feature/blender2.8/images/starwars.jpg" alt="Star Wars" width="24%">
  <img src="https://raw.githubusercontent.com/djmonkeyuk/nms-base-builder/feature/blender2.8/images/titanic.jpg" alt="Titanic" width="24%">
  <img src="https://raw.githubusercontent.com/djmonkeyuk/nms-base-builder/feature/blender2.8/images/notre_dam.png" alt="ND" width="24%">
  <img src="https://raw.githubusercontent.com/djmonkeyuk/nms-base-builder/feature/blender2.8/images/castle.png" alt="Castle" width="24%">
</p>

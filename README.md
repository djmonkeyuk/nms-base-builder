# No Mans Sky Base Builder

<p align="center" style="font-size:26px">
  <img src="https://raw.githubusercontent.com/charliebanks/nms-base-builder/master/images/logo_large.png" alt="No Mans Sky"  width="50%">
  <br />
A plugin for Blender 2.8 to build bases in No Mans Sky.
</p>



<p align="center">
  <a href="#key-features">Key Features</a> •
  <a href="#requirements">Requirements</a> •
  <a href="#how-to-use">Installation & How To Use</a> •
  <a href="#credits">Credits & Support</a> •
  <a href="#examples">Examples</a>
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


<br />

<a name="requirements"></a>
## Requirements
* Latest Base Builder Release (https://github.com/charliebanks/nms-base-builder/releases)
* No Mans Sky Save Editor (https://nomansskymods.com/mods/no-mans-sky-save-editor/)
* Blender 2.8 (https://www.blender.org/)
<br />

<a name="how-to-use"></a>

## Installation and How To Use

### Vidoes
* **Installation** Video: https://www.youtube.com/watch?v=_zN82oueFTE
* **Getting started** video: https://www.youtube.com/watch?v=qXcguoROM-A
* How to use **presets** video: https://www.youtube.com/watch?v=BFIvRH5-S0I&t
* How to do **snapping** video: https://youtu.be/1I3KDRiSTW8
* How to manage **power and electricity** video: https://youtu.be/1I3KDRiSTW8

### Installation Steps

See video above for installation guide, otherwise follow these steps.

2. Download the latest release. (https://github.com/charliebanks/nms-base-builder/releases)
3. Open "User Preferences" in Blender.
4. Go to the Add-ons tab.
5. Click "Install Add-on from File..." at the bottom of the window.
6. Select the downloaded zip file.
7. In the right side panel of the viewport, click the "No Man's Sky" tab.


## Preset Location

Presets are stored in your "**%USERPROFILE%\NoMansSkyBaseBuilder\presets**" directory.
These can be downloaded and shared with other people. You can find a few basic presets I've made on the nexus
mod page - https://www.nexusmods.com/nomanssky/mods/984?tab=files.

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

Created and maintained by.

* Charlie Banks (<a href="http://www.twitter.com/charliebanks" target="_blank">@charliebanks</a>)

Feel free to get in touch :)

<a name="examples"></a>
## Examples
<p align="center">
  <img src="https://raw.githubusercontent.com/charliebanks/nms-base-builder/feature/blender2.8/images/blender_poster.jpg" alt="NMS" width="100%">
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/charliebanks/nms-base-builder/feature/blender2.8/images/blender_showcase.png" alt="NMS1" width="100%">
</p>

<a name="examples"></a>
## Community Screenshots

**/u/ashfacta**
<p style="float: left;">
  <img float="left" src="https://raw.githubusercontent.com/charliebanks/nms-base-builder/feature/blender2.8/images/casino.jpg" alt="Casino" width="25%">
  <img src="https://raw.githubusercontent.com/charliebanks/nms-base-builder/feature/blender2.8/images/airship.jpg" alt="Air Ship" width="25%">
  <img src="https://raw.githubusercontent.com/charliebanks/nms-base-builder/feature/blender2.8/images/drop_ship.jpg" alt="Drop Ship" width="25%">
  <img src="https://raw.githubusercontent.com/charliebanks/nms-base-builder/feature/blender2.8/images/skygate.jpg" alt="Sky Gate" width="25%">
</p>

**/u/258100**
<p style="float: left;">
  <img float="left" src="https://raw.githubusercontent.com/charliebanks/nms-base-builder/feature/blender2.8/images/starwars.jpg" alt="Star Wars" width="25%">
  <img float="left" src="https://raw.githubusercontent.com/charliebanks/nms-base-builder/feature/blender2.8/images/titanic.jpg" alt="Titanic" width="25%">
  <img float="left" src="https://raw.githubusercontent.com/charliebanks/nms-base-builder/feature/blender2.8/images/notre_dam.jpg" alt="ND" width="25%">
  <img float="left" src="https://raw.githubusercontent.com/charliebanks/nms-base-builder/feature/blender2.8/images/castle.png" alt="Castle" width="25%">
</p>

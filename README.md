# No Mans Sky Base Builder

<p align="center" style="font-size:26px">
  <img src="https://raw.githubusercontent.com/charliebanks/nms-base-builder/master/images/logo_large.png" alt="No Mans Sky"  width="50%">
  <br />
A plugin for Blender to build bases in No Mans Sky.
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
* Complete freedome of movement when placing building parts - want something upside down? Up in the air? You can place it that way!
* Define presets to build complex items quickly. Share or download presets online.
* Save and Load bases to disk (.json format).
* Import and Export base data compatable with the No Mans Sky Save Editor.
* Snapping features help with placement of parts similar to how No Man's Sky positions parts.


<br />

<a name="requirements"></a>
## Requirements
* Latest Base Builder Release (https://github.com/charliebanks/nms-base-builder/releases)
* No Mans Sky Save Editor (https://nomansskymods.com/mods/no-mans-sky-save-editor/)
* Blender (https://www.blender.org/)
<br />

<a name="how-to-use"></a>

## Installation and How To Use

### Vidoes
* Installation Video: https://www.youtube.com/watch?v=_zN82oueFTE
* Simple Use Video: https://www.youtube.com/watch?v=qXcguoROM-A
* How to use Presets Video: https://www.youtube.com/watch?v=BFIvRH5-S0I&t
* How to do Snapping Video: https://youtu.be/1I3KDRiSTW8

### Written Steps
1. Download the latest release. (https://github.com/charliebanks/nms-base-builder/releases)
2. Open "User Preferences" in Blender.
3. Go to the Add-ons tab.
4. Click "Install Add-on from File..." at the bottom of the window.
5. Select the downloaded zip file.

## Presets

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
  <img src="https://raw.githubusercontent.com/charliebanks/nms-base-builder/master/images/nms_base_builder.jpg" alt="NMS" width="100%">
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/charliebanks/nms-base-builder/master/images/example_1.jpg" alt="NMS1" width="100%">
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/charliebanks/nms-base-builder/master/images/example_2.jpg" alt="NMS2" width="100%">
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/charliebanks/nms-base-builder/master/images/example_4.jpg" alt="NMS3" width="100%">
</p>
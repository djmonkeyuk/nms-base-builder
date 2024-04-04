release 2.1.0
-------------

* Fixed errors when using Blender 4.0
* Base parts up to date as of ORBITAL update.

release 2.0.5
-------------

* Fixed a bug where some scaled parts were being assigned a random color.

release 2.0.4
-------------

* Added model support for Timber, Alloy and Stone variant pieces.


release 2.0.3
-------------

* Added some automation scripts for updating this tool.
* Added a bunch of missing objects since the last year (Expeditions/Sentinel/Outlaws/Endurance/Waypoint).
* Thanks to Peter Laan for assistance with missing parts and their source file locations.


release 2.0.2
-------------

* Simplified Qt Dependencies. (Swapped to PySide6)
* Compatible with latest Python 3.10 and Blender 3.0 versions.


release 2.0.1
-------------

* Fixed an issue where loading a base using presets would error.
* Small fixes to asset naming and categorization in the Asset Browser.


release 2.0.0
-------------

* Added over 250 new parts to support the FRONTIERs update.
* Fixed issues with cable placement logic introduced with FRONTIERS.
* Added a new Asset Browser UI for better browsing on building parts. (See readme and video tutorials for more information.)
* Added category support for Presets. The tool will now recognise sub-folders within the user Preset folder.
* Added a button to apply the default colour to a base part.
* A fancy new logo.


release 1.3.3
-------------

Thanks to Wormhole Badger (@MarkAlanSwann1) for supplying the proxy models for
this update.

* Added a Fireworks category with firework items.
* Added support for the following items.
    * Unlockables
        * BASE_HOUDINI1
        * BASE_HOUDINI2
        * BASE_HOUDINI3
        * BASE_INFEST1
        * BASE_INFEST2
        * BASE_INFEST3
        * BASE_LAVA1
        * BASE_LAVA2
        * BASE_LAVA3
        * BASE_SWAMP1
        * BASE_SWAMP2
        * BASE_SWAMP3
        * BASE_TOYJELLY
        * SLIME_MED
        * SPOOKY_PLANT
        * SPEC_FIREWORK01
        * SPEC_FIREWORK02
        * SPEC_FIREWORK03
        * SPEC_FIREWORK04
        * SPEC_FIREWORK05
        * SPEC_FIREWORK06


release 1.3.2
-------------

* Added the Derelict Freighter Turret as a buildable item.
* Added some window and door items to the visibility ghost list.
* Changed blender ops naming from "nms." to "object.nms_".
* Added more snapping positions so walls can be snapped below floors.
* Complete rework of triangle pieces.
    * Triangles are now the correct size.
    * 3D model updated to better represent part, with indication of the direction of the triangle.
    * Fixed snapping points on triangle pieces.
* Renamed Parts...
    * BASE_HOTPLANT1 > * BASE_HOTPLANT01
    * BASE_HOTPLANT2 > * BASE_HOTPLANT02
    * BASE_HOTPLANT3 > * BASE_HOTPLANT03
* Added support for the following models ...
    * Freighter
        * TURRET_ABAND - Freighter Turret
* Fixed a power connection position on the Light Floor (credit: @bjj)
* "Connect" can now operate on multiple selections. (credit: @bjj)
* Added a "Select Connected" button to the Power Tooling (credit: @bjj)
* Added a "Select Floating" button to the Power Tooling (credit: @bjj)
* Fixed a power line division bug (credit: @bjj)
* Material clears when importing OBJs. (credit: @bjj)
* Power Controllers now created at the 3D cursor position. (credit: @bjj)


release 1.3.1
-------------

* Added `bl_options = {"UNDO", "REGISTER"}` everywhere required.
* Changed material colour of U_PORTALLINE.
* Added .gitignore file.


release 1.3.0
-------------

* Fixed some Blender error messages when interacting with non-NMS scene items.
* Missing/Modded parts will be named their ID instead of "cube".
* New models for C_ROOF, M_ROOF
* Added support for the following models ...
    * Freighter
        * ABAND_BARREL - Industrial Barrel
        * ABAND_BENCH - Industrial Bench
        * ABAND_CASE - Secure Briefcase
        * ABAND_CRATE_L - Storage Unit
        * ABAND_CRATE_M - Salvage Crate
        * ABAND_CRATE_XL - Large Storage
        * ABAND_SHELF - Heavy-Duty Furniture
        * FOORLIGHT - Emergency Light
        * FOOTLOCKER - Crew Footlocker
        * HEATER - Emergency Heater
        * LOCKER2 - Crew Locker
        * MEDTUBE - Sample Container
        * PALLET - Industrial Pallet
        * PLANTTUBE - Floral Cannister


release 1.2.1
-------------

* Fixed naming of BUILDCHAIR.
* Fixed a model positioning issue with NPCFRIGTERM.
* Added snapping positions for Plants, Platers and Bioroom.
* Adjusted scaling for gold, silver and bronze statues.
* Added support for the following models ...(with help from @DevilinPixy)
    * Main
        * PANEL_GLASS
    * Decoration
        * STATUE_DIP_B
        * STATUE_DIP_S
        * STATUE_DIP_G
    * Exocraft
        * GARAGE_MECH
    * Technology
        * POWERLINE_HIDER
        * BUILDHARVESTER
    * Farming
        * TOXICPLANT
        * SNOWPLANT
        * SCORCHEDPLANT
        * SACVENOMPLANT
        * RADIOPLANT
        * POOPPLANT
        * PEARLPLANT
        * NIPPLANT
        * GRAVPLANT
        * LUSHPLANT
        * BARRENPLANT
        * CREATUREPLANT
    * Freighter
        * GARAGE_FREIGHT
        * S_CONTAINER0
        * S_CONTAINER1
        * S_CONTAINER2
        * S_CONTAINER3
        * S_CONTAINER4
        * S_CONTAINER5
        * S_CONTAINER6
        * S_CONTAINER7
        * S_CONTAINER8
        * S_CONTAINER9
    * Unlockables
        * BASE_BEAMSTONE
        * BASE_BUBBLECLUS
        * BASE_COLDPLANT1
        * BASE_COLDPLANT2
        * BASE_COLDPLANT3
        * BASE_CONTOURPOD
        * BASE_DUSTPLANT1
        * BASE_DUSTPLANT2
        * BASE_DUSTPLANT3
        * BASE_ENGINEORB
        * BASE_HOTPLANT1
        * BASE_HOTPLANT2
        * BASE_HOTPLANT3
        * BASE_HYDROPOD
        * BASE_MEDGEOMETR
        * BASE_MEDPLANT01
        * BASE_MEDPLANT02
        * BASE_MEDPLANT03
        * BASE_RADPLANT01
        * BASE_RADPLANT02
        * BASE_RADPLANT03
        * BASE_ROBOTOY
        * BASE_ROCK01
        * BASE_ROCK02
        * BASE_ROCK03
        * BASE_SHARD
        * BASE_SHELLWHITE
        * BASE_STARJOINT
        * BASE_TOXPLANT01
        * BASE_TOXPLANT02
        * BASE_TOXPLANT03
        * BASE_WEIRDCUBE
        * BASE_WPLANT1
        * BASE_WPLANT2

release 1.2.0
-------------

* Added support for the decal items.
* Added models for...
    * BUILDDECAL
    * BUILDDECAL2
    * BUILDDECALNMS
    * BUILDDECALNUM0
    * BUILDDECALNUM1
    * BUILDDECALNUM2
    * BUILDDECALNUM3
    * BUILDDECALNUM4
    * BUILDDECALNUM5
    * BUILDDECALNUM6
    * BUILDDECALNUM7
    * BUILDDECALNUM8
    * BUILDDECALNUM9
    * BUILDDECALSIMP1
    * BUILDDECALSIMP2
    * BUILDDECALSIMP3
    * BUILDDECALSIMP4
    * BUILDDECALVIS1
    * BUILDDECALVIS2
    * BUILDDECALVIS3
    * BUILDDECALVIS4
    * BUILDDECALVIS5
    * SPEC_DECAL01
    * SPEC_DECAL02
    * SPEC_DECAL03
    * SPEC_DECAL04
    * SPEC_DECAL05
    * SPEC_DECAL06
    * SPEC_DECAL07
    * SPEC_DECAL08

release 1.1.9
-------------

* Updated Add-on information for Blender 2.82
* Added missing Half Metal Arch object.
* Added missing power connection to Garage Wall items.
* Added missing power connections to Light Posts.
* Added missing power connection to Byte Beat Switch.
* Enabled message capturing on Byte Beat Switch.
* Added some snapping information to the short wall pieces.
* Improved models for...
    * BUILDLIGHT
    * BUILDLIGHT2
    * BUILDLIGHT3
    * BYTEBEATSWITCH
    * C_GDOOR
    * M_GDOOR
    * W_GDOOR
    * C_WALL_Q
    * C_WALL_Q_H
    * M_WALL_Q
    * M_WALL_Q_H
    * W_WALL_Q
    * W_WALL_Q_H

release 1.1.8
-------------

* Arranged the Tools panel into a neater and more compact layout.
* Missing object cube placeholder's are now named after the object ID in the scene.
* Added OBJ add-on as a plugin dependency.


release 1.1.7
-------------

* Added a specific "Delete" button in the tools area that safely removed Base Parts and Presets from the scene.
* BYTEBEAT machines and their configurations are now supported.
    * BYTEBEAT machines and their songs can now be saved as presets and shared with other people.
    * Example: https://djmonkeyuk.github.io/nms-base-builder-presets/Byte%20Beats
* Optimized the creation of wiring controls. Bases with lots of wiring should now load faster.
* Added models for...
    * BYTEBEAT
    * BYTEBEATSWITCH
    * L_FLOOR_Q
    * U_BYTEBEATLINE

release 1.1.6
-------------

* Fixed a rotation accuracy bug when generating presets.
* Preset files now have a time stamp applied to them to help with date sorting in the Preset Directory.
* Improved timestamp data on individual base objects.


release 1.1.5
-------------

* Added support for triangle pieces.

release 1.1.4
-------------

* Support for Blender 2.81.
* Added support for Freighter bases.
    * Added simple model parts for Freighter pieces.
    * Restricted movement of FREIGHTER_CORE, AIRLCKCONNECTOR and BRIDGECONNECTOR.
    * Freighter BaseType key detected on import and kept at export. Planet base key used as default.
    * Added snapping support for Freighter parts.
* Improved snapping information for cube parts.
* Improved snapping information for light/noise boxes.
* Updated import/export functions with new keys and values from NMS version 2.16.
* Added a "Open Preset Folder" button that opens explorer window for quick access to preset .json files.


release 1.1.3
-------------

* Added a "Get More Presets..." button that opens the directory web-page for community made presets.

release 1.1.2
-------------

* Added a 'Build Counter' to the Base Properties panel to show the total number of NMS objects in your scene.
* Fixed communication message modules forgetting messages.
* Fixed the 'X' delete preset button in the preset list.
* Apply radian rotation values when snapping objects for better accuracy.
    (which fixes some cases where small offsets were being applied to snap positions)
* Fixed an issue where objects weren't remembering their snapped partner object when they don't have matching snap points.
* Added socket model and power connection to CONTAINER objects.
* Added CONTAINER7.
* Added Infrastructure Ladder.
* Added Oscilloscope.


release 1.1.1
-------------

* Fixed preset folder creation for new users.


release 1.1.0
-------------

* General
    * Further improvements to Blender 2.8 support.
    * Vastly improved loading times for base and preset generation.
    * Added more custom warnings and error messages so the user encounters less Python trace-back errors.
    * Removed the default Blender Cube, Light and Camera when generating bases.
    * Ensured all items fit under the default "Collection" in the Outliner.
    * Fixed the transparent shader being applied to all items instead of just structural items as intended.
    * Turned off relationship lines by default.
    * Part and Preset list search bar to always be visible.
    * Base parts are now listed alphabetically in the UI list.
* Presets
    * A better control is generated, calculated from the total floor-area of the preset parts.
    * Fixed an issue where presets were not generating properly if more than one instance existed.
* Snapping
    * Snapping an object remembers which object it has previously snapped to.
    * Allows you to use the snap buttons without having to select two items at a time after the initial snap has been done.
    * Updated snap information for BUILDLANDINGPAD.
    * Swapped the selection order when snapping one object to another.
* Power
    * When selecting a point then pressing "New Point". This will automatically create a power line between the new point and the previous point.
    * Added power sockets to farm planter and mega planter.
* Models improvements for...
    * BUILDLANDINGPAD
    * GARAGE_M
    * GARAGE_SUB
    * PLANTER
    * PLANTERMEGA
* Added models for...
    * GARAGE_L
    * GARAGE_S
    * SUMMON_GARAGE
    * RACE_RAMP
    * BASE_TOYCORE
    * BASE_TOYCUBE
    * BASE_TOYSPHERE
    * U_SILO_S
    * CUBEROOF
    * BUILDGASHARVEST
    * STATUE_GEK_B
    * STATUE_GEK_S
    * STATUE_GEK_G
    * STATUE_SHIP_B
    * STATUE_SHIP_S
    * STATUE_SHIP_G
* Code refactor.
    * Restructured object and class hierarchy to something more manageable.
    * Replaced most bpy.ops methods with bpy.data methods.
    * Enhanced the caching mechanism for base part and preset retrieval.
    * Added framework to easily allow custom behavior for specific parts.
    * Categorized utility methods into their own modules.


release 1.0.0
-------------

* Updated code-base to work for Blender 2.8.
* Internal base version updated to 4. Additional save data keys added to export.
* Unlocked scale channels on all base parts as scaling is now supported. Works for ALL base parts.
    * (Use at your own risk, in-game snapping behavior becomes unreliable for base parts not intending to be scaled.)
* Added power socket details to some base part models that require electricity.
* Added a set of features for managing power and electricity.
    * Connect electrical base parts together from the new power UI panel.
    * Snap and cycle wire ends to base part connection points.
    * Divide existing wires into two, creating an additional control.
    * Split existing wires into two, creating a gap with 2 additional controls.
    * Create arbitrary control points to create more complex wire paths.
    * Quickly create logic gates and switches in the logic UI area.
* Fixed a minor matrix offset on wall snap points.
* MAINROOMCUBE and BUILDLANDINGPAD model improvements.
* Fixed and adjusted "nice name" table.
* Added models for...
    * W_GDOOR
    * M_GDOOR
    * C_GDOOR
    * W_ROOF_IC
    * M_ROOF_IC
    * C_ROOF_IC
    * U_BATTERY_S
    * U_EXTRACTOR_S
    * U_GASEXTRACTOR
    * U_GENERATOR_S
    * U_MINIPORTAL
    * CREATURE_FEED
    * CREATURE_FARM
    * COOKER
    * BUILDANTIMATTER
    * U_BIOGENERATOR
    * BUILDTABLE3
    * NOISEBOX
    * LIGHTBOX
    * U_POWERLINE
    * U_PORTALLINE
    * U_PIPELINE


release 0.9.3
-------------
* Refactored module and code structure.
* Faster loading times for bases and presets with OBJ reference cache mechanism (only imports OBJs for first load).
* Improved models for mainrooms.
* Added support for a vast amount of decoration and technology parts: WATERBUBBLE, SHIELDSTATION, HEALTHSTATION, O2_HARVESTER, DRESSING_TABLE, BUILDTERMINAL, FOUNDATION, CRATELRARE, CRATELCYLINDER, MAINROOMFRAME, SMALLLIGHT, BUILDLABLAMP, GARAGE_B, CUBEWINDOWSMALL, CUBEWINDOWOVAL, WALLSCREEN, WALLSCREENB, WALLSCREENB2, WALLFLAG1, WALLFLAG2, WALLFLAG3, WALLFAN, TECHPANEL, STORAGEPANEL, STATUE_WALK_?, STATUE_ASTRO_?, SERVERSTACK, OCTACABINET, FLOORMAT1, DRAWS, BUILDSIDEPANEL, BUILDLIGHTTABLE, BUILDHCABINET, BUILDFLATPLANEL, BUILDCANRACK, BUILDBED, BLDWALLUNIT, BASE_WPLANT3, BASE_TREE03, BASE_MEDPLANT01, BASE_MEDPLANT02, BASE_MEDPLANT03, BASE_BONEGARDEN, BASE_BARNACLE, ?_DOOR_H, ?_DOORWINDOW, ?_DOOR, ?_ARCH_H, ?_ROOF_M, ?_ROOF_C, BASE_TERRARIUM, BASE_AQUARIUM, NPCWEAPONTERM, NPCBUILDERTERM


release 0.9.2
-------------
* Added some legacy base building parts.
* New OBJs for Standing Planter, Walls, Floors, Folding Door, Corner Post.


release 0.9.1
-------------
* Added under water parts to the list.
* Added and improved snap point information and relationships.
* Improved appearance of L shape hallway pieces.
* Implemented first phase of mod support. (see readme for more details.)
* Light objects now create blender lights.
* Improved room visibility switch to display current mode.
* Added "Lighted" as an option on room visibility.


release 0.9.0
-------------
* Added colour options.
* Improved overall UI. Changed to collapsible areas and added button icons.
* Changes to snapping information.
* Added nice name mechanism to base parts.

release 0.8.0
-------------
* Improved and added various models.
* New Snapping area in the tool. With convenient Duplicate button. (Expect some items would not snap yet!)
* Items with compatible snapping will automatically snap on creation.
* Fixed a bug where the tool would disappear when no item was selected.
* Re-organised Basic parts into more granular categories (floors, stairs, walls, etc)


release 0.7.2
-------------
* Improved obj's of CUBEFLOOR, C_WALL_Q_H, BUILDPAVING and BUILDPAVING_BIG.
* Added obj for BUILDSODA2L and CUBESTAIRS.


release 0.7.0
-------------
* Added options for defining and building presets.
* Added large paving, pipe and curved pipe.


release 0.6.0
-------------
* Added a button to toggle between different room visibility. Shown, Ghost and Hidden.
* Added display support for...
    Chairs
    Locker
    Sofas
    Worktop
    Ceiling light
    Cube Inner Doors
    Cube Walls
    Large Desk
    Robotic Arm
    Shelf Panel
    Roof Monitor
    Weapon Rack
    Plant Pot
    Ladder
    Main room Window


release 0.5.0
-------------
* Initial release
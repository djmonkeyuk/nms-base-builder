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
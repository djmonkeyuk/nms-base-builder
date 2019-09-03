release 1.0.0-beta
------------------

* Updated code-base to work for Blender 2.8.
* Interal base version updated to 4. Additional save data keys added to export.
* Unlocked scale channels on all base parts as scaling is now supported. Works for ALL base parts.
    * (Use at your own risk, in-game snapping behaviour becomes unreliable for base parts not intending to be scaled.)
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
* Added support for a vast ammount of decoraton and technology parts: WATERBUBBLE, SHIELDSTATION, HEALTHSTATION, O2_HARVESTER, DRESSING_TABLE, BUILDTERMINAL, FOUNDATION, CRATELRARE, CRATELCYLINDER, MAINROOMFRAME, SMALLLIGHT, BUILDLABLAMP, GARAGE_B, CUBEWINDOWSMALL, CUBEWINDOWOVAL, WALLSCREEN, WALLSCREENB, WALLSCREENB2, WALLFLAG1, WALLFLAG2, WALLFLAG3, WALLFAN, TECHPANEL, STORAGEPANEL, STATUE_WALK_?, STATUE_ASTRO_?, SERVERSTACK, OCTACABINET, FLOORMAT1, DRAWS, BUILDSIDEPANEL, BUILDLIGHTTABLE, BUILDHCABINET, BUILDFLATPLANEL, BUILDCANRACK, BUILDBED, BLDWALLUNIT, BASE_WPLANT3, BASE_TREE03, BASE_MEDPLANT01, BASE_MEDPLANT02, BASE_MEDPLANT03, BASE_BONEGARDEN, BASE_BARNACLE, ?_DOOR_H, ?_DOORWINDOW, ?_DOOR, ?_ARCH_H, ?_ROOF_M, ?_ROOF_C, BASE_TERRARIUM, BASE_AQUARIUM, NPCWEAPONTERM, NPCBUILDERTERM


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
* Improved overall UI. Changed to collapsable areas and added button icons.
* Changes to snapping information.
* Added nice name mechanism to base parts.

release 0.8.0
-------------
* Improved and added various models.
* New Snapping area in the tool. With convenient Duplicate button. (Expect some items would not snap yet!)
* Items with compatible snapping will automatically snap on creation.
* Fixed a bug where the tool would dissapear when no item was selected.
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
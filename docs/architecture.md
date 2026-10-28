# Architecture

## Repository

```
build.py                      build the .wotmod, optionally install it
src/gui/mods/                 Python sources, packed to res/scripts/client/gui/mods/ as .pyc
  mod_sagtary_armor_hits.py   entry point: the game imports it and calls init() / fini()
  sagtary_armor_hits/         code of the mod
resources/                    packed to res/ as they are
  gui/gen_resources/            declarations of the mod's own R.mods.sagtary_armor_hits.* resources
  gui/gameface/mods/sagtary_armor_hits/   Gameface pages, scripts and styles
  gui/maps/sagtary_armor_hits/  images
docs/                         notes
```

The game loads every `gui/mods/mod_*.pyc` and then calls its `init()`; `fini()` runs when the client shuts down.
The entry module only wires the parts together; the code is in the package.

Everything in `res/` is shared by the game and all mods, so this mod keeps its files in folders of its own:
`gui/mods/sagtary_armor_hits/`, `gui/maps/sagtary_armor_hits/`, `gui/gameface/mods/sagtary_armor_hits/`. The
declaration file is `gui/gen_resources/sagtary_armor_hits.json`: a file with the name of a client one replaces it.

## Package `sagtary_armor_hits`

Now. The parts depend one way: the entry module wires them; `views/` uses `data/`; `data/` knows nothing of the UI.
The objects are made in the entry module and given to the parts that use them (a `BattleStore` to `HitsScreen`,
which gives it to the window with the keyword arguments of `App.loadView`), so there is no shared state in modules.

Core:

| Module             | Does                                                                         |
|--------------------|------------------------------------------------------------------------------|
| `config.py`        | ids, resource paths, texts, limits, the battle files folder `BATTLE_FILES_DIR` |
| `lang.py`          | texts in the client language                                                 |
| `settings.py`      | user settings from `mods/configs/sagtary_armor_hits/config.json`; `ModSettings` keeps them for the mod and writes the file when the settings menu changes one |
| `trace.py`         | log of the calls (prefix `calls:`, counts on screen open and close) and texts for the checks of a hit (prefix `check:`, `check: MISMATCH` warnings) |
| `optional_mods.py` | the optional third-party mods, or `None` when not installed: OpenWG Gameface (`gfModInject`), ModsList API (`modsListApi`) |

Data, without UI (`data/`):

| Module                    | Does                                                                         |
|---------------------------|------------------------------------------------------------------------------|
| `data/record.py`          | `Record`: a plain data object with fields and defaults (`FIELDS`) and nested records (`NESTED`), written to and read from a dict; the base of `Battle` and `Hit` |
| `data/hits.py`            | hits of a battle: `Hit` (shell kind, premium shell, caliber, damage, crits, the teams of the attacker and the target (a hit on an ally), the hit vehicle's pose as `VehiclePose` (turret yaw, gun pitch), all the points the shell hit as `HitPoint`s (part index, the shell's way, the effect and the hit type by their client names; the hit effects and the points on the chassis, hull, turret and gun to draw worked out from them), where a splash's shell burst in the hit vehicle's chassis space, the shell's exact direction at the first point from its tracer, the other vehicle's compact descriptor, the distance between the vehicles, what the shell did to the player's vehicle as `DamagedDevice`s by the client's names: damage info code, extra, device kind; its result: damage, else like the client's armor tooltip by the last point's effect: blocked, ricochet, no damage) |
| `data/hit_parser.py`      | the rules that make the hits from the server's calls, without reading the client: whose hit it is, a shell's hit from its decoded points, a splash, what the battle events and the damage info add (`HitPairing`: an event and a hit of the same vehicle within 1.5 s are one hit), the shell's direction from the tracer whose way passes the first point nearest (`Tracers`) |
| `data/hit_collector.py`   | `HitCollector`: adds the received and dealt hits to the battle in the `BattleStore` from `Vehicle.showDamageFromShot` and `showDamageFromExplosion`; the crits and a premium shell from the client's battle events, `PlayerAvatar.onBattleEvents`; the damaged modules from `PlayerAvatar.showVehicleDamageInfo`; the tracers from `PlayerAvatar.showTracer`; reads the client at each call (decoded points, arena, positions) for `hit_parser.py` |
| `data/hooks.py`           | `ClientHooks`: wraps each client method the server calls once, for all its listeners (the debug record, the hit collector); a listener gets each call (`Call`: entity, arguments by name) before the client's method; the method is put back after its last listener |
| `data/battle_modes.py`    | the client's battle types in groups by skill (random, competitive, training, fun, other: the types of no group) and how each group's battles are kept (`battleModes`: off, session, file) |
| `data/battles.py`         | battles of the session in memory: `Battle` (fields with defaults in `FIELDS`), `BattleStore` (newest first, up to `BATTLES_LIMIT`, `onChanged`), `BattleCollector` (adds the battle on `onAvatarReady`, battles and replays, and its winner on `onRoundFinished`) |
| `data/client_names.py`   | names of vehicles and maps by their ids from the client caches, in the client language; a battle keeps only the ids (`battleId`, `mapId`, `gameplayId`, `battleType`; `vehicleId` from the first bytes of `vehicleDescriptor`), so a battle from a file shows in the current client language |
| `data/battle_file.py`     | the battles written to JSON files and read back (`BattleFiles`), for the file buttons (reports): one file `hits_<battleId>.json` per battle, written over when saved again; loading reads all `hits_*.json` of the folder; a file has `formatVersion` (its layout) and `appVersion` (the mod that wrote it) |
| `data/debug_recorder.py`  | debug record of every server call about shots and damage, a JSON Lines file per battle in `mods/sagtary_armor_hits/debug/`; on only with the `debug` setting (`mods/configs/sagtary_armor_hits/config.json`, read when the client starts) |

UI (`views/`), a package per screen or button. The view models, the data the Gameface pages read, are apart in
`views/models/`, like the client's `gui/impl/gen/view_models`; they hold no logic, the views and presenters fill them.

| Module                                    | Does                                                         |
|-------------------------------------------|--------------------------------------------------------------|
| `views/hits/hits_screen.py`               | puts the hits screen into the client: the view setting, the lobby state and its transition; loads the view with the `BattleStore` |
| `views/hits/hits_state.py`                | lobby state of the screen: a page of the lobby navigation, the armor page scene and camera |
| `views/hits/hits_view.py`                 | window and Gameface view of the screen: the full screen page, the mouse over the scene, the panel presenters |
| `views/hits/battle_selector.py`           | presenter of the battle selector: fills its model from the `BattleStore`, keeps the selected battle (`onBattleSelected`) |
| `views/hits/hits_panel.py`                | presenter of the hits panel: the received or dealt hits of the selected battle, the result filters, the chosen hit (`onChanged`, `selection`) |
| `views/hits/hangar_vehicle.py`            | presenter of the hangar vehicle: the vehicle the panel shows the hits on, as the client's preview vehicle |
| `views/hits/hangar_scene.py`              | presenter of the hangar camera while the screen is open: its collisions off and its pitch limits widened, so it goes under the floor and looks from below; put back when the screen closes |
| `views/hits/settings_menu.py`             | presenter of the settings menu: the mod's settings (hits on allies, the lobby button's place, the debug record), how the battles of each group of modes are kept (off, session, file), and the file buttons, opened by the gear right of the battle selector; a click writes the settings file (`settings.ModSettings`) |
| `views/hits/hit_lines.py`                 | presenter of the hit lines: the chosen hit's way (`Way`: lead, pieces on, ricochet's way out, splash) in the 3D scene over the hangar vehicle, turned to the hit's pose (turret yaw, gun pitch) first |
| `views/hits/hit_way.py`                   | the look of a hit's way: a solid white line to the first point, white dashes after a ricochet or spaced armor, at the line's start a white dot and rings as a cone back towards the shooter |
| `views/hits/scene_lines.py`               | shapes in the 3D scene drawn every frame with the client's debug drawer (`DebugDrawer`), over the armor overlay: tubes, dashed tubes (with gaps), spheres, rings; shapes that follow the vehicle's parts are put again before every frame (`follow`) |
| `views/hits/scene_log.py`                 | log of the scene (prefix `scene:`): the client's hangar vehicle events with the vehicle's state |
| `views/hits/overlay_panel.py`             | presenter of the overlay panel: the armor page's three overlay types (client texts) and the client's armor overlay on the hangar vehicle |
| `views/hits/shot_panel.py`                | presenter of the shot panel: the chosen hit's shooter and target cards (vehicle; icons of the shooter's gun and shell, the target's turret and gun, with the client's module and shell tooltips), result, and sections (damage, penetration, armor and angle counted in the garage, distance, modules and crew: on a hit on the player's vehicle the battle damage panel's icons copied into `gui/maps/sagtary_armor_hits/modules/`, a tile per module kind and crew role that shot damaged, in rows of four, the crew under them, with the client's names of the damaged parts and crew members under the icon in their state's color) |
| `views/hits/armor_tooltip.py`             | presenter of the armor tooltip: the client's armor page tooltip (`ArmorTooltipWindow`) for the armor under the mouse, with the chosen hit's shell |
| `views/hits/scene_panel.py`               | presenter of the scene panel: lines of all shown hits (received side only) or of the chosen one, the shooter view (camera along the shell) |
| `views/hits/file_buttons.py`              | presenter of the file buttons: save the chosen battle to its file, load all the battle files into the `BattleStore`; the result is a system message with the path |
| `views/lobby_button/lobby_button.py`      | the hangar button that opens the screen; picks one of the two below |
| `views/lobby_button/mods_list_entry.py`   | entry in the ModsList API mods list (optional)               |
| `views/lobby_button/footer_button.py`     | button of its own in the hangar footer, next to the game menu button |
| `views/models/hits_view_model.py`         | view model of the hits screen                                |
| `views/models/battle_selector_model.py`   | view models of the battle selector and of a battle in its list |
| `views/models/footer_button_model.py`     | view model of the footer button                              |
| `views/models/hits_panel_model.py`        | view models of the hits panel, its hits, targets and filters |
| `views/models/file_buttons_model.py`      | view model of the file buttons (commands only)               |
| `views/models/overlay_panel_model.py`     | view models of the overlay panel and its types               |
| `views/models/shot_panel_model.py`        | view models of the shot panel: vehicle cards, modules, sections and their lines |
| `views/models/scene_panel_model.py`       | view model of the scene panel                                |

## Lobby button

ModsList API is optional; the footer button is the main one.

| Installed                                                 | Button                              |
|-----------------------------------------------------------|-------------------------------------|
| OpenWG Gameface                                           | button in the hangar footer         |
| OpenWG Gameface, ModsList API, `showButtonInModsMenu` on  | entry in the ModsList API mods list |
| OpenWG Gameface, ModsList API, `showButtonInModsMenu` off | button in the hangar footer         |
| neither                                                   | no button, a warning in `game.log`  |

ModsList API needs OpenWG Gameface itself, so there is no case with ModsList API alone. `showButtonInModsMenu` is in
the user settings file (see README).

The footer button uses the client's own API where there is one:

- Since client 2.4.1 the client reads `gui/gen_resources/*.json` of all packages into the `R` tree, so the layout
  is `R.mods.sagtary_armor_hits.views.FooterButton`.
- The view is a `ViewComponent`, added as a child view of the footer in `LobbyFooter._initChildren` (and of the
  footers of the modes: Comp7, Comp7 Light, Last Stand, Battle Royale).

The client has no API to put an element into the footer page: the footer script draws only its own children, by
name. So `FooterButton.js` is loaded into the footer page by OpenWG Gameface (`gf_mod_inject`: it replaces the
client's `gui/gameface/js/index.js`, which every Gameface page loads). The script puts the button before the menu
button and calls the view model's `onClick` command. ModsList API and Aslain's Mod Menu add their buttons the same
way.

## Hits screen

The screen is built like the client's vehicle armor page (Vehicle Hub, `VehicleHubWindow`):

- a Scaleform view setting (`ViewSettings`, alias `sagtaryArmorHitsView`, layer `SUB_VIEW`) whose class is a Gameface
  window (`WindowImpl`); it is added to `IGuiLoader.entitiesFactory` when the lobby app initializes;
- the window's content is a Gameface view (`ViewComponent`) with the layout `R.mods.sagtary_armor_hits.views.HitsView`;
  the page is transparent, so the 3D hangar shows through it;
- a lobby state (`SFViewLobbyState`, child of `SubScopeSubLayerState`) is added to the lobby state machine
  (`AppLifeCycleEvent.INITIALIZING`, `addStateConfigurator`); entering it fires a `LOAD_VIEW` event for the alias, and
  the mod loads the view (`app.loadView`), as the client's package business handlers do;
- the lobby draws its header and footer as opaque bars ("old style", CSS class `base__oldStyle` with a background
  pattern) around a sub view in a frame, and the window then gets only the space between them; the Flash lobby page
  (`LobbyPageSubContainer.onViewVisibilityChanged`) leaves a view out of the frame when its wrapper reports
  `isFullScreenModeSupported`, which a Gameface page sets with `viewEnv.setFullscreenModeSupported(true)`;
  `HitsView.js` does that, like the armor page, and puts `viewEnv.getExternalPaddingsRem()` (the space of the header
  and the footer, updated on `self.onPaddingsUpdated`) into the CSS variables `--external-padding-*`;
- the page draws the armor page's shading itself (`Page_base__armor` in `vehicle_hub/main/main.css`) over the whole
  screen, so the dark fade under the footer comes from the page, not from the footer;
- the state has no `LobbyStateFlags.HANGAR` flag: the lobby header picks its type by that flag, and without it shows the
  page header (hangar button, page title, wallet) instead of the full hangar header; the hangar button closes the
  screen;
- the 3D scene is set like on the armor page (the client's `VehicleHubState` and `ArmorState`): entering the state
  moves the hangar vehicle to the customization place (`HangarCustomizationEvent.CHANGE_VEHICLE_MODEL_TRANSFORM`, the
  place and angles of `customizationHangarCFG()`), and leaving it puts the vehicle back
  (`RESET_VEHICLE_MODEL_TRANSFORM`, `turretAndGunAngles.reset()`);
- the state is a `SubhangarStateGroupConfigProvider`: the client's `SubhangarObserver` activates the subhangar groups
  `VehicleHub` and `VehicleHubArmor{Small,Medium,Large}Tank` (by the vehicle size, `selectItemByTankSize`), which
  switches to the armor camera (`Armor_Inspector_Camera`); the camera moves there at once (`CameraMover`), as a smooth
  move would fly it from the hangar up to the customization place; the group is chosen for the vehicle in the hangar
  when the screen opens and stays when the vehicle changes;
- the hangar shows the vehicle the hits panel shows the hits on, as the preview vehicle like on the Vehicle Hub
  (`g_currentPreviewVehicle.selectVehicle`): the player's vehicle of the battle on the received side, the vehicle of
  the chosen hit on the dealt side (the copied vehicle for a maps training dummy), no vehicle when there is none
  to show: no battles, no hits on the dealt side (`HangarSpace.removeVehicle`). The vehicle has the modules it had in the battle (the compact
  descriptor kept in `Battle.vehicleDescriptor` and `Hit.vehicleDescriptor`), as the hit points are on them; a battle recorded
  without it shows the default modules. Closing the screen shows the current vehicle again (`selectNoVehicle`);
- the chosen hit is drawn in the 3D scene over that vehicle (`hit_lines.py`). The hit points are in the space of
  their parts (`DamageFromShotDecoder.parseHitPoint`: the part and the shell's way through it); a point is the middle
  of that way and the shell's direction is along it, like the Battle Hits mod does, put into the scene by the part's
  node (the node the client puts the hit effects on). Before that the hangar vehicle turns its turret and gun as the
  hit's vehicle had them (`Hit.vehiclePose`), like the client's armor screen turns them; without a chosen hit the
  vehicle goes back to the hangar's pose. The nodes take a new pose when a next frame is drawn, sometimes after the
  lines are first put, so the lines are put again before every frame by the nodes as they are then
  (`SceneLines.follow`) and follow the turret and the gun; when the chosen hit's first point moves so, the shot panel
  and the shooter view get it again. The vehicle's collision model is used only for the armor's normal at a last
  ricochet (once, kept in the part's space): it comes a few frames after the vehicle and answers with wrong points
  before that.
  When: at once if the hangar already shows the hit's vehicle, loaded; else on `HangarSpace.onVehicleChanged` after
  the hangar vehicle presenter asked for it (the parts are in their places then); the lines go on
  `onVehicleChangeStarted` and on another hit. All in white (`hit_way.py`): a solid line to the first point, dashes
  with gaps after a ricochet or spaced armor, at the line's start a dot and rings as a cone back towards the shooter;
  the other hits' ways ("All" lines) thinner, without the dot and the rings; a line is a cylinder 18 mm thick (12 mm for the others)
  drawn with the client's debug drawer (`DebugDrawer.DebugDrawer().cylinder()`, tested against the scene's depth, so the vehicle
  hides what is behind it), again on every frame. The debug drawer draws after the client's armor overlay, which
  covers every scene model whatever its shader (`glow.fx`, `glow_noalpha.fx`, opaque `lightonly.fx` were tried). The way:
  2.5 m before the first point; on to the next point after a ricochet or spaced armor; 1.5 m out of a last ricochet
  in the mirrored direction; none after a penetration; only the first point for a high explosive shell (its other
  points are what the burst hit). A splash has no points: the hit keeps where the shell burst
  (`showDamageFromExplosion`'s center, in the hit vehicle's chassis space), drawn as a sphere of three rings around
  the chassis' axes with a dot on the burst, and a dashed line down (or up) to the tracks' level (the chassis space's
  ground): the shell may burst above or below the tracks (a slope, a hole, a rock, a wall), while the
  hangar's floor is flat. The explosion radius (about 10 m for a big gun) is
  not drawn: it covers the hangar. Tried before: a Gameface overlay projected every frame (thin and colored, but flat,
  over the vehicle), the client's cube `objects/misc/bbox/unit_cube_1m_proxy.model` (lit, of one bluish color) and
  the mod's own tube models with the glow shader (under the armor overlay);
- the page passes the mouse over the scene to the hangar camera like the client's `SceneWrapper`: a layer under the
  panels sends drags (`dx`, `dy` in pixels) and wheel steps (`dz` of 600) to `onMoveSpace`, which fires
  `CameraRelatedEvents.LOBBY_VIEW_MOUSE_MOVE`, and `onMouseOver3dScene` fires `NOTIFY_CURSOR_OVER_3DSCENE`; the
  panels' container lets the mouse through (`pointer-events: none`), the panels do not.

The battle selector shows the selected battle (map preview `gui/maps/icons/map/small/<map>.png`, map, result,
vehicle, time) and opens the list of the session's battles grouped by date. Every text of it is the client's: names by
the ids, the result from the client's `#event_boards:summary/result/*` texts, the date and the time in the client format; it is styled like the client's dropdowns (the armor page's overlay type: the client's arrow and list item
background). The battles are kept in memory only, so the list starts empty with every game start; without battles the card says so. To add a field:
a field in `Battle.FIELDS` and in `battleFromAvatar`, a property in `BattleItemModel`, a line in `_fillItem`, and its
place on the page.

The hits panel under the selector shows the hits of the selected battle: on the player's vehicle or by the player,
the result filters with their counts, the chosen hit and the list (number and time, then the order of the client's damage log:
damage (none when the hit took none),
result, the critical icon for a hit with crits (no count), shell kind (white plate, gold for a premium shell), vehicle class, vehicle; the player last). Its result icons are the mod's copies in
`gui/maps/sagtary_armor_hits/hits/`: the client's damage log icons (damage, critical, blocked) cut out of its battle
atlas, and the mod's own ricochet (a dashed way off a plate, on a pink square) and no damage (the blocked shield in
cyan, a dash inside), drawn in their style in the colors of the armor tooltip's results' texts. Its vehicle class icons are the client's damage log icons, taken from the
client's battle atlas (`gui/flash/atlases/commonBattleLobby.dds`, positions from its `.xml`) as CSS sprites; the
shell kinds are the client's damage log texts (`#ingame_gui:damageLog/shellType/*`).

The file buttons are in the settings menu under the settings, in every build: a floppy disk writes the chosen
battle to `mods/sagtary_armor_hits/hits/hits_<battleId>.json` (`BATTLE_FILES_DIR`; off without a battle), over the
file of the same battle saved before; an arrow up reads the battles of all the `hits_*.json` files of that folder.
A player sends the battle's file with a report, the developer puts it into the folder and looks at the battle without
playing it; the system message tells the full path. A `.env` file is not used: Python 2.7 of the client has no reader of it
(python-dotenv is a third-party package), and the mod runs in the game folder, not in this repository.

The armor overlay of the client's armor screen is a CGF component (`ArmorInspectorComponent`) put on the hangar
vehicle, so the hits screen can show it without the Vehicle Hub. The overlay panel presenter puts it on the vehicle's
game object on `HangarSpace.onVehicleChanged` and takes it off on `onVehicleChangeStarted`, on "no overlay" and when
the screen closes. For the penetration chance it sets the chosen hit's shell as the armor page sets its attacker's
(`setShellParamsFromVehicle`): the shot of the shooter's gun with the hit's shell kind, premium or not (the shooter is
the other vehicle of a received hit, the player's vehicle of a dealt one, with its modules from the compact
descriptor).

The armor tooltip is the client's `ArmorTooltipWindow`, made, filled and loaded as the armor page does. Its page
tells the client its size only from its first drawing (a `ResizeObserver` set up once) and draws nothing without armor
layers, so the window must be filled with armor before `load()`: a window loaded empty, or filled when it has loaded,
is laid out only after the client's 3 s "Size calculation timeout". The presenter makes a window only where the mouse
ray meets armor (a collision with a material), fills it, then loads it.

## Logging

All modules log to the `sagtary.armor_hits` logger. The lines go to `game.log` in the game folder, for example
`[INFO] [Main] [SCRIPT] [sagtary.armor_hits] init v0.1.0`.

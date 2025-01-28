# Euroland Blender add-on

Export intermediate Eurocom formats for *Sphinx and the Cursed Mummy* in Blender. This project aims to reimplement the missing *3ds Max* (EIF, ESE) and *Maya* (RTG) plug-ins and make creating Euroland assets possible. Heavily work in progress.

> ➥ *You can [download the latest version from the Releases tab](https://github.com/Swyter/sphinx-euroland/releases/tag/latest)*.

# Formats

The formats we aim to support are documented here:
*https://sphinxandthecursedmummy.fandom.com/wiki/Technical*

Here's a rough table with the kind of data they can work with, you usually need different formats for different elements:

| Format   | Entities       | Maps         | Animations + Skins | Scripts     |
| :------- | :------------- | :----------- | ------------------ | ----------- |
| [EIF]    | ✓              | ✓            |                    |             |
| [RTG]    | ✓              | ✓            | ✓                  | ✓           |
| [ESE]    | ✓              | ✓            | ✓                  | ✓           |

[EIF]: https://sphinxandthecursedmummy.fandom.com/wiki/EIF
[RTG]: https://sphinxandthecursedmummy.fandom.com/wiki/RTG
[ESE]: https://sphinxandthecursedmummy.fandom.com/wiki/ESE

For more info about which things each format supports, you can look at the [wiki].

[wiki]: https://sphinxandthecursedmummy.fandom.com/wiki/EuroLand#Intermediate_formats

## Current status / supported export features
* EIF (_Eurocom Interchange Format_)
  - [x] Arbitrary polygons
  - [x] Vertex colors
  - [ ] Layers
  - [X] Maps

* ESE (_Eurocom Export Scene_)
  - [x] Arbitrary polygons
  - [x] Edge visibility: recombining the right triangles back into n-gons.
  - [x] Vertex colors
  - [x] Shape keys, or morph targets
  - [x] Mesh skeletal rigging
  - [x] Lights and animated lights
  - [x] Cameras and animated cameras
  - [ ] Layers
  - [X] Maps
  - [ ] Animations + Skins
  - [X] Scripts

* RTG (_Real Time Game_)
  - [ ] Arbitrary polygons: Visible vertex edges is not implemented yet
  - [ ] Vertex colors
  - [ ] LODs
  - [ ] Layers
  - [ ] Hard edges
  - [ ] Maps
  - [ ] Animations + Skins
  - [ ] Scripts
  - [x] Cameras and camera animations, but rotations need fixing


# To develop

For ease of development it's a good idea to install the add-on in some place where Blender can find it, otherwise you would have to change the Blender startup script to add your folder to the Python search path, a good place to put it is the local scripts folder.

You can do this by cloning the Git repository and making a symbolic link from one folder to another. On Windows, open `cmd`, navigate to your local Git repository folder (with `cd <path>`) and type something like this, note the `2.93` version and adjust accordingly:
```
mklink /j '%appdata%\Blender Foundation\Blender\2.93\scripts\addons\io_scene_sphnx' '.\io_scene_sphnx'
```

Once you refresh the Blender Add-ons window it should show up; click under «Edit > Preferences...» to open the dialog with the «Add-ons» tab, click the «Refresh» button and you should be able to find our entry in the list and toggle it on.

## Live-reloading
After editing the `.py` files you can live-reload the code (without restarting Blender) via shortcut; press *F3* to open the search menu and look for the «*Reload scripts*» operator. Right-click over the *«Blender > System > Reload Scripts»* entry that comes up and select «*Add to Quick Favorites*».

From now on you can easily refresh it with the latest changes from the text editor by pressing the *Q* key and then right-clicking or immediately pressing *Enter*, as long as it stays as the first *Quick Favorites* menu option.

A normal cycle should be; save, switch to the Blender window and quickly press *Q* and *Enter*. Try your changes and see the results.

## Useful tools
Other useful tools during development are the _Python Console_ (_Shift + F4_) to view the internal data structures, and the _System Console_ (_Window > Toggle System Console_) to view possible Python error output and dumping debug `print("LOL")` calls.

Keep in mind that there is [a great extension for the free *Visual Studio Code* IDE](https://github.com/JacquesLucke/blender_vscode) to debug and auto-live-reload on save, making Blender add-on development much more straightforward. I found about this after the fact.

That should be enough.

# Transforming coordinates

     Euroland       Blender
        Y+            Z+
        |             |
        |__ __ _ +Z   |__ __ _ +Y
       /             /
     +X            +X

     Blender: right is +X, forward into the screen is +Y, up is +Z.
    Euroland: right is +X, forward into the screen is +Z, up is +Y.
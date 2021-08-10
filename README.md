# Euroland Blender add-on

Import and export intermediate Eurocom formats for *Sphinx and the Cursed Mummy* in Blender.
Heavily work in progress.

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
  - [X] Maps: Issues with rotations

* ESE (_Eurocom Export Scene_)
  - [x] Arbitrary polygons: Visible vertex edges is not implemented yet
  - [x] Vertex colors
  - [ ] Layers
  - [ ] Maps
  - [ ] Animations + Skins
  - [ ] Scripts

* RTG (_Real Time Game_)
  - [ ] Arbitrary polygons: Visible vertex edges is not implemented yet
  - [ ] Vertex colors
  - [ ] LODs
  - [ ] Layers
  - [ ] Hard edges
  - [ ] Maps
  - [ ] Animations + Skins
  - [ ] Scripts: Only Animated cameras, but rotations need fixing


# To develop

For ease of development it's a good idea to install the add-on in some place where Blender can find it, otherwise you would have to change the Blender startup script to add your folder to the Python search path, a good place to put it in the local scripts folder:
```
%appdata%\Blender Foundation\Blender\<version>\scripts\addons\
```

You can do this by cloning the Git repository and making a symbolic link. On Windows, open `cmd`, navigate to your Git repository (with `cd <path>`) and type something like this:
```
mklink /j '%appdata%\Blender Foundation\Blender\<version>\scripts\addons\io_scene_sphnx' '.\io_scene_sphnx'
```

Once you refresh the Blender Add-ons window it should show up; click under «Edit > Preferences...» to open the dialog with the «Add-ons» tab, click the «Refresh» button and you should be able to find our entry in the list and toggle it on.

After editing the `.py` files you can live-reload the code (without restarting Blender) via shortcut; press *F3* to open the search menu and look for the «*Reload scripts*» operator. Right-click over the *«Blender > System > Reload Scripts»* entry that comes up and select «*Add to Quick Favorites*», now you can easily refresh it with the latest changes from the text editor by pressing the *Q* key and then right-clicking or immediately pressing *Enter*, as long as it stays as the first *Quick Favorites* menu option.

Other useful tools during development are the _Python Console_ (_Shift + F4_) to view the internal data structures, and the _System Console_ (_Window > Toggle System Console_) to view possible Python errors and dumping debug `print("LOL")` calls. That should be enough.

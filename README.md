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

For ease of development it's a good idea to install the plugin in some place where Blender can find it, otherwise you would have to change the Blender startup script to add your folder to the Python search path, a good place to put it is:
```
C:\Users\<user-name>\AppData\Roaming\Blender Foundation\Blender\2.90\scripts\addons\
```

You can do this by cloning the Git repository and making a symbolic link. On Windows, open `cmd`, navigate to your user's Blender Add-ons folder and type something like this:
```
mklink /j '.\io_scene_sphnx' 'C:\Users\<user-name>\Documents\github\sphinx-euroland\io_scene_sphnx'
```

Once you refresh the Blender Add-ons window it should show up and you should be able to enable it. But there are many ways of doing this.
You can also use the F3 search menu to look for the «*Eurocom reload*» operator, and assign it to a hotkey, like F8, to easily refresh it with the latest changes from the text editor.

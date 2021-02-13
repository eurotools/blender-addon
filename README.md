# sphinx-euroland

Import and export intermediate Eurocom formats for *Sphinx and the Cursed Mummy* in Blender.
Heavily work in progress.

> ➥ *You can [download the latest version from the Releases tab](https://github.com/Swyter/sphinx-euroland/releases/tag/latest)*.

# Formats

> *The formats we aim to support are documented here:*  
> *https://sphinxandthecursedmummy.fandom.com/wiki/Technical*


| Format   | Entities       | Maps         | Animations + Skins | Scripts     |
| :------- | :------------- | :----------- | ------------------ | ----------- |
| [EIF]    | ✓              | ✓            |                    |             |
| [RTG]    | ✓              | ✓            | ✓                  | ✓           |
| [ESE]    | ✓              | ✓            | ✓                  | ✓           |

[EIF]: https://sphinxandthecursedmummy.fandom.com/wiki/EIF
[RTG]: https://sphinxandthecursedmummy.fandom.com/wiki/RTG
[ESE]: https://sphinxandthecursedmummy.fandom.com/wiki/ESE

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

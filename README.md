# sphinx-euroland

Import and export intermediate Eurocom formats for *Sphinx and the Cursed Mummy* in Blender.
Work in progress.


# To develop

For ease of development it's a good idea to install the plugin somewhere Blender can find it, a good place is:
C:\Users\<user-name>\AppData\Roaming\Blender Foundation\Blender\2.90\scripts\addons\io_scene_sphnx

You can do this by cloning the Git repository and making a symbolic link. On Windows, open `cmd`, navigate to your `io_scene_sphnx` and type something like this:
```
mklink /j '.\io_scene_sphnx' 'C:\Users\<user-name>\Documents\github\sphinx-euroland\io_scene_sphnx'
```

Once you refresh the Blender Addons window it should show up. There are many ways of doing this.

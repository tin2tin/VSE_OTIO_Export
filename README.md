# VSE_OTIO_Export
Export from the Blender Video Sequence Editor(VSE) using [OpenTimelineIO](https://github.com/PixarAnimationStudios/OpenTimelineIO) to many formats, including aaf, fcpxml, cms 3600 edl, kdenlive, otio etc. 

## Installation:
OTIO module needs to be installed.
Mac and Linux users can use this add-on to install OpentimelineIO by simply typing `opentimelineio` in to it:
https://blenderartists.org/t/pip-for-blender/1259938

For Windows it's a bit more complicated, but @Celeborn2BeAlive found a way:
https://github.com/PixarAnimationStudios/OpenTimelineIO/issues/667#issuecomment-732507206

(I'm mirrored @Celeborn2BeAlive's OTIO wheel for Windows [here](https://github.com/tin2tin/VSE_OTIO_Export/raw/main/OpenTimelineIO-0.13.0-cp37-cp37m-win_amd64.whl). Install after download like this: 
`"...blendersomething\\2.92\\python\\bin\\python.EXE" -m pip install "C:\\Users\\XXXX\\Downloads\\OpenTimelineIO-0.13.0-cp37-cp37m-win_amd64.whl" --user` )

After that install the VSE_OTIO_Export add-on in Blender and find the option in the Export menu.

## Warning
This is work-in-progress and will cause a lot of errors.
I'n not a coder, so please help out.

### Things working:
Export of video, gaps and audio in .otio, .kdenlive, edl(one track).

### Things not working:
- Fcpxml, aaf.
- Exporting everything execpt video, gaps and audio.



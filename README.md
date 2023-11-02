# Export OTIO
Export .otio from the Blender Video Sequence Editor(VSE) using [OpenTimelineIO](https://github.com/PixarAnimationStudios/OpenTimelineIO) which is useful because ex. Davinci Resolve supports import of .otio files. 

![image](https://github.com/tin2tin/VSE_OTIO_Export/assets/1322593/e2015319-9047-46ff-930c-8731fb6873bb)


## Usage:
On Windows Blender must be "Run as Administrator" for the Python dependencies to be installed.

## Supported Export Elements
- Video
- Audio

## Not Working (uncommented code)
- OTIO does have various adaptors for various formats, but they're currently not working.
- Transitions

## Useful Add-on:
For cleaning up and organizing the timeline: https://github.com/tin2tin/Arrange_Sequence

Conform. Render any strip(ex. Scene strips) to a trimmed movie strip: https://github.com/tin2tin/Add_Rendered_Strips

## Location
View Menu > Export Timeline (.otio)

![image](https://github.com/tin2tin/VSE_OTIO_Export/assets/1322593/f3e7d55d-c0b3-4dfe-b446-5a65ebb1517a)




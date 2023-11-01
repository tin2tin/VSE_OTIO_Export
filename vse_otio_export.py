bl_info = {
    "name": "Export OTIO",
    "author": "tintwotin",
    "version": (1, 1),
    "blender": (3, 4, 0),
    "location": "View > Export > Video Sequence Editor",
    "description": "Export to various OTIO supported formats",
    "warning": "",
    "doc_url": "",
    "category": "Sequencer",
}

import bpy
import os
import sys
import site
import subprocess

from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator

app_path = site.USER_SITE
if app_path not in sys.path:
    sys.path.append(app_path)

pybin = sys.executable  # bpy.app.binary_path_python # Use for 2.83

try:
    subprocess.call([pybin, "-m", "ensurepip"])
except ImportError:
    pass
try:
    import opentimelineio as otio
except ImportError:
    subprocess.check_call([pybin, "-m", "pip", "install", "OpenTimelineIO==0.17.0.dev1"])
    import opentimelineio as otio        

TRACK_TYPES = {
    "video": otio.schema.TrackKind.Video,
    "audio": otio.schema.TrackKind.Audio,
}

# Adapters are currently not working
#required_packages = ["otio-fcpx-xml-adapter", "otio-cmx3600-adapter", "otio-xges-adapter", "otio-aaf-adapter", "otio-mlt-adapter", "otio-hls-playlist-adapter"]

#for package in required_packages:
#    package_imp = package.replace("-", "_")
#    try:
#        exec("import " + package_imp)
#    except ModuleNotFoundError:
#        print(f"Installing: {package}")
#        subprocess.check_call([pybin, "-m", "pip", "install", package])
#        package = package.replace("-", "_")
#        exec("import " + package_imp)


def _create_rational_time(frame, fps):
    return otio.opentime.RationalTime(float(frame), float(fps))


def _create_time_range(start, duration, fps):
    return otio.opentime.TimeRange(
        start_time=_create_rational_time(start, fps),
        duration=_create_rational_time(duration, fps),
    )


def _create_reference(mp_item, filepath):
    render = bpy.context.scene.render
    vse_fps = round((render.fps / render.fps_base), 3)
    if int(vse_fps) == (vse_fps):
        vse_fps = int(vse_fps)
    return otio.schema.ExternalReference(
        target_url=filepath,
        available_range=_create_time_range(0, mp_item.frame_duration, vse_fps),
    )


def _create_clip(tl_item, frame_rate):
    # Frame_rate should be clip fps, but Blender doesn't have clip properties exposed in the API.
    if tl_item.type == "SOUND":
        filename = os.path.realpath(bpy.path.abspath(tl_item.sound.filepath))
    else:
        filename = os.path.realpath(bpy.path.abspath(tl_item.filepath))
    clip = otio.schema.Clip(
        name=bpy.path.basename(filename),
        source_range=_create_time_range(
            tl_item.frame_offset_start, tl_item.frame_final_duration, frame_rate
        ),
        media_reference=_create_reference(tl_item, filename),
    )
    return clip


def _create_gap(gap_start, clip_start, tl_start_frame, frame_rate):
    return otio.schema.Gap(
        source_range=_create_time_range(
            gap_start, int(clip_start - tl_start_frame), frame_rate)
    )
    
#def _create_transition(duration, frame_rate):
#    half_time = int(duration/2)
#    in_time = otio.opentime.RationalTime(half_time, frame_rate)
#    out_time = otio.opentime.RationalTime(half_time, frame_rate)
#    return otio.schema.Transition(
#        name="Dissolve",
#        transition_type=otio.schema.TransitionTypes.SMPTE_Dissolve,
#        in_offset=in_time,
#        out_offset=out_time
#    )
#    # opentimelineio._otio.Transition(name: str = '', transition_type: str = '', in_offset: opentimelineio._opentime.RationalTime = otio.opentime.RationalTime(value=0, rate=1), out_offset: opentimelineio._opentime.RationalTime = otio.opentime.RationalTime(value=0, rate=1), metadata: object = None)

def get_tracks(sequences):
    maximum_channel = 0
    # determine number of channels
    for sequence in sequences:
        if sequence.channel > maximum_channel:
            maximum_channel = sequence.channel
    tracks = [list() for x in range(maximum_channel + 1)]

    # sort files into channels
    index = 0
    for sequence in sequences:
        index = index + 1
        tracks[sequence.channel - 1].append([index, sequence])
    # simplify and sort channels
    sorted_tracks = []
    for track in tracks:
        if len(track) > 0:
            sorted_track = sorted(track, key=lambda x: x[1].frame_final_start)
            sorted_tracks.append(sorted_track)
    return sorted_tracks


def _create_ot_timeline(self, output_path, output_type):
    
    # Check if the output_path is not empty
    if not output_path:
        return

    # Get the Blender context and scene
    context = bpy.context
    scene = context.scene

    # Access the Video Sequence Editor
    vse = scene.sequence_editor

    # Get the render settings
    render = bpy.context.scene.render

    # Calculate the frame rate in VSE
    vse_fps = round((render.fps / render.fps_base), 3)

    # Convert the frame rate to an integer if it's a whole number
    if int(vse_fps) == (vse_fps):
        vse_fps = int(vse_fps)

    # Get the sequences in the VSE
    seq_strips = bpy.context.scene.sequence_editor.sequences

    # Organize sequences into tracks
    tracks = get_tracks(seq_strips)

    # Create an OTIO Timeline with the scene name
    ot_timeline = otio.schema.Timeline(name=bpy.context.scene.name)

    # Determine the output filename and extension
    filename, file_extension = os.path.splitext(output_path)
    
    if file_extension == "" and output_type != "other":
        filename = filename + "." + output_type
    else:
        filename = output_path

    for track_type in list(TRACK_TYPES.keys()):  # Iterate over video and audio tracks

        index = 0
        track_index = -1

        for track in tracks:
            ot_track = otio.schema.Track(
                name="{}{}".format(track_type[0].upper(), track_index),
                kind=TRACK_TYPES[track_type],
            )

            tl_items = []

            for sequence_data in track:
                source, tl_item = sequence_data

                # Check if the sequence is of the appropriate type (video or audio)
                if (tl_item.type == "MOVIE" and track_type.upper() == "VIDEO") or (
                    tl_item.type == "SOUND" and track_type.upper() == "AUDIO"): # or (
                    #tl_item.type == "CROSS" and track_type.upper() == "VIDEO"):

                    index = index + 1
                    clip_start = int(tl_item.frame_final_start)

                    # Handle gaps if there are any before the clip
                    if clip_start > ot_track.available_range().duration.value:
#                       if tl_item.type == "CROSS": 
#                            ot_track.append(
#                                _create_transition(
#                                    tl_item.frame_final_duration,
#                                    vse_fps,
#                                )
#                            )
#                       else:
                        ot_track.append(
                            _create_gap(
                                ot_track.available_range().duration.value,
                                clip_start,
                                ot_track.available_range().duration.value,
                                vse_fps,
                            )
                        )

                    # Add the clip to the OTIO track
                    #if not tl_item.type == "CROSS":
                    ot_track.append(_create_clip(tl_item, vse_fps))

            # Add the OTIO track to the timeline
            ot_timeline.tracks.append(ot_track)

    # Export the OTIO timeline to a file with the given filename
    # print(otio.adapters.otio_json.write_to_string(ot_timeline, indent=4))
    self.report({"INFO"}, "Exported: " + filename)
    print("Exported: " + filename)
    otio.adapters.write_to_file(ot_timeline, filename)


    return {"FINISHED"}


class EXPORT_OT_video_sequence_editor(Operator, ExportHelper):
    """Export OpenTimelineIO"""

    bl_idname = "sequencer.otio"
    bl_label = "Export Sequence"

    filename_ext = ""

    filter_glob: StringProperty(
        default="*.otio",
        options={"HIDDEN"},
        maxlen=255,
    )

    type: EnumProperty(
    name="",
    description="Choose extention",
    items=(
        ('OTIO', "OpentimelineIO (.otio)", "OpentimelineIO"),
        #('MLT', "MLT XML (.mlt)", "MLT XML"),  # Adapters are currently not working
        #('XGES', "xges (.xges)", "xges"),
        #('HLS', "hls (.hls)", "hls"),
        #('EDL', "CMX 3600 (.edl)", "CMX 3600 EDL"),
        #('FCPXML', "Final Cut Pro (.fcpxml)", "Final Cut Pro"),
        #('AAF', "Advanced Authoring Format (.aaf)", "Advanced Authoring Format"),
        #('KDENLIVE', "Kdenlive (.kdenlive)", "Kdenlive"),
        ('OTHER', "Other Extension", "No extension will be added"),
    ),
    default='OTIO',
    )

    def execute(self, context):        
        return _create_ot_timeline(self, self.filepath, (self.type).lower())


def menu_func_export(self, context):
    #self.layout.operator(EXPORT_OT_video_sequence_editor.bl_idname, text="Video Editing(.otio, .edl, .fcpxml, .aaf)")
    layout = self.layout
    layout.separator()
    layout.operator(EXPORT_OT_video_sequence_editor.bl_idname, text="Export Timeline (.otio)")


def register():
    bpy.utils.register_class(EXPORT_OT_video_sequence_editor)
    bpy.types.SEQUENCER_MT_view.append(menu_func_export)


def unregister():
    bpy.utils.unregister_class(EXPORT_OT_video_sequence_editor)
    bpy.types.SEQUENCER_MT_view.remove(menu_func_export)


if __name__ == "__main__":
    register()
    
    

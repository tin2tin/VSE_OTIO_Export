bl_info = {
    "name": "Export OTIO",
    "author": "tintwotin",
    "version": (1, 0),
    "blender": (2, 80, 0),
    "location": "File > Export > Video Sequence Editor",
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
    subprocess.check_call([pybin, "-m", "pip", "install", "opentimelineio"])
    import opentimelineio as otio


TRACK_TYPES = {
    "video": otio.schema.TrackKind.Video,
    "audio": otio.schema.TrackKind.Audio,
}


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
            gap_start, int(clip_start - tl_start_frame), frame_rate
        )
    )


# get_tracks by Snu
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


def _create_ot_timeline(output_path, output_type):
    if not output_path:
        return
    context = bpy.context
    scene = context.scene
    vse = scene.sequence_editor
    render = bpy.context.scene.render
    vse_fps = round((render.fps / render.fps_base), 3)
    if int(vse_fps) == (vse_fps):
        vse_fps = int(vse_fps)
    seq_strips = bpy.context.scene.sequence_editor.sequences
    tracks = get_tracks(seq_strips)
    ot_timeline = otio.schema.Timeline(name=bpy.context.scene.name)

    filename, file_extension = os.path.splitext(output_path)
    if file_extension == "" and output_type != "other":
        filename = filename + "." + output_type
    else:
        filename = output_path

    for track_type in list(TRACK_TYPES.keys()):  # video and audio

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
                if (tl_item.type == "MOVIE" and track_type.upper() == "VIDEO") or (
                    tl_item.type == "SOUND" and track_type.upper() == "AUDIO"
                ):
                    index = index + 1
                    clip_start = int(tl_item.frame_final_start)

                    if clip_start > ot_track.available_range().duration.value:
                        ot_track.append(
                            _create_gap(
                                ot_track.available_range().duration.value,
                                clip_start,
                                ot_track.available_range().duration.value,
                                vse_fps,
                            )
                        )
                    ot_track.append(_create_clip(tl_item, vse_fps))
            ot_timeline.tracks.append(ot_track)

    #print(otio.adapters.otio_json.write_to_string(ot_timeline, indent=4))
    print("Exported: "+filename)
    otio.adapters.write_to_file(ot_timeline, filename)

    return {"FINISHED"}


class EXPORT_OT_video_sequence_editor(Operator, ExportHelper):
    """This appears in the tooltip of the operator and in the generated docs"""

    bl_idname = "export.vse"
    bl_label = "Export VSE"

    filename_ext = ""

    filter_glob: StringProperty(
        default="*.otio",
        options={"HIDDEN"},
        maxlen=255,
    )

    type: EnumProperty(
    name="Format",
    description="Choose inserted extention",
    items=(
        ('OTIO', "OpentimelineIO (.otio)", "OpentimelineIO"),
        ('EDL', "CMX 3600 (.edl)", "CMX 3600 EDL"),
        ('FCPXML', "Final Cut Pro (.fcpxml)", "Final Cut Pro"),
        ('AAF', "Advanced Authoring Format (.aaf)", "Advanced Authoring Format"),
        ('KDENLIVE', "Kdenlive (.kdenlive)", "Kdenlive"),
        ('OTHER', "Other Extention", "No extention will be added"),
    ),
    default='OTIO',
    )

    def execute(self, context):
        return _create_ot_timeline(self.filepath, (self.type).lower())


def menu_func_export(self, context):
    self.layout.operator(EXPORT_OT_video_sequence_editor.bl_idname, text="Video Editing(.otio, .edl, .fcpxml, .aaf)")


def register():
    bpy.utils.register_class(EXPORT_OT_video_sequence_editor)
    #bpy.types.SEQUENCER_HT_header.append(menu_func_export)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    bpy.utils.unregister_class(EXPORT_OT_video_sequence_editor)
    #bpy.types.SEQUENCER_HT_header.remove(menu_func_export)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)


if __name__ == "__main__":
    register()

    # test call
    #bpy.ops.export.vse("INVOKE_DEFAULT")

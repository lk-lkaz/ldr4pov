"""
This program is free software.
Feel free to fix, modify, or remake it.
https://github.com/lk-lkaz/ldr4pov
"""

import bpy
import math
import mathutils
from bpy.props import (
                        FloatProperty,
                        IntProperty,
                        EnumProperty,
                        )

bl_info = {
    "name": "ldr4pov_Tools_AssemblyAnimation",
    "description": "Make a assembly animation by Rigid Body simulation",
    "author": "lk.lkaz",
    "version": (0, 0, 1),
    "blender": (2, 67, 0),
    "location": "View3D > Tools",
    #"warning": "",
    #"wiki_url": "http://",
    #"tracker_url": "http://",
    "category": "3D View"}


class panel_layout(bpy.types.Panel):
    bl_label = "Assembly Animation Tool"
    #bl_idname = ""
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"
    #bl_context = ""

    def draw(self, context):
        scn = bpy.context.scene
        layout = self.layout

        layout.label(text="Step0:")
        col = layout.column()
        col.operator("object.initial_setup", text="Set indicators")

        layout.label(text="Step1:")
        col = layout.column(align=True)
        col.operator("object.set_passive", text="Add PASSIVE")

        layout.label(text="Step2:")
        col = layout.column(align=True)
        col.prop(scn, "ldr4pov_gravity_strength", text="Gravity Strength")
        #col.prop(scn, "ldr4pov_sort_vector")
        col.prop(scn, "ldr4pov_interval", text="Interval")
        col.prop(scn, "ldr4pov_bake_quality", text="Accuracy")
        if scn.ldr4pov_bake_quality == "0":  # Custom
            col.prop(scn.rigidbody_world, "steps_per_second", text="steps_per_second")
            col.prop(scn, "ldr4pov_simulation_frames", text="Frames")
            col.prop(scn, "ldr4pov_bake_step", text="Frame Step")
        """
        #lk? Doesn't work. "AttributeError: Writing to ID classes in this context is not allowed:..."
        #lk? Moved to fall_simulation()
        elif scn.ldr4pov_bake_quality == "1":    # Default
            scn.rigidbody_world.steps_per_second = 60
            scn.ldr4pov_simulation_frames = 48 # 2sec in 24fps
            scn.ldr4pov_bake_step = 2
        elif scn.ldr4pov_bake_quality == "2":  # Low
            scn.rigidbody_world.steps_per_second = 30
            scn.ldr4pov_simulation_frames = 24 # 1sec in 24fps
            scn.ldr4pov_bake_step = 3
        """

        layout.label(text="Step3:")
        row = layout.row(align=True)
        row.scale_y = 3.0
        row.operator("object.fall_simulation", text="Start")

        """
        layout.label(text="Step4:")
        col = layout.column(align=True)
        col.operator("object.reverse_frames", text="Reverse Frames")
        """



class initial_setup(bpy.types.Operator):
    bl_idname = "object.initial_setup"
    bl_label = "initial_setup"
    bl_description = "..."
    bl_option = ("REGISTER", "UNDO")

    def execute(self, context):
        # Make indicators of gravity and sort vector.
        if "ldr4pov_gravity_indicator" not in bpy.data.objects:
            # Avoid conflict #lk?
            if "Cone" in bpy.data.objects:
                bpy.data.objects["Cone"].name = "ldr4pov_cone"

            # Cone as ldr4pov_gravity_indicator
            bpy.ops.mesh.primitive_cone_add(vertices=6, radius1=1, radius2=0, depth=2, enter_editmode=True, location=(0,0,0))
            bpy.ops.transform.translate(value=(0,0,10)) # Edit mode
            bpy.ops.object.editmode_toggle()
            o = bpy.data.objects["Cone"]
            o.name = "ldr4pov_gravity_indicator"
            o.lock_location = (True,True,True)
            #lk? material?

            # Avoid conflict #lk?
            if "ldr4pov_cone" in bpy.data.objects:
                bpy.data.objects["ldr4pov_cone"].name = "Cone"

        else:
            # Reset location and rotation
            o = bpy.data.objects["ldr4pov_gravity_indicator"]
            o.location = (0,0,0)
            o.rotation_euler = (0,0,0)


        if "ldr4pov_sort_indicator" not in bpy.data.objects:
            # Avoid conflict #lk?
            if "Icosphere" in bpy.data.objects:
                bpy.data.objects["Icosphere"].name = "ldr4pov_icosphere"

            # Ico_Sphere as ldr4pov_sort_indicator
            bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, size=1, enter_editmode=True, location=(0,0,0))
            bpy.ops.transform.translate(value=(0,0,8)) # Edit mode
            bpy.ops.object.editmode_toggle()
            o = bpy.data.objects["Icosphere"]
            o.name = "ldr4pov_sort_indicator"
            o.lock_location=(True,True,True)
            #lk? material?

            # Avoid conflict #lk?
            if "ldr4pov_icosphere" in bpy.data.objects:
                bpy.data.objects["ldr4pov_icosphere"].name = "Icosphere"

        else:
            # Reset location and rotation
            o = bpy.data.objects["ldr4pov_sort_indicator"]
            o.location = (0,0,0)
            o.rotation_euler = (0,0,0)


        # Select indicators
        bpy.ops.object.select_all(action="DESELECT")
        bpy.data.objects["ldr4pov_gravity_indicator"].select = True
        bpy.data.objects["ldr4pov_sort_indicator"].select = True


        return{"FINISHED"}



class set_passive(bpy.types.Operator):
    bl_idname = "object.set_passive"
    bl_label = "set_passive"
    bl_description = "Add selected objects as PASSIVE (collision_shape = 'CONVEX_HULL')"
    bl_option = ("REGISTER", "UNDO")

    def execute(self, context):
        scn = bpy.context.scene

        # Deselect indicators
        if "ldr4pov_gravity_indicator" in bpy.data.objects:
            bpy.data.objects["ldr4pov_gravity_indicator"].select = False

        if "ldr4pov_sort_indicator" in bpy.data.objects:
            bpy.data.objects["ldr4pov_sort_indicator"].select = False

        # Deselect non-mesh object, and no-polygon object
        list1 = [o for o in bpy.context.selected_objects if o.type == "MESH" and len(o.data.polygons) != 0]
        if len(list1) == 0:
            return{"FINISHED"}

        bpy.ops.object.select_all(action="DESELECT")
        for o in list1:
            o.select = True

        # Add "PASSIVE"
        scn.objects.active = list1[0]
        #bpy.ops.object.origin_set(type="ORIGIN_CENTER_OF_MASS")
        bpy.ops.rigidbody.objects_add(type="PASSIVE")
        bpy.context.object.rigid_body.collision_shape = "CONVEX_HULL"
        bpy.ops.rigidbody.object_settings_copy()


        return{"FINISHED"}



class fall_simulation(bpy.types.Operator):
    bl_idname = "object.fall_simulation"
    bl_label = "fall_simulation"
    bl_description = "..."
    bl_option = ("REGISTER", "UNDO")

    def execute(self, context):
        scn = bpy.context.scene

        # step1--------------------------------------------------------------------------------------------------------------
        # Initial settings
        # Set accuracy
        if scn.ldr4pov_bake_quality == "1": # Default
            scn.rigidbody_world.steps_per_second = 60
            scn.ldr4pov_simulation_frames = 48 # 2sec in 24fps
            scn.ldr4pov_bake_step = 2
        elif scn.ldr4pov_bake_quality == "2": # Low
            scn.rigidbody_world.steps_per_second = 30
            scn.ldr4pov_simulation_frames = 24 # 1sec in 24fps
            scn.ldr4pov_bake_step = 3

        # Get vector settings from indicators
        if "ldr4pov_gravity_indicator" in bpy.data.objects:
            o = bpy.data.objects["ldr4pov_gravity_indicator"]
            o.location = (0,0,0)
            ldr4pov_gravity_vector = o.matrix_world * mathutils.Vector((0,0,1)) / o.scale[2]
            scn.gravity = ldr4pov_gravity_vector * scn.ldr4pov_gravity_strength

            # Deselect indicator
            o.select = False

        if "ldr4pov_sort_indicator" in bpy.data.objects:
            o = bpy.data.objects["ldr4pov_sort_indicator"]
            o.location = (0,0,0)
            ldr4pov_sort_vector = o.matrix_world * mathutils.Vector((0,0,1))

            # Deselect indicator
            o.select = False

        else:
            ldr4pov_sort_vector = scn.gravity


        # step2--------------------------------------------------------------------------------------------------------------
        # Make a sorted list
        # Make a list of passive objects
        list1 = [o for o in bpy.context.selected_objects if o.rigid_body is not None and o.rigid_body.type == "PASSIVE"]
        if len(list1) == 0:
            return{"FINISHED"}

        # Sort the list by ldr4pov_sort_vector
        list1.sort(key=lambda o: o.location * ldr4pov_sort_vector, reverse = True)


        # step3--------------------------------------------------------------------------------------------------------------
        # Rigid body simulation
        bpy.ops.object.select_all(action="DESELECT")
        frame_start = scn.frame_current +1
        frame_end = scn.frame_current + scn.ldr4pov_simulation_frames -1
        for o in list1:
            o.select = True
            scn.objects.active = o
            o.rigid_body.type = "ACTIVE"

            # Save current location to keyframe
            bpy.ops.anim.keyframe_insert_menu(type="LocRotScale")

            # Start simulation
            scn.rigidbody_world.point_cache.frame_start = frame_start
            scn.rigidbody_world.point_cache.frame_end = frame_end
            bpy.ops.rigidbody.bake_to_keyframes(frame_start=frame_start, frame_end=frame_end, step=scn.ldr4pov_bake_step)
            #bpy.ops.ptcache.free_bake_all()

            #lk? add passive?
            #scn.objects.active.rigid_body.type = "PASSIVE"
            #scn.objects.active.rigid_body.kinematic = True

            o.select = False

            # Move frames for next
            scn.frame_current += scn.ldr4pov_interval
            frame_start += scn.ldr4pov_interval
            frame_end += scn.ldr4pov_interval


        # step4--------------------------------------------------------------------------------------------------------------
        # Correct f-curve for eternal falling
        # Select objects
        #bpy.ops.object.select_all(action="DESELECT")
        for o in list1:
            o.select = True

        # Set f-curve extrapolation_type to "LINEAR"
        bpy.context.area.type="GRAPH_EDITOR"
        bpy.ops.graph.extrapolation_type(type="LINEAR")
        bpy.context.area.type="VIEW_3D"


        # step5--------------------------------------------------------------------------------------------------------------
        scn.frame_end = frame_end - scn.ldr4pov_interval
        scn.frame_current = frame_start -1


        return{"FINISHED"}



# Make a reverse movie #lk?
class reverse_frames(bpy.types.Operator):
    bl_idname = "object.reverse_frames"
    bl_label = "reverse_frames"
    bl_description = "..."
    bl_option = ("REGISTER", "UNDO")

    def execute(self, context):
        scn = bpy.context.scene

        #scn.frame_start = 1


        return{"FINISHED"}



def register():
    bpy.utils.register_class(panel_layout)
    bpy.utils.register_class(initial_setup)
    bpy.utils.register_class(set_passive)
    bpy.utils.register_class(fall_simulation)
    bpy.utils.register_class(reverse_frames)

    # Parameters
    bpy.types.Scene.ldr4pov_gravity_strength = FloatProperty(name="gravity_strength", description="...", default = 10.0, min=0.0)
    #bpy.types.Scene.ldr4pov_sort_vector = FloatVectorProperty(name="sort_vector", description="...", default = (0.0, 0.0, 1.0))
    bpy.types.Scene.ldr4pov_interval = IntProperty(name="interval", description="...", default=5, min=0, step=1)
    bpy.types.Scene.ldr4pov_simulation_frames = IntProperty(name="simulation_frames", description="...", default=48, min=3, step=1)
    bpy.types.Scene.ldr4pov_bake_step = IntProperty(name="bake_step", description="\"Frame Step\" of Bake To Kyeframes", default=2, min=1, step=1)
    bpy.types.Scene.ldr4pov_bake_quality = EnumProperty(
        name="",
        description="...",
        items=[("1","Default","..."),
               ("2","Low","..."),
               ("0","Custom","...")],
        default="1")


def unregister():
    bpy.utils.unregister_class(panel_layout)
    bpy.utils.unregister_class(initial_setup)
    bpy.utils.unregister_class(set_passive)
    bpy.utils.unregister_class(fall_simulation)
    bpy.utils.unregister_class(reverse_frames)

    # Parameters
    del bpy.types.Scene.ldr4pov_gravity_strength
    #del bpy.types.Scene.ldr4pov_sort_vector
    del bpy.types.Scene.ldr4pov_interval
    del bpy.types.Scene.ldr4pov_simulation_frames
    del bpy.types.Scene.ldr4pov_bake_step
    del bpy.types.Scene.ldr4pov_bake_quality


if __name__ == "__main__":
    register()

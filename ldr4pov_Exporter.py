"""
This program is free software.
Feel free to fix, modify, or remake it.
https://github.com/lk-lkaz/ldr4pov
"""


bl_info = {
    "name": "ldr4pov_Exporter",
    "author": "lk.lkaz",
    "version": (0, 0, 1),
    "blender": (2, 67, 0),
    "location": "File > Export",
    "description": "Export LDraw File(.mpd) with comments for POV-Ray",
    "warning": "Only work with \"ldr4pov_Importer.py\"",
    #"wiki_url": "http://",
    #"tracker_url": "http://",
    "category": "Import-Export"}


import bpy
import mathutils, math
import os
from bpy.props import *
from bpy_extras.io_utils import ExportHelper

#RotX90 = mathutils.Matrix.Rotation(math.radians(90), 4, 'X')
RotX90 = mathutils.Matrix(((1,0,0,0),(0,0,-1,0),(0,1,0,0),(0,0,0,1)))


def do_export(context, filepath, scale):
    scn = bpy.context.scene

    lego_obj_animated = []
    lego_obj_static = []
    camera_obj_animated = []
    camera_obj_static = []
    lamp_obj_animated = []
    lamp_obj_static = []

    filename = os.path.basename(filepath).replace(".mpd", "")
    filepath2 = os.path.dirname(filepath) + os.path.sep + filename +"_object_matrix_for_pov.txt"
    filepath3 = os.path.dirname(filepath) + os.path.sep + filename +"_camera_matrix_for_pov.txt"
    filepath4 = os.path.dirname(filepath) + os.path.sep + filename +"_lamp_matrix_for_pov.txt"


    # Switch Animated or Static
    if scn.frame_end == scn.frame_start:
        SWITCH_animated_export = False
        scn.frame_set(scn.frame_start)
    else:
        SWITCH_animated_export = True

    # Make separated lists
    sel = sorted(bpy.context.selected_objects, key=lambda o: o.name)    # Ensure repeatavility
    for o in sel:
        if o.type == 'MESH':
            if ".dat." in o.data.name or ".DAT." in o.data.name:  #lk? LEGO mesh only?
                if SWITCH_animated_export and o.animation_data:
                    lego_obj_animated.append(o)
                else:
                    lego_obj_static.append(o)
        elif o.type == 'CAMERA':
            if SWITCH_animated_export and o.animation_data:
                camera_obj_animated.append(o)
            else:
                camera_obj_static.append(o)
        elif o.type == 'LAMP':
            if SWITCH_animated_export and o.animation_data:
                lamp_obj_animated.append(o)
            else:
                lamp_obj_static.append(o)



    # Output main LDraw file(.mpd) ---------------------------------------------------------------------------------------------------- Output main LDraw file(.mpd)
    file = open(filepath, "wt", encoding="utf-8")

    # Write mainmodel
    file.write("0 FILE main.ldr\n")
    for o in lego_obj_animated:
        file.write( "1 16 0 0 0 1 0 0 0 1 0 0 0 1 {0}.ldr\n".format(o.name) )

    for o in lego_obj_static:
        PartInfo = o.data.name.split(sep=".")  # = ["(part number)", "dat", "(color number)" ]

        # (Correct dimention) * (matrix_world) * (Correct origin)
        PartMat = RotX90 * o.matrix_world * mathutils.Matrix.Translation(mathutils.Vector(o.data.ldr4pov_LDraw_origin))

        # "1 (Color) (Location x,y,z) (Rotation matrix) (Part name).dat\n"
        file.write( "1 {0[2]} {2} {3} {4} {1[0][0]} {1[0][1]} {1[0][2]} {1[1][0]} {1[1][1]} {1[1][2]} {1[2][0]} {1[2][1]} {1[2][2]} {0[0]}.dat\n".format(PartInfo, PartMat, PartMat[0][3]/scale, PartMat[1][3]/scale, PartMat[2][3]/scale) )


    # Write coments for POV-Ray
    file.write(
               "0 \"Header\" ////////////////////////////////////////////////////////////////////////////////////////////////////\n"

              # How to use
              +"0 How to use\n"
              +"0 0. Convert to pov file by LDView, and open in POV-Ray\n"
              +"0 1. Move this \"Header\" section to the head of the pov file\n"
              +"0 2. Delete all \"// DEL__\" to activate comments\n"
              +"0 3. Modify materials, lights, etc.\n"
              +"0 4. Set Command line --> +KI1 +KF{0} +KFI1 +KFF{0}\n".format(scn.frame_end -scn.frame_start +1)
              +"0 5. Run\n"
              +"0 DEL__\n"
              )

    if SWITCH_animated_export:
        file.write(
                  # Set FRAME (="frame" in blender)
                   "0 DEL__// Set FRAME (=\"frame\" in blender)\n"
                  +"0 DEL__#declare FRAME = clock;\n"
                  +"0 DEL__#if(FRAME < 1)\n"
                  +"0 DEL__  #declare FRAME = 1;\n"
                  +"0 DEL__#end\n"
                  +"0 DEL__\n"
                  )

    if camera_obj_animated or camera_obj_static:
        file.write("0 DEL__// Camera ---------------------------------------------------------------------- Camera\n")

        # Write CameraSwitch
        CameraSwitch = 0
        file.write("0 DEL__#declare CameraSwitch = 0;\n")
        for o in camera_obj_animated:
            file.write("0 DEL__//                      {0}: {1}\n".format(CameraSwitch, o.name) )
            CameraSwitch += 1

        for o in camera_obj_static:
            file.write("0 DEL__//                      {0}: {1}\n".format(CameraSwitch, o.name) )
            CameraSwitch += 1

        file.write("0 DEL__\n")


        if camera_obj_animated:
            file.write(
                      # Open camera matrix file, and skip frames
                       "0 DEL__// Open camera matrix file, and skip frames\n"
                      +"0 DEL__#fopen bFile \"{0}\" read\n".format(os.path.basename(filepath3))
                      +"0 DEL__#declare ReadLine = (FRAME -1) *{0} +CameraSwitch;\n".format(len(camera_obj_animated))
                      +"0 DEL__#while(ReadLine > 0)\n"
                      +"0 DEL__  #read (bFile, a,b,c,d,e,f,g,h,i,j,k,l)\n"
                      +"0 DEL__  #declare ReadLine = ReadLine -1;\n"
                      +"0 DEL__#end\n"
                      +"0 DEL__\n"
                      )

        CameraSwitch = 0
        for o in camera_obj_animated:
            file.write(
                       "0 DEL__#if(CameraSwitch = {0})\n".format(CameraSwitch)

                      # camera{}
                      +"0 DEL__camera {\n"
                      +"0 DEL__  right image_width/image_height * < -1,0,0 >\n"
                      +"0 DEL__  angle {0}\n".format(o.data.angle *180/math.pi)
                      +"0 DEL__\n"
                      +"0 DEL__  rotate <0,180,0>\n"
                      +"0 DEL__  #read (bFile, a,b,c,d,e,f,g,h,i,j,k,l)\n"
                      +"0 DEL__  matrix <a,b,c,d,e,f,g,h,i,j,k,l>\n"
                      +"0 DEL__}\n"

                      +"0 DEL__#end\n"

                      +"0 DEL__\n"
                      )
            CameraSwitch += 1

        for o in camera_obj_static:
            PartMat = RotX90 * o.matrix_world
            file.write(
                       "0 DEL__#if(CameraSwitch = {0})\n".format(CameraSwitch)

                      # camera{}
                      +"0 DEL__camera {\n"
                      +"0 DEL__  right image_width/image_height * < -1,0,0 >\n"
                      +"0 DEL__  angle {0}\n".format(o.data.angle *180/math.pi)
                      +"0 DEL__\n"
                      +"0 DEL__  rotate <0,180,0>\n"
                      +"0 DEL__  matrix <{0[0][0]},{0[1][0]},{0[2][0]},\n".format(PartMat)
                      +"0 DEL__          {0[0][1]},{0[1][1]},{0[2][1]},\n".format(PartMat)
                      +"0 DEL__          {0[0][2]},{0[1][2]},{0[2][2]},\n".format(PartMat)
                      +"0 DEL__          {0},{1},{2}>\n".format(PartMat[0][3]/scale, PartMat[1][3]/scale, PartMat[2][3]/scale)
                      +"0 DEL__}\n"

                      +"0 DEL__#end\n"

                      +"0 DEL__\n"
                      )
            CameraSwitch += 1

        file.write(
                  # Skip LDView's default camera
                   "0 DEL__// Skip LDView's default camera\n"
                  +"0 DEL__#declare LDXSkipCamera = true;\n"
                  +"0 DEL__\n"
                  )

    if lamp_obj_animated or lamp_obj_static:
        file.write("0 DEL__// Lights ---------------------------------------------------------------------- Lights\n")

        if lamp_obj_animated:
            file.write(
                      # Open lamp matrix file, and skip frames
                       "0 DEL__// Open lamp matrix file, and skip frames\n"
                      +"0 DEL__#fopen cFile \"{0}\" read\n".format(os.path.basename(filepath4))
                      +"0 DEL__#declare ReadLine = (FRAME -1) *{0};\n".format(len(lamp_obj_animated))
                      +"0 DEL__#while(ReadLine > 0)\n"
                      +"0 DEL__  #read (cFile, a,b,c,d,e,f,g,h,i,j,k,l)\n"
                      +"0 DEL__  #declare ReadLine = ReadLine -1;\n"
                      +"0 DEL__#end\n"
                      +"0 DEL__\n"
                      )

            write_light_source(file, lamp_obj_animated, scale, True)

        if lamp_obj_static:
            write_light_source(file, lamp_obj_static, scale, False)

        file.write(
                  # Skip LDView's default lights
                   "0 DEL__// Skip LDView's default lights\n"
                  +"0 DEL__#declare LDXSkipLight1 = true;\n"
                  +"0 DEL__#declare LDXSkipLight2 = true;\n"
                  +"0 DEL__#declare LDXSkipLight3 = true;\n"
                  +"0 DEL__\n"
                  )

    if lego_obj_animated:
        file.write(
                   "0 DEL__// Objects ---------------------------------------------------------------------- Objects\n"

                  # Open object matrix file, and skip frames
                  +"0 DEL__// Open object matrix file, and skip frames\n"
                  +"0 DEL__#fopen aFile \"{0}\" read\n".format(os.path.basename(filepath2))
                  +"0 DEL__#declare ReadLine = (FRAME -1) *{0};\n".format(len(lego_obj_animated))
                  +"0 DEL__#while(ReadLine > 0)\n"
                  +"0 DEL__  #read (aFile, a,b,c,d,e,f,g,h,i,j,k,l)\n"
                  +"0 DEL__  #declare ReadLine = ReadLine -1;\n"
                  +"0 DEL__#end\n"
                  +"0 DEL__\n"
                  )

    file.write(
               "0 end of \"Header\" /////////////////////////////////////////////////////////////////////////////////////////////\n"
              +"0\n"
              )


    # Write submodels
    for o in lego_obj_animated:
        PartInfo = o.data.name.split(sep=".")
        file.write("0 FILE {0}.ldr\n".format(o.name))

        # Set location (Correct origin)
        # "1 (Color) (Location x,y,z) (Rotation matrix) (Part name).dat\n"
        file.write( "1 {0[2]} {1} {2} {3} 1 0 0 0 1 0 0 0 1 {0[0]}.dat\n".format(PartInfo, o.data.ldr4pov_LDraw_origin[0]/scale, o.data.ldr4pov_LDraw_origin[1]/scale, o.data.ldr4pov_LDraw_origin[2]/scale) )

        # Set matrix
        file.write(
                   "0 DEL__#read (aFile, a,b,c,d,e,f,g,h,i,j,k,l)\n"
                  +"0 DEL__matrix <a,b,c,d,e,f,g,h,i,j,k,l>\n"
                  +"0\n"
                  )

    file.flush()
    file.close()



    # Output object parameters file ---------------------------------------------------------------------------------------------------- Output object parameters file
    if lego_obj_animated:
        file = open(filepath2, "wt", encoding="utf-8")

        # Write matrix_world of each LEGO object for all frames
        for frame in range(scn.frame_end -scn.frame_start +1):
            scn.frame_set(scn.frame_start + frame)
            for o in lego_obj_animated:
                PartMat = RotX90 * o.matrix_world
                # "(Rotation matrix),(Location x,y,z),\n"
                file.write( "{0[0][0]},{0[1][0]},{0[2][0]},{0[0][1]},{0[1][1]},{0[2][1]},{0[0][2]},{0[1][2]},{0[2][2]},{1},{2},{3},\n".format(PartMat, PartMat[0][3]/scale, PartMat[1][3]/scale, PartMat[2][3]/scale) )

        # Write Index
        for o in lego_obj_animated:
            file.write( '"{0}",\n'.format(o.name) )

        file.flush()
        file.close()



    # Output camera parameters file ---------------------------------------------------------------------------------------------------- Output camera parameters file
    if camera_obj_animated:
        file = open(filepath3, "wt", encoding="utf-8")

        # Write matrix_world of each camera object for all frames
        for frame in range(scn.frame_end -scn.frame_start +1):
            scn.frame_set(scn.frame_start + frame)
            for o in camera_obj_animated:
                PartMat = RotX90 * o.matrix_world
                # "(Rotation matrix),(Location x,y,z),\n"
                file.write( "{0[0][0]},{0[1][0]},{0[2][0]},{0[0][1]},{0[1][1]},{0[2][1]},{0[0][2]},{0[1][2]},{0[2][2]},{1},{2},{3},\n".format(PartMat, PartMat[0][3]/scale, PartMat[1][3]/scale, PartMat[2][3]/scale) )

        # Write Index
        for o in camera_obj_animated:
            file.write( '"{0}",\n'.format(o.name) )

        file.flush()
        file.close()



    # Output lamp parameters file ---------------------------------------------------------------------------------------------------- Output lamp parameters file
    if lamp_obj_animated:
        file = open(filepath4, "wt", encoding="utf-8")

        # Write matrix_world of each lamp object for all frames
        for frame in range(scn.frame_end -scn.frame_start +1):
            scn.frame_set(scn.frame_start + frame)
            for o in lamp_obj_animated:
                PartMat = RotX90 * o.matrix_world
                # "(Rotation matrix),(Location x,y,z),\n"
                file.write( "{0[0][0]},{0[1][0]},{0[2][0]},{0[0][1]},{0[1][1]},{0[2][1]},{0[0][2]},{0[1][2]},{0[2][2]},{1},{2},{3},\n".format(PartMat, PartMat[0][3]/scale, PartMat[1][3]/scale, PartMat[2][3]/scale) )

        # Write Index
        for o in lamp_obj_animated:
            file.write( '"{0}",\n'.format(o.name) )

        file.flush()
        file.close()



    return True



def write_light_source(file, list1, scale, SWITCH_animated):
    for o in list1:
        file.write(
                   "0 DEL__// {0}\n".format(o.name)
                  +"0 DEL__light_source {\n"
                  +"0 DEL__  <0,0,0>\n"
                  +"0 DEL__  color rgb <{0[0]},{0[1]},{0[2]}>\n".format(o.data.color)
                  )

        if o.data.type == 'POINT':  # Point light
            pass
        elif o.data.type == 'SUN':  # Parallel light
            file.write(
                       "0 DEL__  parallel\n"
                      +"0 DEL__  point_at <0,0,-1>\n"
                      )
        elif o.data.type == 'SPOT': # Spot light
            file.write(
                       "0 DEL__  spotlight\n"
                      +"0 DEL__  point_at <0,0,-1>\n"
                      +"0 DEL__  radius {0}\n".format( math.atan( math.tan(o.data.spot_size/2) *(1-o.data.spot_blend**2) ) *180/math.pi )  #lk? Correct? (measured by try and error)
                      +"0 DEL__  falloff {0}\n".format(o.data.spot_size *90/math.pi)   # /2 *180/math.pi)
                      +"0 DEL__  //tightness TIGHTNESS\n"
                      )
        elif o.data.type == 'HEMI': #lk? How to support hemi light?
            file.write(
                       "0 DEL__  parallel\n"
                      +"0 DEL__  point_at <0,0,-1>\n"
                      +"0 DEL__  shadowless\n"
                      )
        elif o.data.type == 'AREA': # Area light
            if o.data.shape == 'SQUARE':
                file.write(
                           "0 DEL__  area_light\n"
                          +"0 DEL__  <{0},0,0>, <0,{0},0>, 10, 10\n".format(o.data.size/scale) #lk? 10, 10?
                          +"0 DEL__  //adaptive ADAPTIVE\n"
                          +"0 DEL__  //circular\n"
                          +"0 DEL__  //orient\n"
                          )
            else:   # == 'RECTANGLE':
                file.write(
                           "0 DEL__  area_light\n"
                          +"0 DEL__  <{0},0,0>, <0,{1},0>, 10, 10\n".format(o.data.size/scale, o.data.size_y/scale) #lk? 10, 10?
                          +"0 DEL__  //adaptive ADAPTIVE\n"
                          +"0 DEL__  //circular\n"
                          )


        # Set matrix
        if SWITCH_animated:
            file.write(
                       "0 DEL__  \n"
                      +"0 DEL__  #read (cFile, a,b,c,d,e,f,g,h,i,j,k,l)\n"
                      +"0 DEL__  matrix <a,b,c,d,e,f,g,h,i,j,k,l>\n"
                      +"0 DEL__}\n"
                      +"0 DEL__\n"
                      )
        else:
            PartMat = RotX90 * o.matrix_world
            file.write(
                       "0 DEL__  \n"
                      +"0 DEL__  matrix <{0[0][0]},{0[1][0]},{0[2][0]},\n".format(PartMat)
                      +"0 DEL__          {0[0][1]},{0[1][1]},{0[2][1]},\n".format(PartMat)
                      +"0 DEL__          {0[0][2]},{0[1][2]},{0[2][2]},\n".format(PartMat)
                      +"0 DEL__          {0},{1},{2}>\n".format(PartMat[0][3]/scale, PartMat[1][3]/scale, PartMat[2][3]/scale)
                      +"0 DEL__}\n"
                      +"0 DEL__\n"
                      )



###### EXPORT OPERATOR #######
#memo Based on "io_export_pc2.py"
class Export_ldr4pov(bpy.types.Operator, ExportHelper):
    """Export LDraw File(.mpd) with comments for POV-Ray"""
    bl_idname = "export_scene_ldr4pov.mpd"
    bl_label = "Export LDraw (.mpd)"

    filename_ext = ".mpd"

    ## Export options ##
    scale = FloatProperty(
        name="Scale",
        description="You must ajust this scale value same as import scale",
        #default=0.0004 # Real scale
        default=0.05    # Useful scale
    )

    """
    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label("Export Options:", icon='SCRIPTWIN')
        box.prop(self, "scale")
    """

    def execute(self, context):
        print('\n_____START_____')
        filepath = self.filepath
        filepath = bpy.path.ensure_ext(filepath, self.filename_ext)

        exported = do_export(context, filepath, self.scale)

        if exported:
            print(filepath)

        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager

        if True:
            # File selector
            wm.fileselect_add(self) # will run self.execute()
            return {'RUNNING_MODAL'}
        elif True:
            # search the enum
            wm.invoke_search_popup(self)
            return {'RUNNING_MODAL'}
        elif False:
            # Redo popup
            return wm.invoke_props_popup(self, event)
        elif False:
            return self.execute(context)


### REGISTER ###

def menu_func(self, context):
    self.layout.operator(Export_ldr4pov.bl_idname, text="LDraw (.mpd)")


def register():
    bpy.utils.register_module(__name__)
    bpy.types.INFO_MT_file_export.append(menu_func)


def unregister():
    bpy.utils.unregister_module(__name__)
    bpy.types.INFO_MT_file_export.remove(menu_func)


if __name__ == "__main__":
    register()

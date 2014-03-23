"""
This is just a modified program of "LDR Importer".

If you have an interest in this program, it is better to contribute to the original project on GitHub.
https://github.com/le717/LDR-Importer

"""



"""
Modified by lk.lkaz (http://www.flickr.com/photos/lk-lkaz)
Search "#lk_mod_" to see what I changed.

lk_mod_1
    Fix bug found in a part contains other part(not subpart). Example:"2555.dat" separates into 2 objects.
lk_mod_2
    Keep LDraw's origin.
lk_mod_3
    Use same mesh in same part(in same color).
lk_mod_4
    Delete no-user meshes before start LDrawFile() (to avoid no-material error in lk_mod_3).
lk_mod_5
    For rigid_body simulation,
        Apply scale and change origin to center_of_mass.
        Add new property ".Mesh.ldr4pov_LDraw_origin" to save LDraw's origin.
lk_mod_6
    Trying to avoid conflict with original "LDR Importer"
lk_mod_7
    Scale = 0.05 only. To avoid any error with "ldr4pov_Exporter".

lk_mod_0
    Trivial changes.
    Remove "submodels" in LDrawFile()
"""

# -*- coding: utf-8 -*-
###### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
###### END GPL LICENSE BLOCK #####

bl_info = {
    #lk_mod_6 "name": "LDR Importer",
    "name": "ldr4pov_Importer",
    "description": "Import LDraw models in .ldr and .dat format",
    "author": "David Pluntze, Triangle717, Banbury, Tribex, rioforce, JrMasterModelBuilder",
    "version": (1, 1, 0),
    "blender": (2, 67, 0),
    #lk_mod_6 "api": 31236,
    "location": "File > Import",
    "warning": "Cycles support is incomplete, Bricksmith and MPD models are not supported",
    #lk_mod_6 "wiki_url": "http://wiki.blender.org/index.php/Extensions:2.6/Py/Scripts/Import-Export/LDRAW_Importer",
    #"tracker_url": "maybe"
                #"soon",
    "category": "Import-Export"}

import os
import sys
#lk_mod_0 import math
import mathutils
import traceback
from struct import unpack
from time import strftime

import bpy
from bpy.props import (StringProperty,
                       FloatProperty,
                       BoolProperty,
                       EnumProperty
                       )

from bpy_extras.io_utils import ImportHelper

# Global variables
objects = []
mat_list = {}
colors = {}
scale = 1.0


"""
Default LDraw installation paths
Index 0: Windows
Index 1: Mac OS X
Index 2: Linux
Index 3: User defined, raw string
Storing the paths in a list prevents the creation of global variables
if they are changed. Instead, simply update the proper index.
"""
LDrawDirs = ["C:\\LDraw", "/Applications/ldraw/", "~/ldraw/", r""]

# Location of addon script
addon_path = os.path.abspath(os.path.dirname(__file__))
# Name and location of configuration file
# `up` and `os.path.abspath` is used to break it out of core app files
up = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
#lk_mod_6 config_path = os.path.abspath(os.path.join(up, "presets", "io_import_ldraw"))
config_path = os.path.abspath(os.path.join(up, "presets", "io_import_ldraw_ldr4pov"))
config_filename = os.path.abspath(os.path.join(config_path, "config.py"))


def debugPrint(string):
    """Debug print with timestamp for identification"""
    # Check if it is a list or not
    if type(string) == list:
        string = " ".join(string)

    print("\n[LDR Importer] {0} - {1}\n".format(
          string, strftime("%H:%M:%S")))

# Attempt to read and use the path in the config
try:
    # A hacky trick that basically is: from config import *
    debugPrint("Configuration file found at\n{0}".format(config_filename))
    with open(config_filename, "rt") as f:
        lines = f.read()
    exec(compile(lines, config_filename, 'exec'))

    # Set LDrawDirs[3] to the value that was in the file (ldraw_dir)
    LDrawDirs[3] = ldraw_dir  # lint:ok

# Suppress error when script is run the first time
# and config.py does not yet exist
except FileNotFoundError:  # lint:ok
    pass

# If we had an error, dump the traceback
except Exception as e:
    debugPrint("ERROR: {0}\n{1}\n".format(
               type(e).__name__, traceback.format_exc()))

    debugPrint("ERROR: Reason: {0}.".format(
               type(e).__name__))


class LDrawFile(object):
    """Scans LDraw files"""
    def __init__(self, context, filename, mat, colour=None):

        engine = context.scene.render.engine
        self.points = []
        self.faces = []
        self.material_index = []
        self.subparts = []
        #lk_mod_0 self.submodels = []
        self.part_count = 0

        #lk_mod_2-1 self.mat = mat
        self.mat = mathutils.Matrix()   #lk_memo To keep LDraw's origin
        self.colour = colour
        self.parse(filename)

        # Deselect all objects before import.
        # This prevents them from receiving any cleanup (if applicable).
        bpy.ops.object.select_all(action='DESELECT')

        if len(self.points) > 0 and len(self.faces) > 0:
            #lk_mod_3-1 me = bpy.data.meshes.new('LDrawMesh')
            me = bpy.data.meshes.new(os.path.basename(filename)+"."+self.colour) #lk_memo If you change this line, you must change
            #                                                                    #lk_memo "if os.path.basename(i[0])+"."+str(i[2]) in bpy.data.meshes:"
            me.from_pydata(self.points, [], self.faces)
            me.validate()
            me.update()

            for i, f in enumerate(me.polygons):
                n = self.material_index[i]

                # Use Cycles materials if user is using Cycles
                if engine == 'CYCLES':
                    material = getCyclesMaterial(n)
                # Non-Cycles materials (BI, BGE, POV-Ray, etc...)
                else:
                    material = getMaterial(n)

                if material is not None:
                    if me.materials.get(material.name) is None:
                        me.materials.append(material)

                    f.material_index = me.materials.find(material.name)

            self.ob = bpy.data.objects.new('LDrawObj', me)
            self.ob.name = os.path.basename(filename)

            #lk_mod_2-2 self.ob.location = (0, 0, 0)
            self.ob.matrix_world = mat

            objects.append(self.ob)

            # Link object to scene
            bpy.context.scene.objects.link(self.ob)
            
            #lk_mod_5-1 ----------------------------------------------------------------------------------------------------lk_mod_5-1
            #lk_memo Apply scale and change origin to center_of_mass. (for rigid_body simulation)
            self.ob.select = True
            
            # Apply scale
            bpy.ops.object.transform_apply(scale=True)
            
            #lk? if CleanUpOpt != "DoNothing":
            # Change origin
            lk_tmp_matrix = self.ob.matrix_world.copy()
            self.ob.matrix_world = mathutils.Matrix()
            bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS')
            
            # Save the vector between "New origin" --> "LDraw's origin"
            self.ob.data.ldr4pov_LDraw_origin = -self.ob.location
            
            # Set new matrix
            self.ob.matrix_world = lk_tmp_matrix * self.ob.matrix_world
            
            self.ob.select = False
            #lk_mod_5-1_end ----------------------------------------------------------------------------------------------------lk_mod_5-1_end

        #lk_mod_3-2 ----------------------------------------------------------------------------------------------------lk_mod_3-2
        #lk_memo Use same mesh in same part(in same color)
        """
        for i in self.subparts:
            self.submodels.append(LDrawFile(context, i[0], i[1], i[2]))
        """
        for i in self.subparts:
            if os.path.basename(i[0])+"."+str(i[2]) in bpy.data.meshes:
                me = bpy.data.meshes[os.path.basename(i[0])+"."+str(i[2])]
                
                self.ob = bpy.data.objects.new(os.path.basename(i[0]), me)    #lk_memo "[NAME].001" or some
                
                self.ob.matrix_world = mat * i[1]
                
                objects.append(self.ob)
                
                # Link object to scene
                bpy.context.scene.objects.link(self.ob)
                
                #lk_mod_5-2
                # Correct scale and location
                self.ob.scale = (1,1,1)
                bpy.context.scene.update()
                self.ob.location -= self.ob.matrix_world.to_3x3() * mathutils.Vector(self.ob.data.ldr4pov_LDraw_origin)
                #lk_mod_5-2_end
            else:
                #lk_mod_0 self.submodels.append(LDrawFile(context, i[0], mat*i[1], i[2]))
                LDrawFile(context, i[0], mat*i[1], i[2])
        #lk_mod_3-2_end ----------------------------------------------------------------------------------------------------lk_mod_3-2_end

    def parse_line(self, line):
        """Harvest the information from each line"""
        verts = []
        color = line[1]

        if color == '16':
            color = self.colour

        num_points = int((len(line) - 2) / 3)
        #matrix = mathutils.Matrix(mat)
        for i in range(num_points):
                self.points.append(
                    (self.mat * mathutils.Vector((float(line[i * 3 + 2]),
                     float(line[i * 3 + 3]), float(line[i * 3 + 4])))).
                    to_tuple())
                verts.append(len(self.points) - 1)
        self.faces.append(verts)
        self.material_index.append(color)

    def parse_quad(self, line):
        """Properly construct quads in each brick"""
        color = line[1]
        verts = []
        num_points = 4
        v = []

        if color == '16':
            color = self.colour

        #lk_mod_0
        """
        v.append(self.mat * mathutils.Vector((float(line[0 * 3 + 2]),
                 float(line[0 * 3 + 3]), float(line[0 * 3 + 4]))))
        v.append(self.mat * mathutils.Vector((float(line[1 * 3 + 2]),
                 float(line[1 * 3 + 3]), float(line[1 * 3 + 4]))))
        v.append(self.mat * mathutils.Vector((float(line[2 * 3 + 2]),
                 float(line[2 * 3 + 3]), float(line[2 * 3 + 4]))))
        v.append(self.mat * mathutils.Vector((float(line[3 * 3 + 2]),
                 float(line[3 * 3 + 3]), float(line[3 * 3 + 4]))))
        """
        v.append(self.mat * mathutils.Vector((float(line[2]),
                 float(line[3]), float(line[4]))))
        v.append(self.mat * mathutils.Vector((float(line[5]),
                 float(line[6]), float(line[7]))))
        v.append(self.mat * mathutils.Vector((float(line[8]),
                 float(line[9]), float(line[10]))))
        v.append(self.mat * mathutils.Vector((float(line[11]),
                 float(line[12]), float(line[13]))))
        #lk_mod_0_end

        nA = (v[1] - v[0]).cross(v[2] - v[0])
        nB = (v[2] - v[1]).cross(v[3] - v[1])

        for i in range(num_points):
            verts.append(len(self.points) + i)

        if (nA.dot(nB) < 0):
            self.points.extend([v[0].to_tuple(), v[1].to_tuple(),
                               v[3].to_tuple(), v[2].to_tuple()])
        else:
            self.points.extend([v[0].to_tuple(), v[1].to_tuple(),
                               v[2].to_tuple(), v[3].to_tuple()])

        self.faces.append(verts)
        self.material_index.append(color)

    def parse(self, filename):
        """Construct tri's in each brick"""
        subfiles = []

        while True:
            isPart = False
            if os.path.exists(filename):

                # Check if this is a main part or a subpart
                if not isSubPart(filename):
                    isPart = True

                # Read the brick using relative path (to entire model)
                with open(filename, "rt", encoding="utf-8") as f_in:
                    lines = f_in.readlines()

            else:
                # Search for the brick in the various folders
                fname, isPart = locate(filename)

                # It exists, read it and get the data
                if os.path.exists(fname):
                    with open(fname, "rt", encoding="utf-8") as f_in:
                        lines = f_in.readlines()

                # The brick does not exist
                else:
                    debugPrint("File not found: {0}".format(fname))
                    return False

            self.part_count += 1
            #lk_mod_1-1 if self.part_count > 1 and isPart:
            if self.part_count > 1 and isPart and len(self.faces) == 0: #lk_memo Add new condition for a part contains other part(not subpart). Example:"2555.dat"
                self.subparts.append([filename, self.mat, self.colour])
            else:
                for retval in lines:
                    tmpdate = retval.strip()
                    if tmpdate != '':
                        tmpdate = tmpdate.split()

                        #lk_mod_1-2
                        """
                        # LDraw brick comments
                        if tmpdate[0] == "0":
                            if len(tmpdate) >= 3:
                                if (
                                    tmpdate[1] == "!LDRAW_ORG" and
                                    'Part' in tmpdate[2]
                                ):
                                    if self.part_count > 1:
                                        self.subparts.append(
                                            [filename, self.mat, self.colour]
                                        )
                                        break
                        """
                        #lk_mod_1-2_end

                        # The brick content
                        if tmpdate[0] == "1":
                            new_file = tmpdate[14]
                            x, y, z, a, b, c, d, e, f, g, h, i = map(
                                float, tmpdate[2:14])
                            #mat_new = self.mat * mathutils.Matrix(
                                #[[a, d, g, 0], [b, e, h, 0], [c, f, i, 0],
                                 #[x, y, z, 1]])
                            mat_new = self.mat * mathutils.Matrix(
                                ((a, b, c, x), (d, e, f, y), (g, h, i, z),
                                 (0, 0, 0, 1)))

                            color = tmpdate[1]
                            if color == '16':
                                color = self.colour
                            subfiles.append([new_file, mat_new, color])

                        # Triangle (tri)
                        if tmpdate[0] == "3":
                            self.parse_line(tmpdate)

                        # Quadrilateral (quad)
                        if tmpdate[0] == "4":
                            self.parse_quad(tmpdate)

            if len(subfiles) > 0:
                subfile = subfiles.pop()
                filename = subfile[0]
                self.mat = subfile[1]
                self.colour = subfile[2]
            else:
                break


def getMaterial(colour):
    """Get Blender Internal Material Values"""
    if colour in colors:
        if not (colour in mat_list):
            mat = bpy.data.materials.new("Mat_{0}_".format(colour))
            col = colors[colour]

            mat.diffuse_color = col["color"]

            alpha = col["alpha"]
            if alpha < 1.0:
                mat.use_transparency = True
                mat.alpha = alpha

            mat.emit = col["luminance"] / 100

            if col["material"] == "CHROME":
                mat.specular_intensity = 1.4
                mat.roughness = 0.01
                mat.raytrace_mirror.use = True
                mat.raytrace_mirror.reflect_factor = 0.3

            elif col["material"] == "PEARLESCENT":
                mat.specular_intensity = 0.1
                mat.roughness = 0.32
                mat.raytrace_mirror.use = True
                mat.raytrace_mirror.reflect_factor = 0.07

            elif col["material"] == "RUBBER":
                mat.specular_intensity = 0.19

            elif col["material"] == "METAL":
                mat.specular_intensity = 1.473
                mat.specular_hardness = 292
                mat.diffuse_fresnel = 0.93
                mat.darkness = 0.771
                mat.roughness = 0.01
                mat.raytrace_mirror.use = True
                mat.raytrace_mirror.reflect_factor = 0.9

            #elif col["material"] == "GLITTER":
            #    slot = mat.texture_slots.add()
            #    tex = bpy.data.textures.new("GlitterTex", type = "STUCCI")
            #    tex.use_color_ramp = True
            #
            #    slot.texture = tex

            else:
                mat.specular_intensity = 0.2

            mat_list[colour] = mat

        return mat_list[colour]

    return None


def getCyclesMaterial(colour):
    """Get Cycles Material Values"""
    if colour in colors:
        if not (colour in mat_list):
            col = colors[colour]

            if col["name"] == "Milky_White":
                mat = getCyclesMilkyWhite("Mat_{0}_".format(colour),
                                          col["color"])

            elif (col["material"] == "BASIC" and col["luminance"]) == 0:
                mat = getCyclesBase("Mat_{0}_".format(colour),
                                    col["color"], col["alpha"])

            elif col["luminance"] > 0:
                mat = getCyclesEmit("Mat_{0}_".format(colour), col["color"],
                                    col["alpha"], col["luminance"])

            elif col["material"] == "CHROME":
                mat = getCyclesChrome("Mat_{0}_".format(colour), col['color'])

            elif col["material"] == "PEARLESCENT":
                mat = getCyclesPearlMetal("Mat_{0}_".format(colour),
                                          col["color"], 0.2)

            elif col["material"] == "METAL":
                mat = getCyclesPearlMetal("Mat_{0}_".format(colour),
                                          col["color"], 0.5)

            elif col["material"] == "RUBBER":
                mat = getCyclesRubber("Mat_{0}_".format(colour),
                                      col["color"], col["alpha"])

            else:
                mat = getCyclesBase("Mat_{0}_".format(colour),
                                    col["color"], col["alpha"])

            mat_list[colour] = mat

        return mat_list[colour]
    else:
        mat_list[colour] = getCyclesBase("Mat_{0}_".format(colour),
                                         (1, 1, 0), 1.0)
        return mat_list[colour]

    return None


def getCyclesBase(name, diff_color, alpha):
    """Base Material, Mix shader and output node"""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True

    # Set viewport color to be the same as material color
    mat.diffuse_color = diff_color

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    for n in nodes:
        nodes.remove(n)

    mix = nodes.new('ShaderNodeMixShader')
    mix.location = 0, 90

    out = nodes.new('ShaderNodeOutputMaterial')
    out.location = 290, 100

    if alpha == 1.0:
        mix.inputs['Fac'].default_value = 0.05
        node = nodes.new('ShaderNodeBsdfDiffuse')
        node.location = -242, 154
        node.inputs['Color'].default_value = diff_color + (1.0,)
        node.inputs['Roughness'].default_value = 0.0

    else:
        """
        The alpha transparency used by LDraw is too simplistic for Cycles,
        so I'm not using the value here. Other transparent colors
        like 'Milky White' will need special materials.
        """
        mix.inputs['Fac'].default_value = 0.05
        node = nodes.new('ShaderNodeBsdfGlass')
        node.location = -242, 154
        node.inputs['Color'].default_value = diff_color + (1.0,)
        node.inputs['Roughness'].default_value = 0.01

        # The IOR of LEGO brick plastic is 1.46
        node.inputs['IOR'].default_value = 1.46

    aniso = nodes.new('ShaderNodeBsdfGlossy')
    aniso.location = -242, -23
    aniso.inputs['Roughness'].default_value = 0.05

    links.new(mix.outputs[0], out.inputs[0])
    links.new(node.outputs[0], mix.inputs[1])
    links.new(aniso.outputs[0], mix.inputs[2])

    return mat


def getCyclesEmit(name, diff_color, alpha, luminance):

    mat = bpy.data.materials.new(name)
    mat.use_nodes = True

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    for n in nodes:
        nodes.remove(n)

    mix = nodes.new('ShaderNodeMixShader')
    mix.location = 0, 90
    mix.inputs['Fac'].default_value = luminance / 100

    out = nodes.new('ShaderNodeOutputMaterial')
    out.location = 290, 100

    """
    NOTE: The alpha value again is not making much sense here.
    I'm leaving it in, in case someone has an idea how to use it.
    """

    trans = nodes.new('ShaderNodeBsdfTranslucent')
    trans.location = -242, 154
    trans.inputs['Color'].default_value = diff_color + (1.0,)

    emit = nodes.new('ShaderNodeEmission')
    emit.location = -242, -23

    links.new(mix.outputs[0], out.inputs[0])
    links.new(trans.outputs[0], mix.inputs[1])
    links.new(emit.outputs[0], mix.inputs[2])

    return mat


def getCyclesChrome(name, diff_color):
    """Cycles Chrome Material"""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    for n in nodes:
        nodes.remove(n)

    out = nodes.new('ShaderNodeOutputMaterial')
    out.location = 290, 100

    glass = nodes.new('ShaderNodeBsdfGlossy')
    glass.location = -242, 154
    glass.inputs['Color'].default_value = diff_color + (1.0,)
    glass.inputs['Roughness'].default_value = 0.05

    links.new(glass.outputs[0], out.inputs[0])

    return mat


def getCyclesPearlMetal(name, diff_color, roughness):

    mat = bpy.data.materials.new(name)
    mat.use_nodes = True

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    for n in nodes:
        nodes.remove(n)

    mix = nodes.new('ShaderNodeMixShader')
    mix.location = 0, 90
    mix.inputs['Fac'].default_value = 0.4

    out = nodes.new('ShaderNodeOutputMaterial')
    out.location = 290, 100

    glossy = nodes.new('ShaderNodeBsdfGlossy')
    glossy.location = -242, 154
    glossy.inputs['Color'].default_value = diff_color + (1.0,)
    glossy.inputs['Roughness'].default_value = 3.25

    aniso = nodes.new('ShaderNodeBsdfDiffuse')
    aniso.location = -242, -23
    aniso.inputs['Roughness'].default_value = 0.0

    links.new(mix.outputs[0], out.inputs[0])
    links.new(glossy.outputs[0], mix.inputs[1])
    links.new(aniso.outputs[0], mix.inputs[2])

    return mat


def getCyclesRubber(name, diff_color, alpha):
    """Cycles Rubber Material"""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    for n in nodes:
        nodes.remove(n)

    mix = nodes.new('ShaderNodeMixShader')
    mix.location = 0, 90

    out = nodes.new('ShaderNodeOutputMaterial')
    out.location = 290, 100

    if alpha == 1.0:
        mix.inputs['Fac'].default_value = 0.05
        node = nodes.new('ShaderNodeBsdfDiffuse')
        node.location = -242, 154
        node.inputs['Color'].default_value = diff_color + (1.0,)
        node.inputs['Roughness'].default_value = 0.3

    else:
        """
        The alpha transparency used by LDraw is too simplistic for Cycles,
        so I'm not using the value here. Other transparent colors
        like 'Milky White' will need special materials.
        """
        mix.inputs['Fac'].default_value = 0.1
        node = nodes.new('ShaderNodeBsdfGlass')
        node.location = -242, 154
        node.inputs['Color'].default_value = diff_color + (1.0,)
        node.inputs['Roughness'].default_value = 0.01
        node.inputs['IOR'].default_value = 1.5191

    aniso = nodes.new('ShaderNodeBsdfAnisotropic')
    aniso.location = -242, -23
    aniso.inputs['Roughness'].default_value = 0.5
    aniso.inputs['Anisotropy'].default_value = 0.02

    links.new(mix.outputs[0], out.inputs[0])
    links.new(node.outputs[0], mix.inputs[1])
    links.new(aniso.outputs[0], mix.inputs[2])

    return mat


def getCyclesMilkyWhite(name, diff_color):

    mat = bpy.data.materials.new(name)
    mat.use_nodes = True

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    for n in nodes:
        nodes.remove(n)

    mix = nodes.new('ShaderNodeMixShader')
    mix.location = 0, 90
    mix.inputs['Fac'].default_value = 0.1

    out = nodes.new('ShaderNodeOutputMaterial')
    out.location = 290, 100

    trans = nodes.new('ShaderNodeBsdfTranslucent')
    trans.location = -242, 154
    trans.inputs['Color'].default_value = diff_color + (1.0,)

    diff = nodes.new('ShaderNodeBsdfDiffuse')
    diff.location = -242, -23
    diff.inputs['Color'].default_value = diff_color + (1.0,)
    diff.inputs['Roughness'].default_value = 0.1

    links.new(mix.outputs[0], out.inputs[0])
    links.new(trans.outputs[0], mix.inputs[1])
    links.new(diff.outputs[0], mix.inputs[2])

    return mat


def isSubPart(brick):
    """Check if brick is a main part or a subpart"""

    if str.lower(os.path.split(brick)[0]) == "s":
        isSubpart = True
    else:
        isSubpart = False

    return isSubpart


def locate(pattern):
    """
    Locate all files matching supplied filename pattern in and below
    supplied root directory.
    Check all available possible folders so every single brick
    can be imported, even unofficial ones.
    """
    fname = pattern.replace("\\", os.path.sep)
    isPart = False

    #lint:disable
    # Define all possible folders in the library, including unofficial bricks

    # Standard Paths
    ldrawPath = os.path.join(LDrawDir, fname)
    hiResPath = os.path.join(LDrawDir, "p".lower(), "48".lower(), fname)
    primitivesPath = os.path.join(LDrawDir, "p".lower(), fname)
    partsPath = os.path.join(LDrawDir, "parts".lower(), fname)
    partsSPath = os.path.join(LDrawDir, "parts".lower(), "s".lower(), fname)

    # Unoffical Paths
    UnofficialPath = os.path.join(LDrawDir, "unofficial".lower(), fname)
    UnofficialhiResPath = os.path.join(LDrawDir, "unofficial".lower(),
                                       "p".lower(), "48".lower(), fname)
    UnofficialPrimPath = os.path.join(LDrawDir, "unofficial".lower(),
                                      "p".lower(), fname)
    UnofficialPartsPath = os.path.join(LDrawDir, "unofficial".lower(),
                                       "parts".lower(), fname)
    UnofficialPartsSPath = os.path.join(LDrawDir, "unofficial".lower(),
                                        "parts".lower(), "s".lower(), fname)
    #lint:enable
    if os.path.exists(ldrawPath):
        fname = ldrawPath
    elif os.path.exists(hiResPath) and HighRes:  # lint:ok
        fname = hiResPath
    elif os.path.exists(primitivesPath):
        fname = primitivesPath
    elif os.path.exists(partsPath):
        fname = partsPath
        isPart = True   #lk_mod_1-3
    elif os.path.exists(partsSPath):
        fname = partsSPath
    elif os.path.exists(UnofficialPath):
        fname = UnofficialPath
    elif os.path.exists(UnofficialhiResPath):
        fname = UnofficialhiResPath
    elif os.path.exists(UnofficialPrimPath):
        fname = UnofficialPrimPath
    elif os.path.exists(UnofficialPartsPath):
        fname = UnofficialPartsPath
        #lk? isPart = True   #lk_mod_1-4
    elif os.path.exists(UnofficialPartsSPath):
        fname = UnofficialPartsSPath

        # Since this is not a subpart, mark it as a root part
        if not isSubPart(fname):
            isPart = True
    else:
        debugPrint("Could not find file {0}".format(fname))

    # TODO: Currently will return the inputted path, possibly causing
    # any error checking to clearuntil it tries to actually load parts.
    return (fname, isPart)


def create_model(self, scale, context):
    """Create the actual model"""
    global objects
    global colors
    global mat_list

    file_name = self.filepath
    debugPrint("Attempting to import {0}".format(file_name))

    # Make sure the model ends with the proper file extension
    if not (
        file_name.endswith(".ldr")
        or file_name.endswith(".dat")
    ):

        debugPrint('''ERROR: Reason: Invalid File Type
Must be a .ldr or .dat''')
        self.report({'ERROR'}, '''Error: Invalid File Type
Must be a .ldr or .dat''')
        return {'CANCELLED'}

    # It has the proper file extension, continue with the import
    else:
        try:

            """
            Set the initial transformation matrix,
            set the scale factor to 0.05,
            and rotate -90 degrees around the x-axis,
            so the object is upright.
            """
            
            #lk_mod_0
            """
            mat = mathutils.Matrix(
                ((1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1))) * scale
            mat = mat * mathutils.Matrix.Rotation(math.radians(-90), 4, 'X')
            """
            mat = mathutils.Matrix(((scale,0,0,0),(0,0,scale,0),(0,-scale,0,0),(0,0,0,1)))
            #lk_mod_0_end

            # If LDrawDir does not exist, stop the import
            if not os.path.isdir(LDrawDir):
                debugPrint(''''ERROR: Cannot find LDraw installation at
{0}'''.format(LDrawDir))
                self.report({'ERROR'}, '''Cannot find LDraw installation at
{0}'''.format(LDrawDir))
                return {'CANCELLED'}

            colors = {}
            mat_list = {}

            # Get material list from LDConfig.ldr
            scanLDConfig(self)

            #lk_mod_4-1
            # Delete no-user meshes
            for me in bpy.data.meshes:
                if me.users == 0 and ('.dat.' in me.name or '.DAT.' in me.name):    #lk? LEGO mesh only?
                    bpy.data.meshes.remove(me)
            #lk_mod_4-1_end

            LDrawFile(context, file_name, mat)

            """
            Remove doubles and recalculate normals in each brick.
            The model is super high-poly without the cleanup.
            Cleanup can be disabled by user if wished.
            """

            # Default values for model cleanup options
            CleanUp = False
            GameFix = False

            # The CleanUp option was selected
            if CleanUpOpt == "CleanUp":  # lint:ok
                CleanUp = True
                debugPrint("CleanUp option selected")

            # The GameFix option was selected
            elif CleanUpOpt == "GameFix":  # lint:ok
                GameFix = True
                debugPrint("GameFix option selected")

            # Standard cleanup actions
            if (CleanUp or GameFix):  # lint:ok

                # Select all the mesh
                for cur_obj in objects:
                    cur_obj.select = True
                    bpy.context.scene.objects.active = cur_obj
                    if bpy.ops.object.mode_set.poll():

                        # Change to edit mode
                        bpy.ops.object.mode_set(mode='EDIT')
                        bpy.ops.mesh.select_all(action='SELECT')

                        # Remove doubles, calculate normals
                        bpy.ops.mesh.remove_doubles(threshold=0.01)
                        bpy.ops.mesh.normals_make_consistent()
                        if bpy.ops.object.mode_set.poll():

                            # Go back to object mode, set origin to geometry
                            bpy.ops.object.mode_set(mode='OBJECT')
                            #lk_mod_2_3 bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY')

                            # Set smooth shading
                            bpy.ops.object.shade_smooth()

           # -------- Actions only for CleanUp option -------- #

            if CleanUp:  # lint:ok
                # Add 30 degree edge split modifier to all bricks
                for cur_obj in objects:
                    edges = cur_obj.modifiers.new(
                        "Edge Split", type='EDGE_SPLIT')
                    edges.split_angle = 0.523599

            # -------- Actions only for GameFix option -------- #

            if GameFix:  # lint:ok
                for cur_obj in objects:
                    # Add 0.7 ratio decimate modifier to all bricks
                    deci = cur_obj.modifiers.new("Decimate", type='DECIMATE')
                    deci.ratio = 0.7

                    # Add 45 degree edge split modifier to all bricks
                    edges = cur_obj.modifiers.new("Edge Split",
                                                  type='EDGE_SPLIT')
                    edges.split_angle = 0.802851

            # Select all the mesh now that import is complete
            for cur_obj in objects:
                cur_obj.select = True

            # Update the scene with the changes
            context.scene.update()
            objects = []

            # Always reset 3D cursor to <0,0,0> after import
            bpy.context.scene.cursor_location = (0.0, 0.0, 0.0)

            # Display success message
            debugPrint("{0} successfully imported!".format(file_name))
            return {'FINISHED'}

        except Exception as e:
            debugPrint("ERROR: {0}\n{1}\n".format(
                       type(e).__name__, traceback.format_exc()))

            debugPrint("ERROR: Reason: {0}.".format(
                       type(e).__name__))

            self.report({'ERROR'}, '''File not imported ("{0}").
Check the console logs for more information.'''.format(type(e).__name__))
            return {'CANCELLED'}


def scanLDConfig(self):
    """Scan LDConfig to get the material color info."""
    # LDConfig.ldr does not exist for some reason
    if not os.path.exists(os.path.join(LDrawDir, "LDConfig.ldr")):
        self.report({'ERROR'}, '''Could not find LDConfig.ldr at
{0}
Check the console logs for more information.'''.format(LDrawDir))

        debugPrint('''ERROR: Could not find LDConfig.ldr at
{0}'''.format(LDrawDir))
        return {'CANCELLED'}

    with open(os.path.join(LDrawDir, "LDConfig.ldr"), "rt") as ldconfig:
        ldconfig_lines = ldconfig.readlines()

    for line in ldconfig_lines:
        if len(line) > 3:
            if line[2:4].lower() == '!c':
                line_split = line.split()

                name = line_split[2]
                code = line_split[4]

                color = {
                    "name": name,
                    "color": hex_to_rgb(line_split[6][1:]),
                    "alpha": 1.0,
                    "luminance": 0.0,
                    "material": "BASIC"
                }

                #if len(line_split) > 10 and line_split[9] == 'ALPHA':
                if hasColorValue(line_split, "ALPHA"):
                    color["alpha"] = int(
                        getColorValue(line_split, "ALPHA")) / 256.0

                if hasColorValue(line_split, "LUMINANCE"):
                    color["luminance"] = int(
                        getColorValue(line_split, "LUMINANCE"))

                if hasColorValue(line_split, "CHROME"):
                    color["material"] = "CHROME"

                if hasColorValue(line_split, "PEARLESCENT"):
                    color["material"] = "PEARLESCENT"

                if hasColorValue(line_split, 'RUBBER'):
                    color["material"] = "RUBBER"

                if hasColorValue(line_split, "METAL"):
                    color["material"] = "METAL"

                if hasColorValue(line_split, "MATERIAL"):
                    subline = line_split[line_split.index("MATERIAL"):]

                    color["material"] = getColorValue(subline, "MATERIAL")
                    color["secondary_color"] = getColorValue(subline, "VALUE")[1:]
                    color["fraction"] = getColorValue(subline, "FRACTION")
                    color["vfraction"] = getColorValue(subline, "VFRACTION")
                    color["size"] = getColorValue(subline, "SIZE")
                    color["minsize"] = getColorValue(subline, "MINSIZE")
                    color["maxsize"] = getColorValue(subline, "MAXSIZE")

                colors[code] = color


def hasColorValue(line, value):
    """Check if the color value is present"""
    return value in line


def getColorValue(line, value):

    if value in line:
        n = line.index(value)
        return line[n + 1]


def findWinLDrawDir():
    """Detect LDraw Installation Path on Windows"""
    # Use previously defined path if it exists
    if LDrawDirs[3] != r"":
        install_path = LDrawDirs[3]

    # No previous path, so check at default installation (C:\\LDraw)
    elif os.path.isfile(os.path.join(LDrawDirs[0], "LDConfig.ldr")):
        install_path = LDrawDirs[0]

    # If that fails, look in Program Files
    elif os.path.isfile(os.path.join(
                        "C:\\Program Files\\LDraw", "LDConfig.ldr")):
        install_path = "C:\\Program Files\\LDraw"

    # If it fails again, look in Program Files (x86)
    elif os.path.isfile(os.path.join(
                        "C:\\Program Files (x86)\\LDraw", "LDConfig.ldr")):
        install_path = "C:\\Program Files (x86)\\LDraw"

    # If all that fails, fall back to default installation
    else:
        install_path = LDrawDirs[0]

    # Update the list with the path (avoids creating a global variable)
    LDrawDirs[0] = install_path


def RunMe(self, context):
    """Run process to store the installation path"""
    saveInstallPath(self)


def hex_to_rgb(rgb_str):
    """Convert color hex value to RGB value"""
    int_tuple = unpack('BBB', bytes.fromhex(rgb_str))
    return tuple([val / 255 for val in int_tuple])

# Model cleanup options
# DoNothing option does not require any checks
CLEANUP_OPTIONS = (
    ("CleanUp", "Basic Cleanup",
     "Removes double vertices, recalculate normals, add Edge Split modifier"),
    ("GameFix", "Video Game Optimization",
     "Optimize model for video game usage (Decimate Modifier)"),
    ("DoNothing", "Original LDraw Mesh", "Import LDraw Mesh as Original"),
)

# ------------ Operator ------------ #


class LDRImporterOps(bpy.types.Operator, ImportHelper):
    """LDR Importer Operator"""
    bl_idname = "import_scene.ldraw"
    bl_description = "Import an LDraw model (.ldr/.dat)"
    bl_label = "Import LDraw Model"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_options = {'REGISTER', 'UNDO'}

    # File type filter in file browser
    filename_ext = ".ldr"

    filter_glob = StringProperty(
        default="*.ldr;*.dat",
        options={'HIDDEN'}
    )

    # The installation path was defined, use it
    if LDrawDirs[3] != r"":
        FinalLDrawDir = LDrawDirs[3]

    # The installation path was not defined, fall back to defaults
    # On Windows, this means attempting to detect the installation
    else:

        # Run Windows installation path detection process
        if sys.platform == "win32":
            findWinLDrawDir()

        FinalLDrawDir = {
            "win32": LDrawDirs[0],
            "darwin": LDrawDirs[1]
        }.get(sys.platform, LDrawDirs[2])

    debugPrint('''The LDraw Parts Library installation path to be used is
{0}'''.format(FinalLDrawDir))

    ldrawPath = StringProperty(
        name="LDraw Path",
        description="Path to the LDraw Parts Library",
        default=FinalLDrawDir,
        update=RunMe
    )

    ## Import options ##

    scale = FloatProperty(
        name="Scale",
        description="Scale the model by this amount",
        default=0.05
    )

    highResBricks = BoolProperty(
        name="Use High-res bricks",
        description="Import high-resolution bricks in your model",
        default=False
    )

    cleanUpModel = EnumProperty(
        name="Model Cleanup Options",
        items=CLEANUP_OPTIONS,
        description="Model cleanup options"
    )

    def draw(self, context):
        """Display model cleanup options"""
        layout = self.layout
        box = layout.box()
        box.label("Import Options:", icon='SCRIPTWIN')
        box.prop(self, "ldrawPath", icon="FILESEL")
        #lk_mod_7 box.prop(self, "scale")
        box.prop(self, "highResBricks", icon="MOD_BUILD")
        box.label("Model Cleanup:", icon='EDIT')
        box.prop(self, "cleanUpModel", expand=True)

    def execute(self, context):
        """Set import options and run the script"""
        global LDrawDir, CleanUp, GameFix, HighRes, CleanUpOpt
        LDrawDir = str(self.ldrawPath)
        HighRes = bool(self.highResBricks)
        CleanUpOpt = str(self.cleanUpModel)

        # Display message if HighRes bricks are to be used
        if HighRes:
            debugPrint("High resolution bricks option selected")

        """
        Blender for Windows does not like the 'update' key in ldrawPath{},
        so force it to run. We can run the process directly,
        rather than going through RunMe().
        """
        if sys.platform == "win32":
            saveInstallPath(self)

        create_model(self, self.scale, context)
        return {'FINISHED'}


def saveInstallPath(self):
    """Save the LDraw installation path for future use"""
    # The contents of the configuration file
    config_contents = '''# -*- coding: utf-8 -*-
# LDR Importer Configuration File #

# Path to the LDraw Parts Library
{0}"{1}"
'''.format("ldraw_dir = r", self.ldrawPath)

    # Create the config path if it does not exist
    if not os.path.exists(config_path):
        os.makedirs(config_path)

    # Write the config file
    with open(config_filename, "wt") as f:
        f.write(config_contents)


def menu_import(self, context):
    """Import menu listing label"""
    self.layout.operator(LDRImporterOps.bl_idname, text="LDraw (.ldr/.dat)")


def register():
    """Register Menu Listing"""
    bpy.utils.register_module(__name__)
    bpy.types.INFO_MT_file_import.append(menu_import)
    
    bpy.types.Mesh.ldr4pov_LDraw_origin = bpy.props.FloatVectorProperty(name="LDraw_origin", description="Save LDraw's origin", default = (0.0, 0.0, 0.0))	#lk_mod_5-3

    
def unregister():
    """Unregister Menu Listing"""
    bpy.utils.unregister_module(__name__)
    bpy.types.INFO_MT_file_import.remove(menu_import)
    
    del bpy.types.Mesh.ldr4pov_LDraw_origin	#lk_mod_5-4


if __name__ == "__main__":
    register()

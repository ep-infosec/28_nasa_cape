#!/bin/bash

# Required modules
. $MODULESHOME/init/bash
module load pycart
module load aflr3

# Convert to ASCII tri
pc_UH3D2Tri.py -i bullet-far.uh3d -c bullet-far.xml

# Convert to surface
pc_Tri2Surf.py \
    -i  bullet-far.tri \
    -c  bullet-far.xml \
    -bc bullet-inviscid.bc \
    -o  bullet-inviscid.surf

# Create the mesh
aflr3 -i bullet-inviscid.surf -o bullet-inviscid.ugrid \
    angblisimx=175 -grow1 nqual=2

# Nice copy
ugc bullet-inviscid.ugrid bullet-inviscid.cgns

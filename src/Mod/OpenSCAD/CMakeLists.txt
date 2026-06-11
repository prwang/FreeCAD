# SPDX-License-Identifier: LGPL-2.1-or-later

IF (BUILD_GUI)
    PYSIDE_WRAP_RC(OpenSCAD_QRC_SRCS Resources/OpenSCAD.qrc)
ENDIF (BUILD_GUI)

SET(OpenSCAD_SRCS
    Init.py
    InitGui.py
    OpenSCAD2Dgeom.py
    OpenSCADFeatures.py
    OpenSCADUtils.py
    OpenSCADCommands.py
    exportCSG.py
    importCSG.py
    tokrules.py
    colorcodeshapes.py
    expandplacements.py
    replaceobj.py
    TestOpenSCADApp.py
)
IF (BUILD_GUI)
	LIST(APPEND OpenSCAD_SRCS TestOpenSCADGui.py)
ENDIF (BUILD_GUI)
SOURCE_GROUP("" FILES ${OpenSCAD_SRCS})

SET(OpenSCADTests_SRCS
    OpenSCADTest/__init__.py
    OpenSCADTest/test_information.md
)

SET(OpenSCADTestsApp_SRCS
    OpenSCADTest/app/__init__.py
    OpenSCADTest/app/test_importCSG.py
)

SET(OpenSCADTestsGui_SRCS
    OpenSCADTest/gui/__init__.py
    OpenSCADTest/gui/test_dummy.py
)

SET(OpenSCADTestsFiles_SRCS
    OpenSCADTest/data/__init__.py
    OpenSCADTest/data/CSG.scad
    OpenSCADTest/data/CSG.csg
    OpenSCADTest/data/Cube.stl
    OpenSCADTest/data/Square.dxf
    OpenSCADTest/data/Surface.dat
    OpenSCADTest/data/Surface2.dat
    OpenSCADTest/data/Surface.png
)

SET(OpenSCADTests_ALL
	${OpenSCADTests_SRCS}
	${OpenSCADTestsApp_SRCS}
	${OpenSCADTestsFiles_SRCS}
	)

# headless CSG->STEP conversion & validation harness (see its README.md);
# ships with the package so deployed installs can run the conversion flow
SET(OpenSCADCsgIsolation_SRCS
    csg_isolation/README.md
    csg_isolation/csg2step.py
    csg_isolation/run_all.py
    csg_isolation/validate.py
    csg_isolation/trace_null.py
    csg_isolation/minimize.py
)

SET(OpenSCADCsgIsolationCorpus_SRCS
    csg_isolation/corpus/intersection_three_children.csg
    csg_isolation/corpus/lazy_offset_chain.csg
    csg_isolation/corpus/background_modifier.csg
    csg_isolation/corpus/offset_fillet_closing.csg
)

IF (BUILD_GUI)
	LIST(APPEND OpenSCADTests_ALL ${OpenSCADTestsGui_SRCS})
ENDIF (BUILD_GUI)


set(all_files
    ${OpenSCAD_SRCS}
    ${OpenSCADCsgIsolation_SRCS}
    ${OpenSCADCsgIsolationCorpus_SRCS}
)

SET(OpenSCADGuiIcon_SVG
    Resources/icons/OpenSCADWorkbench.svg
)

ADD_CUSTOM_TARGET(OpenSCAD ALL
    SOURCES ${all_files} ${OpenSCAD_QRC_SRCS} ${OpenSCADGuiIcon_SVG}
)

ADD_CUSTOM_TARGET(OpenSCADTests ALL
    SOURCES ${OpenSCADTests_ALL}
)

fc_copy_sources(OpenSCAD "${CMAKE_BINARY_DIR}/Mod/OpenSCAD" ${all_files})

fc_copy_sources(OpenSCAD "${CMAKE_BINARY_DIR}/${CMAKE_INSTALL_DATADIR}/Mod/OpenSCAD" ${OpenSCADGuiIcon_SVG})

fc_copy_sources(OpenSCADTests "${CMAKE_BINARY_DIR}/Mod/OpenSCAD" ${OpenSCADTests_ALL})

IF (BUILD_GUI)
    fc_target_copy_resource(OpenSCAD
        ${CMAKE_CURRENT_BINARY_DIR}
        ${CMAKE_BINARY_DIR}/Mod/OpenSCAD
        OpenSCAD_rc.py)
ENDIF (BUILD_GUI)

INSTALL(
    FILES
        ${ply_SRCS}
    DESTINATION
        Mod/OpenSCAD/ply
)
INSTALL(
    FILES
        ${OpenSCAD_SRCS}
        ${OpenSCAD_QRC_SRCS}
    DESTINATION
        Mod/OpenSCAD
)
INSTALL(
    FILES
        ${OpenSCADGuiIcon_SVG}
    DESTINATION
       "${CMAKE_INSTALL_DATADIR}/Mod/OpenSCAD/Resources/icons"
)

INSTALL(FILES ${OpenSCADCsgIsolation_SRCS} DESTINATION Mod/OpenSCAD/csg_isolation)
INSTALL(FILES ${OpenSCADCsgIsolationCorpus_SRCS} DESTINATION Mod/OpenSCAD/csg_isolation/corpus)

INSTALL(FILES ${OpenSCADTests_SRCS} DESTINATION Mod/OpenSCAD/OpenSCADTest)
INSTALL(FILES ${OpenSCADTestsApp_SRCS} DESTINATION Mod/OpenSCAD/OpenSCADTest/app)
INSTALL(FILES ${OpenSCADTestsGui_SRCS} DESTINATION Mod/OpenSCAD/OpenSCADTest/gui)
INSTALL(FILES ${OpenSCADTestsFiles_SRCS} DESTINATION Mod/OpenSCAD/OpenSCADTest/data)

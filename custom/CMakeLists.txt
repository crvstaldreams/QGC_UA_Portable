message(STATUS "QGC UA: enabling custom build")

set_property(DIRECTORY ${CMAKE_SOURCE_DIR}
    APPEND PROPERTY COMPILE_DEFINITIONS
    QGC_CUSTOM_BUILD
    QGC_PORTABLE_BUILD
    CUSTOMHEADER="CustomPlugin.h"
    CUSTOMCLASS=CustomPlugin
)

set(CUSTOM_SOURCES
    ${CMAKE_CURRENT_SOURCE_DIR}/src/CustomPlugin.cc
    ${CMAKE_CURRENT_SOURCE_DIR}/src/CustomPlugin.h
    CACHE INTERNAL "" FORCE
)

set(CUSTOM_LIBRARIES "" CACHE INTERNAL "" FORCE)
set(CUSTOM_INCLUDE_DIRECTORIES
    ${CMAKE_CURRENT_SOURCE_DIR}/src
    CACHE INTERNAL "" FORCE
)

if(NOT DEFINED QGC_UA_LICENSE_DIR)
    message(FATAL_ERROR "QGC_UA_LICENSE_DIR must point to the bundled third-party license directory")
endif()

# Normalize Windows backslashes before this value is embedded into cmake_install.cmake.
# Otherwise paths such as D:\a\... are parsed as CMake escape sequences (for example \a).
file(TO_CMAKE_PATH "${QGC_UA_LICENSE_DIR}" QGC_UA_LICENSE_DIR_CMAKE)
if(NOT IS_DIRECTORY "${QGC_UA_LICENSE_DIR_CMAKE}")
    message(FATAL_ERROR "QGC_UA_LICENSE_DIR does not exist: ${QGC_UA_LICENSE_DIR_CMAKE}")
endif()

install(FILES
    ${CMAKE_SOURCE_DIR}/LICENSE-APACHE
    ${CMAKE_SOURCE_DIR}/LICENSE-GPL
    ${CMAKE_CURRENT_SOURCE_DIR}/THIRD_PARTY_NOTICES.txt
    DESTINATION licenses
)

install(DIRECTORY
    "${QGC_UA_LICENSE_DIR_CMAKE}/"
    DESTINATION licenses/third-party
)

cmake_minimum_required(VERSION 3.14)
project(fairsight LANGUAGES CXX)

set(BINARY_NAME "FairSight")

cmake_policy(SET CMP0079 NEW)

# Standard Flutter windows configuration
set(INSTALL_BUNDLE_DATA_DIR "${CMAKE_INSTALL_PREFIX}/data")
set(INSTALL_BUNDLE_LIB_DIR "${CMAKE_INSTALL_PREFIX}")

# Apply compiler settings
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Configure the application runner
add_subdirectory("runner")

# Generated plugin build rules
include(flutter/generated_plugins.cmake OPTIONAL)

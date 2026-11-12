cmake_minimum_required(VERSION 3.14)
project(runner LANGUAGES CXX)

# Source files
set(SOURCES
  "flutter_window.cpp"
  "main.cpp"
  "utils.cpp"
  "win32_window.cpp"
  "Runner.rc"
  "runner.exe.manifest"
)

add_executable(${BINARY_NAME} WIN32
  ${SOURCES}
)

target_compile_definitions(${BINARY_NAME} PRIVATE
  UNICODE
  _UNICODE
  NOMINMAX
)

target_include_directories(${BINARY_NAME} PRIVATE
  "${CMAKE_CURRENT_SOURCE_DIR}"
  "${FLUTTER_MANAGED_DIR}"
)

# Link Flutter and Windows libraries
target_link_libraries(${BINARY_NAME} PRIVATE
  flutter
  flutter_wrapper_app
)

# Standard Windows libraries
target_link_libraries(${BINARY_NAME} PRIVATE
  shlwapi.lib
  dwmapi.lib
)

add_dependencies(${BINARY_NAME} flutter_assemble)

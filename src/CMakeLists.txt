cmake_minimum_required(VERSION 3.16)

project(CaptureNodeProject LANGUAGES CXX C)

find_package(OpenCV REQUIRED)
message(STATUS "OpenCV ${OpenCV_VERSION} found at ${OpenCV_INCLUDE_DIRS}")

set(CAPTURE_SRC ${CMAKE_CURRENT_SOURCE_DIR}/capture.cpp)
set(CAPTURE_HDR ${CMAKE_CURRENT_SOURCE_DIR}/capture.h)

add_executable(capture_app ${CAPTURE_SRC} ${CAPTURE_HDR})

target_compile_features(capture_app PRIVATE cxx_std_17)

target_include_directories(capture_app PRIVATE 
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${OpenCV_INCLUDE_DIRS}
)

target_link_libraries(capture_app PRIVATE 
    ${OpenCV_LIBS}
    stdc++
    pthread
)
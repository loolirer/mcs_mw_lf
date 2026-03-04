# OpenCV.cmake
# This tells Lingua Franca's auto-generated CMake how to build your C++ file

# 0. ENABLE C++ COMPILATION (This fixes the CXX error)
enable_language(CXX)

# 1. Find OpenCV on the Raspberry Pi
find_package(OpenCV REQUIRED)

# 2. Tell LF to compile your C++ file alongside the generated C code
target_sources(${LF_MAIN_TARGET} PRIVATE ${CMAKE_CURRENT_LIST_DIR}/capture.cpp)

# 3. Force C++17 standard for your OpenCV file
set_source_files_properties(${CMAKE_CURRENT_LIST_DIR}/capture.cpp PROPERTIES LANGUAGE CXX)
target_compile_features(${LF_MAIN_TARGET} PRIVATE cxx_std_17)

# 4. Link OpenCV, the C++ standard library, and pthreads to the Lingua Franca binary
target_include_directories(${LF_MAIN_TARGET} PRIVATE ${OpenCV_INCLUDE_DIRS} ${CMAKE_CURRENT_LIST_DIR})
target_link_libraries(${LF_MAIN_TARGET} PRIVATE ${OpenCV_LIBS} stdc++ pthread)
/**
 * capture.cpp
 *
 * OpenCV capture + blob detection library for the Lingua Franca
 * CaptureNode reactor.
 *
 * All timer scheduling and inter-node communication is handled by
 * Lingua Franca.  This file is responsible only for:
 *
 *   1. Opening / configuring the Pi camera (via V4L2 / OpenCV).
 *   2. Grabbing one frame when requested.
 *   3. Pre-processing the frame (background suppression, contrast
 *      stretch, blur, histogram equalisation).
 *   4. Detecting reflective marker blobs with SimpleBlobDetector.
 *   5. Returning the result as a plain BlobFrame struct.
 *
 * Build alongside the LF-generated C code:
 *   g++ -std=c++17 -O2 -c capture.cpp -o capture.o \
 *       $(pkg-config --cflags opencv4)
 *
 *   Then link with the LF artefacts:
 *   gcc lf_generated.c capture.o -o capture_node \
 *       $(pkg-config --libs opencv4) -lstdc++ -lpthread
 *
 * Dependencies:
 *   OpenCV 4.x  (apt install libopencv-dev)
 */

#include "capture.h"

#include <opencv2/opencv.hpp>

#include <chrono>
#include <cstdio>
#include <memory>
#include <vector>
#include <algorithm>
#include <iostream>
#include <thread>

// ─────────────────────────────────────────────
// Compile-time constants
// ─────────────────────────────────────────────

static constexpr int   CAM_WIDTH     = 960;
static constexpr int   CAM_HEIGHT    = 720;
static constexpr int   CAM_FPS       = 30;
static constexpr int   EXPOSURE_TIME = 20000;   // µs (informational for V4L2)

// Image pre-processing parameters (mirrors original Python pipeline)
static constexpr int   CUTOFF        = 100;     // background subtraction level

// ─────────────────────────────────────────────
// Module-level state  (initialised by capture_init)
// ─────────────────────────────────────────────

static cv::VideoCapture                g_cap;
static cv::Ptr<cv::SimpleBlobDetector> g_detector;
static int                             g_node_index  = -1;
static bool                            g_initialised = false;

// ─────────────────────────────────────────────
// Internal helpers
// ─────────────────────────────────────────────

/**
 * Build the SimpleBlobDetector with parameters tuned for small
 * retroreflective IR/visible markers.
 */
static cv::Ptr<cv::SimpleBlobDetector> makeBlobDetector() {
    cv::SimpleBlobDetector::Params p;

    // A blob must survive three consecutive threshold levels
    p.minRepeatability    = 3;
    p.minThreshold        = 50;
    p.thresholdStep       = 50;
    p.maxThreshold        = p.minThreshold
                          + p.thresholdStep * static_cast<int>(p.minRepeatability);

    p.minDistBetweenBlobs = 1.0f;

    // Detect white blobs
    p.filterByColor = true;
    p.blobColor     = 255;

    p.filterByArea        = false;
    p.minArea             = 1.0f;
    p.maxArea             = 40.0f;

    p.filterByCircularity = false;
    p.minCircularity      = 0.59f;

    p.filterByConvexity   = false;
    p.minConvexity        = 1.00f;

    p.filterByInertia     = false;

    return cv::SimpleBlobDetector::create(p);
}

/**
 * Pre-process a raw grayscale frame to maximise marker contrast.
 *
 * Pipeline (mirrors original Python capture.py):
 *   1. Subtract CUTOFF  →  clips low-intensity background to zero.
 *   2. Stretch [0, 255-CUTOFF] → [0, 255]  (contrast amplification).
 *   3. 3×3 Gaussian blur  →  suppresses single-pixel noise.
 *   4. Histogram equalisation  →  maximises local contrast.
 */
static cv::Mat preprocessFrame(const cv::Mat& gray) {
    cv::Mat proc;

    cv::subtract(gray, cv::Scalar(CUTOFF), proc);

    const double alpha = 255.0 / (255.0 - CUTOFF);
    proc.convertTo(proc, CV_8U, alpha, 0.0);

    cv::GaussianBlur(proc, proc, cv::Size(3, 3), 0);
    cv::equalizeHist(proc, proc);

    return proc;
}

/** POSIX wall-clock time as a double (seconds since epoch). */
static double nowSeconds() {
    using namespace std::chrono;
    return duration_cast<duration<double>>(
               system_clock::now().time_since_epoch()).count();
}

// ─────────────────────────────────────────────
// Public C API  (declared extern "C" in capture.h)
// ─────────────────────────────────────────────

extern "C" {

// ── capture_init ─────────────────────────────────────────────────────────

int capture_init(int node_index) {
    g_node_index = node_index;

    // Force the ISP to output RGBx, then convert to BGR for OpenCV
    std::string pipeline = "libcamerasrc ! video/x-raw, width=" + std::to_string(CAM_WIDTH) + 
                           ", height=" + std::to_string(CAM_HEIGHT) + 
                           ", framerate=" + std::to_string(CAM_FPS) + "/1, format=RGBx " +
                           "! videoconvert ! video/x-raw, format=BGR ! appsink drop=true max-buffers=1 sync=false";

    // Open using the GStreamer backend
    g_cap.open(pipeline, cv::CAP_GSTREAMER);
    
    if (!g_cap.isOpened()) {
        std::fprintf(stderr, "[CaptureNode %d] ERROR: Could not open native libcamera pipeline\n", node_index);
        return -1;
    }

    // Flush a few frames to let the ISP auto-exposure settle
    cv::Mat dummy;
    for(int i = 0; i < 5; i++) {
        g_cap.read(dummy);
    }

    g_detector    = makeBlobDetector();
    g_initialised = true;

    std::printf("[CaptureNode %d] Native Camera initialised via libcamerasrc (%dx%d @ %d fps)\n",
                node_index, CAM_WIDTH, CAM_HEIGHT, CAM_FPS);
    return 0;
}

// Add this helper function in the "Internal helpers" section
static void save_debug_image(const cv::Mat& img, const std::vector<cv::KeyPoint>& keypoints, int shot) {
    cv::Mat out;
    // Convert grayscale back to BGR so we can draw colorful circles
    if (img.channels() == 1) cv::cvtColor(img, out, cv::COLOR_GRAY2BGR);
    else out = img.clone();

    // Draw detected blobs (Red circles)
    for (const auto& kp : keypoints) {
        cv::circle(out, kp.pt, kp.size, cv::Scalar(0, 0, 255), 2);
    }

    std::string filename = "debug_shot_" + std::to_string(shot) + ".jpg";
    cv::imwrite(filename, out);
    std::printf("   [DEBUG] Image saved to %s\n", filename.c_str());
}

float (*capture_frame(int shot_number, BlobFrame* out))[3] {
    if (!g_initialised || !out) return nullptr;

    cv::Mat bgr;
    g_cap >> bgr;
    if (bgr.empty()) {
        std::fprintf(stderr, "[CaptureNode %d] WARNING: Empty frame on shot %d\n", g_node_index, shot_number);
        return nullptr;
    }

    const double ts = nowSeconds();
    cv::Mat gray;
    cv::cvtColor(bgr, gray, cv::COLOR_BGR2GRAY);
    gray = gray(cv::Rect(0, 0, std::min(CAM_WIDTH, gray.cols), std::min(CAM_HEIGHT, gray.rows)));

    cv::Mat proc = preprocessFrame(gray);

    std::vector<cv::KeyPoint> keypoints;
    g_detector->detect(proc, keypoints);

    // Uncomment to save shots
    //save_debug_image(proc, keypoints, shot_number);

    out->node_index  = g_node_index;
    out->shot_number = shot_number;
    out->timestamp   = ts;

    const int count = static_cast<int>(std::min(keypoints.size(), static_cast<size_t>(MAX_BLOBS)));
    out->blob_count = count;

    for (int i = 0; i < count; ++i) {
        out->blobs[i][0] = keypoints[i].pt.x;
        out->blobs[i][1] = keypoints[i].pt.y;
        out->blobs[i][2] = keypoints[i].size / 2.0f;
    }
    for (int i = count; i < MAX_BLOBS; ++i) {
        out->blobs[i][0] = 0.0f; out->blobs[i][1] = 0.0f; out->blobs[i][2] = 0.0f;
    }

    // Uncomment to see log
    //std::printf("[CaptureNode %d][shot %05d] %d blob(s) detected\n", g_node_index, shot_number, count);
    
    // Return the pointer to the 2D array inside the struct
    return out->blobs;
}

// ── capture_cleanup ──────────────────────────────────────────────────────

void capture_cleanup(void) {
    if (g_cap.isOpened())
        g_cap.release();
    g_detector.reset();
    g_initialised = false;
    std::printf("[CaptureNode %d] Camera released\n", g_node_index);
}

}   /* extern "C" */

// ── Standalone Test Main ─────────────────────────────────────────────────────
// This only compiles if you define BUILD_EXECUTABLE (e.g., in CMake)
/*
int main(int argc, char** argv) {
    int node_id = (argc > 1) ? std::stoi(argv[1]) : 0;
    
    std::printf("=== Starting Standalone Capture Test (Node %d) ===\n", node_id);

    if (capture_init(node_id) != 0) {
        return 1;
    }

    BlobFrame frame;
    // Capture 5 test frames
    for (int i = 1; i <= 5; ++i) {
        auto result = capture_frame(i, &frame);
        if (!result) break;

        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }

    capture_cleanup();
    std::printf("=== Test Complete ===\n");
    return 0;
}
*/
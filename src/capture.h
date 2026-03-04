/**
 * capture.h
 *
 * C-compatible interface for the OpenCV capture library used by the
 * CaptureNode Lingua Franca reactor (C target).
 *
 * The implementation (capture.cpp) is compiled as C++ but exposes
 * its API via extern "C" so that the LF-generated C code can link
 * against it without name-mangling issues.
 */

#ifndef CAPTURE_H
#define CAPTURE_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>

/* ── Blob data layout ───────────────────────────────────────────────────
 *
 * Each detected marker blob is stored as three consecutive floats:
 *   [ cx,  cy,  radius ]
 *
 * Up to MAX_BLOBS blobs are reported per frame.
 */
#define MAX_BLOBS 64

/**
 * BlobFrame — output payload produced by one capture+detect cycle.
 *
 * This is the type used for the LF `data_out` port.  It carries every
 * piece of information the central server needs to reconstruct 3-D
 * marker positions from multiple camera views:
 *
 *   node_index   – which Raspberry Pi this frame came from
 *   shot_number  – monotonically increasing counter reset on each
 *                  capture session; used to correlate frames across nodes
 *   timestamp    – POSIX wall-clock time (seconds) at the moment the
 *                  camera buffer was grabbed
 *   blob_count   – number of valid entries in `blobs[]`
 *   blobs        – [cx, cy, radius] for each detected marker (pixels)
 */
typedef struct {
    int    node_index;
    int    shot_number;
    double timestamp;
    int    blob_count;
    float  blobs[MAX_BLOBS][3];   /* [0]=cx  [1]=cy  [2]=radius */
} BlobFrame;


/* ── Lifecycle API ──────────────────────────────────────────────────────
 *
 * These three functions map 1-to-1 onto the three LF reaction kinds:
 *   capture_init()    → startup  reaction
 *   capture_frame()   → trigger  reaction
 *   capture_cleanup() → shutdown reaction
 */

/**
 * capture_init() — open the camera and build the blob detector.
 *
 * @param node_index  Index of this CaptureNode (0, 1, 2 …).
 *                    Stored inside BlobFrame.node_index for every frame.
 * @return  0 on success, -1 on failure (camera could not be opened).
 */
int capture_init(int node_index);

/**
 * capture_frame() — capture one frame and detect reflective markers.
 *
 * Called from the LF reaction that fires on `capture_trigger`.
 * The function:
 *   1. Grabs a raw grayscale frame from the camera.
 *   2. Pre-processes it (background subtraction → contrast stretch →
 *      Gaussian blur → histogram equalisation).
 *   3. Runs SimpleBlobDetector to find bright marker blobs.
 *   4. Fills `out` and returns.
 *
 * The call is intentionally blocking and synchronous — Lingua Franca's
 * deadline mechanism is responsible for deciding whether the result
 * arrives in time.
 *
 * @param shot_number  Logical shot index supplied by the LF reactor
 *                     (incremented by the reactor, not here).
 * @param out          Caller-allocated BlobFrame that will be filled.
 * @return  Number of blobs detected (≥ 0), or -1 on capture error.
 */
int capture_frame(int shot_number, BlobFrame* out);

/**
 * capture_cleanup() — release camera and all OpenCV resources.
 *
 * Safe to call even if capture_init() was never called or failed.
 */
void capture_cleanup(void);


#ifdef __cplusplus
}   /* extern "C" */
#endif

#endif /* CAPTURE_H */

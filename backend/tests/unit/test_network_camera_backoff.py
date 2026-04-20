import time

from app.services.network_camera_pool_service import NetworkCameraWorker
from app.services.network_camera_pool_service import network_camera_pool


def test_network_camera_worker_backoff_grows_and_is_capped():
    worker = NetworkCameraWorker(
        "rtsp://camera-1",
        retry_base_seconds=0.5,
        retry_max_seconds=2.0,
    )

    worker._set_error("Cannot open stream")
    worker._schedule_retry()
    assert worker.stats()["retry_delay_seconds"] == 0.5

    worker._set_error("Cannot open stream")
    worker._schedule_retry()
    assert worker.stats()["retry_delay_seconds"] == 1.0

    worker._set_error("Cannot open stream")
    worker._schedule_retry()
    assert worker.stats()["retry_delay_seconds"] == 2.0

    worker._set_error("Cannot open stream")
    worker._schedule_retry()
    assert worker.stats()["retry_delay_seconds"] == 2.0


def test_network_camera_worker_backoff_resets_after_success():
    worker = NetworkCameraWorker(
        "rtsp://camera-2",
        retry_base_seconds=1.0,
        retry_max_seconds=4.0,
    )

    worker._set_error("Cannot open stream")
    worker._schedule_retry()
    assert worker.stats()["retry_delay_seconds"] == 1.0

    worker._set_success()
    stats = worker.stats()
    assert stats["retry_delay_seconds"] == 0.0
    assert stats["next_retry_at"] is None
    assert stats["consecutive_failures"] == 0


def test_network_camera_pool_skips_stale_frames():
    worker = NetworkCameraWorker("rtsp://camera-3")
    worker._latest_frame = [1, 2, 3]
    worker._latest_frame_at = time.time() - 10.0

    active_worker = NetworkCameraWorker("rtsp://camera-4")
    active_worker._latest_frame = [4, 5, 6]
    active_worker._latest_frame_at = time.time()

    original_workers = network_camera_pool._workers
    network_camera_pool._workers = {
        worker.source: worker,
        active_worker.source: active_worker,
    }
    try:
        frames, skipped_stale = network_camera_pool.collect_frames(
            max_frame_age_seconds=1.0
        )
    finally:
        network_camera_pool._workers = original_workers

    assert len(frames) == 1
    assert frames[0][0] == "rtsp://camera-4"
    assert skipped_stale == 1

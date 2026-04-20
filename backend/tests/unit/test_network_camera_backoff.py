from app.services.network_camera_pool_service import NetworkCameraWorker


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

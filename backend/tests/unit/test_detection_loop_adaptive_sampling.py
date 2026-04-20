from app.services.detection_loop import DetectionLoop


def test_detection_loop_skips_unstable_network_source_after_threshold():
    loop = DetectionLoop()
    loop._cycle_counter = 2

    should_skip = loop._should_skip_unstable_source(
        "rtsp://cam-1",
        {
            "rtsp://cam-1": {
                "source": "rtsp://cam-1",
                "consecutive_failures": 4,
            }
        },
        failure_threshold=3,
        cycle_skip=2,
    )

    assert should_skip is True


def test_detection_loop_keeps_local_and_stable_sources_active():
    loop = DetectionLoop()
    loop._cycle_counter = 1

    assert (
        loop._should_skip_unstable_source(
            "local",
            {},
            failure_threshold=3,
            cycle_skip=2,
        )
        is False
    )
    assert (
        loop._should_skip_unstable_source(
            "rtsp://cam-2",
            {
                "rtsp://cam-2": {
                    "source": "rtsp://cam-2",
                    "consecutive_failures": 1,
                }
            },
            failure_threshold=3,
            cycle_skip=2,
        )
        is False
    )

import argparse
import json
import os
import random
import sys
import time
from typing import Iterator
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import urlopen

import cv2
import numpy as np
import uvicorn
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

# Ensure `app` package is importable when running as a script.
BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app.core.database import init_db
from app.core.schemas import ConfigPayload, FaceCreatePayload
from app.services.config_service import read_config, update_config
from app.services.encoder_service import extract_embeddings
from app.services.face_service import create_face, list_faces


TVMAZE_BASE = "https://api.tvmaze.com"


def _fetch_json(url: str):
    with urlopen(url, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def _fetch_bytes(url: str) -> bytes:
    with urlopen(url, timeout=20) as response:
        return response.read()


def _decode_image(image_bytes: bytes):
    raw = np.frombuffer(image_bytes, dtype=np.uint8)
    return cv2.imdecode(raw, cv2.IMREAD_COLOR)


def _find_show(show_query: str) -> dict | None:
    url = f"{TVMAZE_BASE}/search/shows?q={quote(show_query)}"
    data = _fetch_json(url)
    if not data:
        return None
    return data[0].get("show")


def _fetch_cast(show_id: int) -> list[dict]:
    return _fetch_json(f"{TVMAZE_BASE}/shows/{show_id}/cast")


def _image_url_from_cast_item(item: dict) -> str | None:
    person = item.get("person") or {}
    image = person.get("image") or {}
    return image.get("original") or image.get("medium")


def _name_from_cast_item(item: dict) -> str:
    person = item.get("person") or {}
    return str(person.get("name") or "unknown")


def _enroll_actor(name: str, image_url: str) -> bool:
    try:
        image_bytes = _fetch_bytes(image_url)
    except URLError:
        return False

    frame = _decode_image(image_bytes)
    if frame is None:
        return False

    embeddings = extract_embeddings(frame)
    if not embeddings:
        return False

    create_face(FaceCreatePayload(name=name, encoding=embeddings[0]))
    return True


def import_actors(show_query: str, limit: int, name_prefix: str, skip_existing: bool) -> None:
    init_db()
    show = _find_show(show_query)
    if not show:
        raise SystemExit(f"Show not found: {show_query}")

    show_id = int(show["id"])
    show_name = str(show.get("name", show_query))
    cast = _fetch_cast(show_id)
    existing_names = {face.name for face in list_faces()}

    imported = 0
    attempted = 0
    for item in cast:
        if imported >= limit:
            break
        image_url = _image_url_from_cast_item(item)
        if not image_url:
            continue

        raw_name = _name_from_cast_item(item)
        name = f"{name_prefix}{raw_name}".strip()
        attempted += 1

        if skip_existing and name in existing_names:
            print(f"[SKIP] {name} already exists")
            continue

        ok = _enroll_actor(name, image_url)
        if ok:
            imported += 1
            existing_names.add(name)
            print(f"[OK] enrolled {name}")
        else:
            print(f"[FAIL] {name}")

    print(
        f"Done. show='{show_name}' attempted={attempted} imported={imported} limit={limit}"
    )


def configure_camera_stream(stream_url: str, mode: str) -> None:
    init_db()
    current = read_config()

    if mode == "local":
        next_payload = ConfigPayload(
            detection_interval_seconds=current.detection_interval_seconds,
            match_threshold=current.match_threshold,
            camera_index=current.camera_index,
            camera_source=stream_url,
            network_camera_sources=current.network_camera_sources,
            multi_camera_cycle_budget_seconds=current.multi_camera_cycle_budget_seconds,
            enroll_frames_count=current.enroll_frames_count,
            face_crop_padding_ratio=current.face_crop_padding_ratio,
        )
    else:
        sources = [s for s in current.network_camera_sources if s != stream_url]
        sources.append(stream_url)
        sources = sources[:10]
        next_payload = ConfigPayload(
            detection_interval_seconds=current.detection_interval_seconds,
            match_threshold=current.match_threshold,
            camera_index=current.camera_index,
            camera_source=current.camera_source,
            network_camera_sources=sources,
            multi_camera_cycle_budget_seconds=current.multi_camera_cycle_budget_seconds,
            enroll_frames_count=current.enroll_frames_count,
            face_crop_padding_ratio=current.face_crop_padding_ratio,
        )

    saved = update_config(next_payload)
    print(
        "Config updated:",
        {
            "camera_source": saved.camera_source,
            "network_camera_sources_count": len(saved.network_camera_sources),
        },
    )


def _render_debug_overlay(frame, source_name: str):
    text = time.strftime("%Y-%m-%d %H:%M:%S")
    cv2.putText(
        frame,
        f"{source_name} | {text}",
        (12, 24),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 255),
        2,
    )
    return frame


def _build_stream_generator(
    video_path: str,
    fps: float,
    simulate_real_camera: bool,
    jitter_ms: int,
    drop_frame_probability: float,
    freeze_probability: float,
    freeze_seconds: float,
    outage_probability: float,
    outage_seconds: float,
    seed: int | None,
) -> Iterator[bytes]:
    delay_seconds = max(0.01, 1.0 / max(1.0, fps))
    rng = random.Random(seed)
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")
    last_encoded: bytes | None = None
    source_name = os.path.basename(video_path)
    try:
        while True:
            if simulate_real_camera and rng.random() < outage_probability:
                time.sleep(max(0.1, outage_seconds))
                continue

            ok, frame = cap.read()
            if not ok:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue

            frame = _render_debug_overlay(frame, source_name)

            if simulate_real_camera and rng.random() < drop_frame_probability:
                jitter = rng.uniform(-jitter_ms / 1000.0, jitter_ms / 1000.0)
                time.sleep(max(0.005, delay_seconds + jitter))
                continue

            ok_enc, encoded = cv2.imencode(".jpg", frame)
            if ok_enc:
                last_encoded = encoded.tobytes()

            if last_encoded is not None:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + last_encoded + b"\r\n"
                )

            if (
                simulate_real_camera
                and last_encoded is not None
                and rng.random() < freeze_probability
            ):
                freeze_until = time.monotonic() + max(0.1, freeze_seconds)
                while time.monotonic() < freeze_until:
                    yield (
                        b"--frame\r\n"
                        b"Content-Type: image/jpeg\r\n\r\n" + last_encoded + b"\r\n"
                    )
                    jitter = rng.uniform(-jitter_ms / 1000.0, jitter_ms / 1000.0)
                    time.sleep(max(0.005, delay_seconds + jitter))

            if simulate_real_camera:
                jitter = rng.uniform(-jitter_ms / 1000.0, jitter_ms / 1000.0)
                time.sleep(max(0.005, delay_seconds + jitter))
            else:
                time.sleep(delay_seconds)
    finally:
        cap.release()


def run_mjpeg_stream(
    video_path: str,
    host: str,
    port: int,
    path: str,
    fps: float,
    simulate_real_camera: bool,
    jitter_ms: int,
    drop_frame_probability: float,
    freeze_probability: float,
    freeze_seconds: float,
    outage_probability: float,
    outage_seconds: float,
    seed: int | None,
) -> None:
    app = FastAPI(title="Dev Movie MJPEG Stream")

    @app.get(path)
    def stream():
        return StreamingResponse(
            _build_stream_generator(
                video_path=video_path,
                fps=fps,
                simulate_real_camera=simulate_real_camera,
                jitter_ms=max(0, jitter_ms),
                drop_frame_probability=max(0.0, min(1.0, drop_frame_probability)),
                freeze_probability=max(0.0, min(1.0, freeze_probability)),
                freeze_seconds=max(0.1, freeze_seconds),
                outage_probability=max(0.0, min(1.0, outage_probability)),
                outage_seconds=max(0.1, outage_seconds),
                seed=seed,
            ),
            media_type="multipart/x-mixed-replace; boundary=frame",
        )

    print(f"Stream URL: http://{host}:{port}{path}")
    if simulate_real_camera:
        print(
            "Simulation mode ON:",
            {
                "jitter_ms": jitter_ms,
                "drop_frame_probability": drop_frame_probability,
                "freeze_probability": freeze_probability,
                "freeze_seconds": freeze_seconds,
                "outage_probability": outage_probability,
                "outage_seconds": outage_seconds,
                "seed": seed,
            },
        )
    uvicorn.run(app, host=host, port=port, log_level="info")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Dev tool for actor import + movie stream test")
    sub = parser.add_subparsers(dest="command", required=True)

    p_import = sub.add_parser("import-actors", help="Import actors from TVMaze into local faces DB")
    p_import.add_argument("--show", required=True, help="Show query for TVMaze (e.g. 'Breaking Bad')")
    p_import.add_argument("--limit", type=int, default=8)
    p_import.add_argument("--name-prefix", default="")
    p_import.add_argument("--skip-existing", action="store_true")

    p_cfg = sub.add_parser("configure-stream", help="Configure app to consume a stream URL")
    p_cfg.add_argument("--url", required=True, help="e.g. http://127.0.0.1:8090/stream.mjpg")
    p_cfg.add_argument("--mode", choices=["local", "network"], default="network")

    p_stream = sub.add_parser("stream-movie", help="Expose movie file as MJPEG stream")
    p_stream.add_argument("--video", required=True, help="Path to local movie/video file")
    p_stream.add_argument("--host", default="127.0.0.1")
    p_stream.add_argument("--port", type=int, default=8090)
    p_stream.add_argument("--path", default="/stream.mjpg")
    p_stream.add_argument("--fps", type=float, default=10.0)
    p_stream.add_argument("--simulate-real-camera", action="store_true")
    p_stream.add_argument("--jitter-ms", type=int, default=120)
    p_stream.add_argument("--drop-frame-probability", type=float, default=0.03)
    p_stream.add_argument("--freeze-probability", type=float, default=0.02)
    p_stream.add_argument("--freeze-seconds", type=float, default=0.8)
    p_stream.add_argument("--outage-probability", type=float, default=0.005)
    p_stream.add_argument("--outage-seconds", type=float, default=2.0)
    p_stream.add_argument("--seed", type=int, default=None)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "import-actors":
        import_actors(
            show_query=args.show,
            limit=max(1, min(20, args.limit)),
            name_prefix=args.name_prefix,
            skip_existing=bool(args.skip_existing),
        )
        return

    if args.command == "configure-stream":
        configure_camera_stream(stream_url=args.url, mode=args.mode)
        return

    if args.command == "stream-movie":
        run_mjpeg_stream(
            video_path=args.video,
            host=args.host,
            port=args.port,
            path=args.path,
            fps=args.fps,
            simulate_real_camera=bool(args.simulate_real_camera),
            jitter_ms=args.jitter_ms,
            drop_frame_probability=args.drop_frame_probability,
            freeze_probability=args.freeze_probability,
            freeze_seconds=args.freeze_seconds,
            outage_probability=args.outage_probability,
            outage_seconds=args.outage_seconds,
            seed=args.seed,
        )
        return

    raise SystemExit("Unknown command")


if __name__ == "__main__":
    main()

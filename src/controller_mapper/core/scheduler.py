"""スレッド管理・スケジューラ.

設計書 §9 処理周期 に対応.

Main GUI Thread    : PySide6
Worker Thread      : 入力ポーリング → 変換 → 出力
"""
from __future__ import annotations

import logging
import queue
import threading
import time

from controller_mapper.core.pipeline import Pipeline
from controller_mapper.core.state import FilteredState, InputState, OutputState
from controller_mapper.input_backends.base import InputBackend
from controller_mapper.output_backends.base import OutputBackend

logger = logging.getLogger(__name__)


class WorkerThread(threading.Thread):
    """入力ポーリング・変換・出力を行うワーカースレッド.

    設計書§9 「MVPではInput/Mapping/Outputを1スレッドにまとめてもよい」に従う.

    Args:
        input_backend:  入力バックエンド
        output_backend: 出力バックエンド
        pipeline:       変換パイプライン
        update_hz:      更新レート [Hz]
        state_queue:    GUIへの状態通知キュー (Optional)
    """

    def __init__(
        self,
        input_backend: InputBackend,
        output_backend: OutputBackend,
        pipeline: Pipeline,
        update_hz: float = 250.0,
        state_queue: "queue.Queue[tuple[InputState, FilteredState, OutputState]] | None" = None,
    ) -> None:
        super().__init__(daemon=True, name="WorkerThread")
        self._input = input_backend
        self._output = output_backend
        self._pipeline = pipeline
        self._interval = 1.0 / max(1.0, update_hz)
        self._state_queue = state_queue
        self._stop_event = threading.Event()

    def run(self) -> None:
        logger.info("WorkerThread 開始 (%.0f Hz)", 1.0 / self._interval)
        while not self._stop_event.is_set():
            t0 = time.monotonic()

            try:
                # 1. 入力取得
                raw_devices = self._input.poll()
                raw = InputState(timestamp=t0, devices=raw_devices)

                # 2. 変換
                filtered, output = self._pipeline.process(raw)

                # 3. 出力
                self._output.write(output)

                # 4. GUIキューへ通知 (ノンブロッキング)
                if self._state_queue is not None:
                    try:
                        # 古いものを捨てて最新のみ保持
                        if not self._state_queue.empty():
                            try:
                                self._state_queue.get_nowait()
                            except queue.Empty:
                                pass
                        self._state_queue.put_nowait((raw, filtered, output))
                    except queue.Full:
                        pass

            except Exception as e:
                logger.error("WorkerThread エラー: %s", e, exc_info=True)

            # 次のサイクルまで待機
            elapsed = time.monotonic() - t0
            sleep_time = self._interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

        logger.info("WorkerThread 終了")

    def stop(self) -> None:
        """スレッドを停止する."""
        self._stop_event.set()


class Scheduler:
    """WorkerThreadのライフサイクル管理.

    GUI側からの開始/停止を制御する.
    """

    def __init__(self) -> None:
        self._worker: WorkerThread | None = None
        self._state_queue: queue.Queue = queue.Queue(maxsize=2)

    @property
    def state_queue(self) -> "queue.Queue[tuple[InputState, FilteredState, OutputState]]":
        return self._state_queue

    @property
    def is_running(self) -> bool:
        return self._worker is not None and self._worker.is_alive()

    def start(
        self,
        input_backend: InputBackend,
        output_backend: OutputBackend,
        pipeline: Pipeline,
        update_hz: float = 250.0,
    ) -> None:
        """ワーカーを開始する."""
        if self.is_running:
            logger.warning("既に起動中です")
            return
        self._worker = WorkerThread(
            input_backend=input_backend,
            output_backend=output_backend,
            pipeline=pipeline,
            update_hz=update_hz,
            state_queue=self._state_queue,
        )
        self._worker.start()
        logger.info("Scheduler: ワーカー開始")

    def stop(self) -> None:
        """ワーカーを停止する."""
        if self._worker is not None:
            self._worker.stop()
            self._worker.join(timeout=2.0)
            self._worker = None
            logger.info("Scheduler: ワーカー停止")

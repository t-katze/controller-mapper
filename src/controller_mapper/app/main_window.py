"""メインウィンドウ.

設計書 §7.1 画面構成, §7.2 主要タブ に対応.
"""
from __future__ import annotations

import logging
import queue
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from controller_mapper.app.calibration_panel import CalibrationPanel
from controller_mapper.app.device_panel import DevicePanel
from controller_mapper.app.log_panel import LogPanel
from controller_mapper.app.mapping_editor import MappingEditor
from controller_mapper.app.modes_panel import ModesPanel
from controller_mapper.app.monitor_panel import MonitorPanel
from controller_mapper.app.output_panel import OutputPanel
from controller_mapper.config.loader import load_profile
from controller_mapper.core.errors import (
    InputBackendError,
    OutputBackendError,
    ProfileLoadError,
)
from controller_mapper.core.device_matching import resolve_device_aliases
from controller_mapper.core.pipeline import Pipeline
from controller_mapper.core.scheduler import Scheduler
from controller_mapper.core.state import DeviceInfo, FilteredState, InputState, OutputState
from controller_mapper.input_backends.pygame_backend import PygameBackend
from controller_mapper.output_backends.null_backend import NullBackend
from controller_mapper.output_backends.vjoy_backend import VJoyBackend

logger = logging.getLogger(__name__)


class DashboardPanel(QWidget):
    """ダッシュボードタブ."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # タイトル
        title = QLabel("🕹 Controller Mapper")
        title.setStyleSheet(
            "font-size: 28px; font-weight: bold;"
            " color: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "   stop:0 #a78bfa, stop:1 #38bdf8);"
        )
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignHCenter)

        subtitle = QLabel("フライトスティック入力補正・変換アプリ")
        subtitle.setStyleSheet("color: #64748b; font-size: 13px;")
        layout.addWidget(subtitle, alignment=Qt.AlignmentFlag.AlignHCenter)

        layout.addSpacing(20)

        # 状態カード
        self._card = QWidget()
        self._card.setStyleSheet(
            "QWidget { background: #0f172a; border-radius: 12px; border: 1px solid #1e293b; }"
        )
        card_layout = QVBoxLayout(self._card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setSpacing(10)

        self._status_label = QLabel("● 停止中")
        self._status_label.setStyleSheet("color: #ef4444; font-size: 16px; font-weight: bold;")
        card_layout.addWidget(self._status_label)

        self._device_label = QLabel("デバイス: 未検出")
        self._device_label.setStyleSheet("color: #94a3b8; font-size: 12px;")
        card_layout.addWidget(self._device_label)

        self._profile_label = QLabel("プロファイル: なし")
        self._profile_label.setStyleSheet("color: #94a3b8; font-size: 12px;")
        card_layout.addWidget(self._profile_label)

        self._output_label = QLabel("出力: Null (テストモード)")
        self._output_label.setStyleSheet("color: #94a3b8; font-size: 12px;")
        card_layout.addWidget(self._output_label)

        self._mode_label = QLabel("モード: —")
        self._mode_label.setStyleSheet("color: #94a3b8; font-size: 12px;")
        card_layout.addWidget(self._mode_label)

        layout.addWidget(self._card)

        # ボタン行
        btn_row = QHBoxLayout()
        self.btn_load_profile = QPushButton("📂 プロファイル読み込み")
        self.btn_load_profile.setStyleSheet(
            "QPushButton { background: #1e40af; color: white; border-radius: 8px;"
            " padding: 10px 24px; font-size: 13px; }"
            "QPushButton:hover { background: #2563eb; }"
        )
        btn_row.addWidget(self.btn_load_profile)

        self.btn_start = QPushButton("▶ 開始")
        self.btn_start.setStyleSheet(
            "QPushButton { background: #065f46; color: white; border-radius: 8px;"
            " padding: 10px 24px; font-size: 13px; }"
            "QPushButton:hover { background: #047857; }"
            "QPushButton:disabled { background: #374151; color: #6b7280; }"
        )
        btn_row.addWidget(self.btn_start)

        self.btn_stop = QPushButton("■ 停止")
        self.btn_stop.setStyleSheet(
            "QPushButton { background: #7f1d1d; color: white; border-radius: 8px;"
            " padding: 10px 24px; font-size: 13px; }"
            "QPushButton:hover { background: #991b1b; }"
            "QPushButton:disabled { background: #374151; color: #6b7280; }"
        )
        self.btn_stop.setEnabled(False)
        btn_row.addWidget(self.btn_stop)
        layout.addLayout(btn_row)

        layout.addStretch()

        # フッター
        footer = QLabel(
            "⚠ vJoy出力にはWindows + vJoyドライバが必要です。\n"
            "出力バックエンドは読み込んだプロファイルの output 設定に従います。"
        )
        footer.setStyleSheet("color: #78716c; font-size: 11px;")
        footer.setWordWrap(True)
        layout.addWidget(footer)

    def set_running(self, running: bool) -> None:
        if running:
            self._status_label.setText("● 動作中")
            self._status_label.setStyleSheet("color: #10b981; font-size: 16px; font-weight: bold;")
        else:
            self._status_label.setText("● 停止中")
            self._status_label.setStyleSheet("color: #ef4444; font-size: 16px; font-weight: bold;")
        self.btn_start.setEnabled(not running)
        self.btn_stop.setEnabled(running)

    def set_device_info(self, text: str) -> None:
        self._device_label.setText(f"デバイス: {text}")

    def set_profile_info(self, text: str) -> None:
        self._profile_label.setText(f"プロファイル: {text}")

    def set_output_info(self, text: str) -> None:
        self._output_label.setText(f"出力: {text}")

    def set_mode_info(self, text: str) -> None:
        self._mode_label.setText(f"モード: {text}")


class MainWindow(QMainWindow):
    """アプリのメインウィンドウ."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Controller Mapper")
        self.resize(1200, 800)

        # バックエンド
        self._input_backend = PygameBackend()
        self._output_backend = NullBackend()
        self._pipeline = Pipeline()
        self._scheduler = Scheduler()
        self._profile = None
        self._profile_path: str | None = None

        self._setup_style()
        self._setup_ui()
        self._initialize_backends()

        # GUI更新タイマー (30 Hz)
        self._gui_timer = QTimer(self)
        self._gui_timer.setInterval(33)
        self._gui_timer.timeout.connect(self._update_gui)
        self._gui_timer.start()

    def _setup_style(self) -> None:
        app = QApplication.instance()
        if app is None:
            return
        app.setStyle("Fusion")
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#0f172a"))
        palette.setColor(QPalette.ColorRole.WindowText, QColor("#e0e0e0"))
        palette.setColor(QPalette.ColorRole.Base, QColor("#1e293b"))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#0f172a"))
        palette.setColor(QPalette.ColorRole.Text, QColor("#e0e0e0"))
        palette.setColor(QPalette.ColorRole.Button, QColor("#1e293b"))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor("#e0e0e0"))
        palette.setColor(QPalette.ColorRole.Highlight, QColor("#4c1d95"))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
        app.setPalette(palette)

        font = QFont("Segoe UI", 10)
        app.setFont(font)

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # タブウィジェット
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(
            "QTabWidget::pane { border: 1px solid #1e293b; background: #0f172a; }"
            "QTabBar::tab { background: #1e293b; color: #94a3b8; padding: 8px 16px;"
            "  border-top-left-radius: 4px; border-top-right-radius: 4px; margin-right: 2px; }"
            "QTabBar::tab:selected { background: #0f172a; color: #a78bfa; font-weight: bold; }"
            "QTabBar::tab:hover { background: #263548; color: #e0e0e0; }"
        )

        # Dashboard
        self._dashboard = DashboardPanel()
        self._dashboard.btn_load_profile.clicked.connect(self._on_load_profile)
        self._dashboard.btn_start.clicked.connect(self._on_start)
        self._dashboard.btn_stop.clicked.connect(self._on_stop)
        self._tabs.addTab(self._dashboard, "🏠 Dashboard")

        # Devices
        self._device_panel = DevicePanel()
        self._device_panel.rescan_requested.connect(self._on_rescan_devices)
        self._tabs.addTab(self._device_panel, "🎮 Devices")

        # Monitor
        self._monitor_panel = MonitorPanel()
        self._tabs.addTab(self._monitor_panel, "📊 Monitor")

        # Calibration
        self._calib_panel = CalibrationPanel()
        self._calib_panel.calibration_applied.connect(self._on_calibration_applied)
        self._tabs.addTab(self._calib_panel, "🎯 Calibration")

        # Mapping
        self._mapping_editor = MappingEditor()
        self._mapping_editor.profile_changed.connect(self._on_profile_edited)
        self._tabs.addTab(self._mapping_editor, "🗺 Mapping")

        # Modes
        self._modes_panel = ModesPanel()
        self._modes_panel.mode_changed.connect(self._on_mode_changed)
        self._tabs.addTab(self._modes_panel, "🎚 Modes")

        # Output
        self._output_panel = OutputPanel()
        self._tabs.addTab(self._output_panel, "📤 Output")

        # Logs
        self._log_panel = LogPanel()
        self._tabs.addTab(self._log_panel, "📋 Logs")

        main_layout.addWidget(self._tabs)

        # ステータスバー
        self._statusbar = self.statusBar()
        self._statusbar.setStyleSheet(
            "QStatusBar { background: #0f172a; color: #64748b; font-size: 11px; }"
        )
        self._status_main = QLabel("準備完了")
        self._statusbar.addWidget(self._status_main)
        self._status_backend = QLabel("")
        self._statusbar.addPermanentWidget(self._status_backend)

    def _initialize_backends(self) -> None:
        try:
            self._input_backend.initialize()
            self._device_panel.set_backend(self._input_backend)
            devices = self._refresh_device_views("入力バックエンド初期化完了")
            logger.info("入力バックエンド初期化完了: %d デバイス", len(devices))
        except InputBackendError as e:
            logger.error("入力バックエンド初期化失敗: %s", e)
            self._status_main.setText(f"エラー: {e}")

        try:
            self._output_backend.initialize()
            self._update_output_status()
        except OutputBackendError as e:
            logger.error("出力バックエンド初期化失敗: %s", e)

    def _output_status_text(self) -> str:
        backend_name = self._output_backend.backend_name
        if backend_name == "null":
            return "Null (テストモード)"
        if backend_name == "vjoy":
            device_id = getattr(self._output_backend, "device_id", "?")
            connected = getattr(self._output_backend, "is_connected", False)
            state = "接続済み" if connected else "未接続"
            return f"vJoy Device {device_id} ({state})"
        return backend_name

    def _update_output_status(self) -> None:
        text = self._output_status_text()
        self._dashboard.set_output_info(text)
        self._output_panel.set_backend_info(text)
        self._status_backend.setText(f"出力: {text}")

    def _set_output_backend(self, backend) -> None:
        try:
            self._output_backend.shutdown()
        except Exception:
            logger.debug("既存出力バックエンドの終了で例外", exc_info=True)

        self._output_backend = backend
        self._output_backend.initialize()
        self._update_output_status()

    def _configure_output_backend_from_profile(self) -> bool:
        if self._profile is None:
            self._set_output_backend(NullBackend())
            return True

        output_type = self._profile.output.type.lower()
        device_id = self._profile.output.device_id

        try:
            if output_type == "vjoy":
                self._set_output_backend(VJoyBackend(device_id=device_id))
            elif output_type == "null":
                self._set_output_backend(NullBackend())
            else:
                raise OutputBackendError(f"未対応の出力バックエンドです: {output_type}")
            logger.info("出力バックエンド設定完了: %s", self._output_status_text())
            return True
        except OutputBackendError as e:
            logger.error("出力バックエンド設定失敗: %s", e, exc_info=True)
            try:
                self._set_output_backend(NullBackend())
            except OutputBackendError:
                logger.error("NullBackendへのフォールバックに失敗", exc_info=True)
            QMessageBox.warning(
                self,
                "出力バックエンド接続失敗",
                f"{output_type} 出力を初期化できませんでした:\n{e}\n\n"
                "NullBackend (テストモード) にフォールバックします。",
            )
            return False

    def _refresh_device_views(self, status_prefix: str | None = None) -> list[DeviceInfo]:
        """最新のデバイス一覧を、デバイス依存タブへ反映する."""
        devices = self._input_backend.get_devices()
        self._clear_state_queue()
        self._device_panel.refresh(devices)
        self._monitor_panel.setup_devices(devices)

        max_axes = max((dev.num_axes for dev in devices), default=0)
        self._calib_panel.setup_axes(max_axes)

        self._dashboard.set_device_info(f"{len(devices)} 台")
        if status_prefix is not None:
            self._status_main.setText(f"{status_prefix} ({len(devices)} デバイス)")
        return devices

    def _clear_state_queue(self) -> None:
        q = self._scheduler.state_queue
        try:
            while True:
                q.get_nowait()
        except queue.Empty:
            pass

    def _start_pipeline(self, status_text: str = "動作中...") -> None:
        hz = self._profile.global_.update_rate_hz if self._profile else 250
        self._scheduler.start(
            input_backend=self._input_backend,
            output_backend=self._output_backend,
            pipeline=self._pipeline,
            update_hz=hz,
        )
        self._dashboard.set_running(True)
        self._status_main.setText(status_text)
        logger.info("変換パイプライン開始 (%.0f Hz)", hz)

    def _on_rescan_devices(self) -> None:
        was_running = self._scheduler.is_running
        if was_running:
            self._scheduler.stop()
            self._dashboard.set_running(False)

        try:
            if isinstance(self._input_backend, PygameBackend):
                self._input_backend.rescan()
            devices = self._refresh_device_views("再スキャン完了")
            if self._profile is not None:
                self._pipeline.set_device_aliases(self._resolve_profile_device_aliases())
            logger.info("再スキャン結果を各タブへ反映: %d デバイス", len(devices))
        except Exception as e:
            logger.error("再スキャンエラー: %s", e, exc_info=True)
            self._status_main.setText(f"再スキャン失敗: {e}")
            QMessageBox.critical(self, "エラー", f"再スキャンに失敗しました:\n{e}")
            return

        if was_running:
            self._start_pipeline(f"再スキャン完了 ({len(devices)} デバイス) / 動作再開")

    def _resolve_profile_device_aliases(self) -> dict[str, str]:
        """プロファイル内の論理デバイス名をpygameの実デバイスIDへ対応付ける."""
        if self._profile is None:
            return {}
        return resolve_device_aliases(self._profile, self._input_backend.get_devices())

    def _on_load_profile(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "プロファイルを開く",
            str(Path.cwd()),
            "YAML Files (*.yaml *.yml);;All Files (*)",
        )
        if not path:
            return
        was_running = self._scheduler.is_running
        if was_running:
            self._scheduler.stop()
            self._dashboard.set_running(False)
        try:
            self._profile = load_profile(path)
            self._profile_path = path
            self._pipeline.load_profile(
                self._profile,
                device_aliases=self._resolve_profile_device_aliases(),
            )
            self._mapping_editor.load_profile(self._profile, path)
            self._configure_output_backend_from_profile()
            self._dashboard.set_profile_info(
                f"{self._profile.name} ({len(self._profile.rules)} ルール)"
            )
            # モードパネルを更新
            if self._pipeline.mode_manager is not None:
                self._modes_panel.set_mode_manager(self._pipeline.mode_manager)
                self._dashboard.set_mode_info(self._pipeline.mode_manager.current)
            self._status_main.setText(f"プロファイル読み込み完了: {self._profile.name}")
            logger.info("プロファイル読み込み: %s", path)
        except (ProfileLoadError, Exception) as e:
            logger.error("プロファイル読み込みエラー: %s", e)
            QMessageBox.critical(self, "エラー", f"プロファイル読み込みに失敗しました:\n{e}")
            return

        if was_running:
            self._start_pipeline("プロファイル読み込み完了 / 動作再開")

    def _on_start(self) -> None:
        if self._scheduler.is_running:
            return
        self._start_pipeline()

    def _on_stop(self) -> None:
        self._scheduler.stop()
        self._dashboard.set_running(False)
        self._status_main.setText("停止しました")
        logger.info("変換パイプライン停止")

    def _on_mode_changed(self, new_mode: str) -> None:
        """モードパネルからのモード変更通知を処理する."""
        self._dashboard.set_mode_info(new_mode)
        logger.info("GUIからモード変更: %s", new_mode)

    def _on_profile_edited(self) -> None:
        """マッピングエディタでプロファイルが編集された場合にパイプラインを再構築する."""
        if self._profile is None:
            return
        was_running = self._scheduler.is_running
        if was_running:
            self._scheduler.stop()
            self._dashboard.set_running(False)

        self._pipeline.load_profile(
            self._profile,
            device_aliases=self._resolve_profile_device_aliases(),
        )
        self._dashboard.set_profile_info(
            f"{self._profile.name} ({len(self._profile.rules)} ルール) [編集済]"
        )
        if self._pipeline.mode_manager is not None:
            self._modes_panel.set_mode_manager(self._pipeline.mode_manager)

        if was_running:
            self._start_pipeline("プロファイル再構築完了 / 動作再開")

        logger.info("プロファイル編集を反映: %d ルール", len(self._profile.rules))

    def _on_calibration_applied(self, values: list) -> None:
        """キャリブレーションパネルの「適用」を処理する.

        現在読み込み中のプロファイルの axis→axis ルールのフィルタ値を
        キャリブレーション値で上書きし、パイプラインを再構築する.
        """
        if self._profile is None:
            logger.warning("プロファイル未読み込みのためキャリブレーション適用をスキップ")
            return

        # 軸ルールのフィルタを更新
        from controller_mapper.app.calibration_panel import AxisCalibValues
        calib_map: dict[int, AxisCalibValues] = {v.axis_index: v for v in values}

        updated_count = 0
        for rule in self._profile.rules:
            if rule.input.type == "axis" and rule.output.type == "axis":
                cv = calib_map.get(rule.input.index)
                if cv is not None:
                    rule.filters.deadzone = cv.deadzone
                    rule.filters.end_deadzone = cv.end_deadzone
                    rule.filters.curve = cv.curve
                    rule.filters.smoothing = cv.smoothing
                    rule.filters.invert = cv.invert
                    updated_count += 1

        if updated_count > 0:
            self._on_profile_edited()
            logger.info("キャリブレーション適用: %d ルールを更新", updated_count)
        else:
            logger.info("キャリブレーション適用: 対象ルールなし")

    def _update_gui(self) -> None:
        """QTimer で 30 Hz に呼ばれる GUI更新."""
        q = self._scheduler.state_queue
        raw = filtered = output = None
        try:
            while True:
                raw, filtered, output = q.get_nowait()
        except queue.Empty:
            pass

        if raw is not None and filtered is not None and output is not None:
            self._monitor_panel.update_state(raw, filtered, output)
            self._output_panel.update_output(output)

    def closeEvent(self, event) -> None:
        self._gui_timer.stop()
        self._scheduler.stop()
        self._input_backend.shutdown()
        self._output_backend.shutdown()
        logger.info("アプリ終了")
        event.accept()

"""
ICT Trading Bot desktop launcher - ENHANCED VERSION
Larger splash (960x540), prominent logo, immaculate design
"""

import json
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

from PyQt5.QtCore import Qt, QTimer, QRectF
from PyQt5.QtGui import (
    QColor,
    QIcon,
    QPixmap,
    QPainter,
    QFont,
    QLinearGradient,
    QPen,
    QPainterPath,
)
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QMenu,
    QSplashScreen,
    QSystemTrayIcon,
)


class TradingBotLauncher:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        self.bot_process = None
        self._dashboard_wait_start = None
        self._dashboard_poll_timer = None
        self._start_error = ""
        self.repo_root = self._resolve_repo_root()
        self.bot_dir = self.repo_root / "python"
        self.config_path = self.repo_root / "config" / "settings.json"
        self.api_host, self.api_port = self._load_api_target()
        self.dashboard_url = f"http://{self.api_host}:{self.api_port}"
        self.local_dashboard_url = (
            f"http://{'127.0.0.1' if self.api_host in ('0.0.0.0', '::') else self.api_host}:{self.api_port}"
        )

        self.setup_splash_screen()
        self.setup_system_tray()

    def _resolve_repo_root(self):
        current_dir = Path(__file__).resolve().parent
        if (current_dir / "python").exists() and (current_dir / "config").exists():
            return current_dir
        return current_dir.parent

    def _load_api_target(self):
        host = "127.0.0.1"
        port = 5000
        try:
            if self.config_path.exists():
                cfg = json.loads(self.config_path.read_text(encoding="utf-8"))
                api_cfg = cfg.get("api", {})
                host = str(api_cfg.get("host", host)).strip() or host
                port = int(api_cfg.get("port", port))
        except Exception:
            host, port = "127.0.0.1", 5000
        return host, port

    def _fit_splash_pixmap(self, pixmap, available_rect):
        if pixmap.isNull() or available_rect is None:
            return pixmap

        margin = 24
        max_w = max(1, int(available_rect.width()) - (margin * 2))
        max_h = max(1, int(available_rect.height()) - (margin * 2))
        if pixmap.width() <= max_w and pixmap.height() <= max_h:
            return pixmap

        return pixmap.scaled(max_w, max_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    def _build_fallback_splash(self):
        w, h = 900, 600
        px = QPixmap(w, h)
        px.fill(QColor("#eef0f2"))

        p = QPainter(px)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.TextAntialiasing, True)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)

        bg_grad = QLinearGradient(0, 0, 0, h)
        bg_grad.setColorAt(0.0, QColor("#f6f7f8"))
        bg_grad.setColorAt(1.0, QColor("#e8ecef"))
        p.fillRect(0, 0, w, h, bg_grad)

        if not self._splash_icon_pix.isNull():
            icon_size = 220
            icon_rect = QRectF((w - icon_size) / 2, 72, icon_size, icon_size)
            p.drawPixmap(icon_rect.toRect(), self._splash_icon_pix)
        else:
            p.setPen(QColor("#173f6a"))
            p.setFont(QFont("Segoe UI Emoji", 110))
            p.drawText(QRectF(0, 72, w, 220).toRect(), Qt.AlignCenter, "🤖")

        p.setPen(QColor("#173f6a"))
        title_font = QFont("Segoe UI", 34, QFont.Black)
        title_font.setLetterSpacing(QFont.PercentageSpacing, 106)
        p.setFont(title_font)
        p.drawText(QRectF(0, 300, w, 54).toRect(), Qt.AlignCenter, "ICT TRADING BOT")

        p.setPen(QColor("#6d7781"))
        p.setFont(QFont("Segoe UI", 18, QFont.Medium))
        p.drawText(QRectF(0, 352, w, 36).toRect(), Qt.AlignCenter, "Loading...")

        p.end()
        return px

    def setup_splash_screen(self):
        """Create splash from the canonical root PNG when available."""
        self._splash_progress = 0.08
        self._splash_status_text = "Initializing..."
        self._splash_detail_text = None

        self.splash_icon_path = None
        for candidate in (
            self.repo_root / "bot icons" / "bot algo.png",
            self.repo_root / "bot_icon.png",
            self.repo_root / "icon.png",
        ):
            if candidate.exists():
                self.splash_icon_path = candidate
                break
        self._splash_icon_pix = QPixmap(str(self.splash_icon_path)) if self.splash_icon_path else QPixmap()

        screen = self.app.primaryScreen()
        available_rect = screen.availableGeometry() if screen is not None else None

        splash_image_path = self.repo_root / "splashscreen.png"
        splash_pix = QPixmap(str(splash_image_path)) if splash_image_path.exists() else QPixmap()
        if splash_pix.isNull():
            splash_pix = self._build_fallback_splash()
        else:
            splash_pix = self._fit_splash_pixmap(splash_pix, available_rect)

        self.splash_w = splash_pix.width()
        self.splash_h = splash_pix.height()

        self.splash = QSplashScreen(splash_pix)
        self.splash.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.splash.setPixmap(splash_pix)
        self.splash.setFixedSize(self.splash_w, self.splash_h)

        if screen is not None:
            rect = available_rect
            x = rect.x() + (rect.width() - self.splash_w) // 2
            y = rect.y() + (rect.height() - self.splash_h) // 2
            self.splash.move(x, y)

    def update_splash_content(self, status_text, progress=None, detail_text=None):
        """Keep startup status calls compatible without changing the static splash."""
        self._splash_status_text = str(status_text or "Loading...")
        self._splash_detail_text = detail_text
        if progress is not None:
            self._splash_progress = max(0.0, min(1.0, float(progress)))
        QApplication.processEvents()

    def setup_system_tray(self):
        """Create system tray icon"""
        self.tray = QSystemTrayIcon()

        icon_path = self.repo_root / "bot_icon.ico"
        if icon_path.exists():
            self.tray.setIcon(QIcon(str(icon_path)))
        else:
            self.tray.setIcon(self.app.style().standardIcon(
                self.app.style().SP_ComputerIcon
            ))

        self.tray.setToolTip("ICT Trading Bot")

        menu = QMenu()

        dashboard_action = QAction("📊 Open Dashboard", None)
        dashboard_action.triggered.connect(self.open_dashboard)
        menu.addAction(dashboard_action)

        menu.addSeparator()

        self.status_action = QAction("⏳ Status: Starting...", None)
        self.status_action.setEnabled(False)
        menu.addAction(self.status_action)

        menu.addSeparator()

        quit_action = QAction("❌ Quit Bot", None)
        quit_action.triggered.connect(self.quit_app)
        menu.addAction(quit_action)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self.on_tray_clicked)

    def on_tray_clicked(self, reason):
        """Handle tray icon click"""
        if reason == QSystemTrayIcon.DoubleClick:
            self.open_dashboard()

    def start_bot_process(self):
        """Start the bot in background (hidden)"""
        try:
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                creation_flags = subprocess.CREATE_NO_WINDOW
            else:
                startupinfo = None
                creation_flags = 0

            self.bot_process = subprocess.Popen(
                [sys.executable, "main.py"],
                cwd=str(self.bot_dir),
                startupinfo=startupinfo,
                creationflags=creation_flags,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            return True
        except Exception as e:
            self._start_error = str(e)
            return False

    def _is_dashboard_ready(self):
        host_to_probe = "127.0.0.1" if self.api_host in ("0.0.0.0", "::") else self.api_host
        try:
            with socket.create_connection((host_to_probe, self.api_port), timeout=1.0):
                return True
        except OSError:
            return False

    def wait_for_dashboard(self, timeout_seconds=30):
        start = time.monotonic()
        while time.monotonic() - start < timeout_seconds:
            if self.bot_process and self.bot_process.poll() is not None:
                return False
            if self._is_dashboard_ready():
                return True
            time.sleep(0.5)
        return False

    def open_dashboard(self):
        """Open dashboard in browser"""
        webbrowser.open(self.local_dashboard_url)

    def request_graceful_shutdown(self):
        """Ask API server to shutdown engine before process terminate"""
        try:
            req = urllib.request.Request(
                f"{self.local_dashboard_url}/api/shutdown",
                method="POST",
                data=b"{}",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=2):
                return True
        except (urllib.error.URLError, TimeoutError):
            return False

    def _start_stage_engine(self):
        self.update_splash_content("Booting execution environment...", progress=0.18, detail_text="Initializing runtime + config")
        QTimer.singleShot(900, self._start_stage_launch_bot)

    def _start_stage_launch_bot(self):
        self.update_splash_content("Starting trading engine...", progress=0.36, detail_text="Launching core process")
        success = self.start_bot_process()
        if not success:
            detail = f"Startup error: {self._start_error}" if self._start_error else "Startup error"
            self.update_splash_content("❌ Failed to start bot", progress=1.0, detail_text=detail)
            QTimer.singleShot(2500, self._fail_and_quit)
            return

        self.update_splash_content("Connecting to MetaTrader 5...", progress=0.52, detail_text="Preparing broker bridge")
        QTimer.singleShot(1200, self._start_stage_wait_dashboard)

    def _start_stage_wait_dashboard(self):
        self.update_splash_content("Starting dashboard server...", progress=0.68, detail_text="Waiting for API to become available")
        self._dashboard_wait_start = time.monotonic()
        self._dashboard_poll_timer = QTimer(self.app)
        self._dashboard_poll_timer.timeout.connect(self._poll_dashboard_readiness)
        self._dashboard_poll_timer.start(500)

    def _poll_dashboard_readiness(self):
        if self.bot_process and self.bot_process.poll() is not None:
            self._dashboard_poll_timer.stop()
            self._finish_startup(False)
            return

        if self._is_dashboard_ready():
            self._dashboard_poll_timer.stop()
            self._finish_startup(True)
            return

        if self._dashboard_wait_start is not None and (time.monotonic() - self._dashboard_wait_start) >= 20:
            self._dashboard_poll_timer.stop()
            self._finish_startup(False)

    def _finish_startup(self, ready):
        if ready:
            self.update_splash_content("✅ Loading dashboard...", progress=0.92, detail_text="Finalizing UI + endpoints")
            self.open_dashboard()
            QTimer.singleShot(500, self._show_running_state)
            return

        self.update_splash_content("Bot started • Dashboard warming up...", progress=0.86, detail_text="Open from tray icon when ready")
        QTimer.singleShot(1500, self._show_running_state)

    def _show_running_state(self):
        self.tray.setVisible(True)
        self.status_action.setText("✅ Status: Running")
        self.tray.showMessage(
            "ICT Trading Bot",
            "Bot is running! Double-click tray icon to open dashboard.",
            QSystemTrayIcon.Information,
            3000,
        )
        self.splash.close()

    def _fail_and_quit(self):
        self.splash.close()
        self.quit_app()

    def quit_app(self):
        """Clean shutdown"""
        if self.bot_process:
            try:
                self.request_graceful_shutdown()
                self.bot_process.wait(timeout=5)
            except Exception:
                pass

            if self.bot_process.poll() is None:
                try:
                    self.bot_process.terminate()
                    self.bot_process.wait(timeout=5)
                except Exception:
                    try:
                        self.bot_process.kill()
                    except Exception:
                        pass

        self.tray.hide()
        QApplication.quit()

    def run(self):
        """Run the launcher"""
        self.splash.show()
        QApplication.processEvents()
        QTimer.singleShot(500, self._start_stage_engine)
        sys.exit(self.app.exec_())


if __name__ == "__main__":
    launcher = TradingBotLauncher()
    launcher.run()

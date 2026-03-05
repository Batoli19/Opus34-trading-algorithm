"""
ICT Trading Bot desktop launcher.
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

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QIcon, QPalette
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QLabel,
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
        self.repo_root = Path(__file__).resolve().parent
        self.bot_dir = self.repo_root / "python"
        self.config_path = self.repo_root / "config" / "settings.json"
        self.api_host, self.api_port = self._load_api_target()
        self.dashboard_url = f"http://{self.api_host}:{self.api_port}"
        self.local_dashboard_url = (
            f"http://{'127.0.0.1' if self.api_host in ('0.0.0.0', '::') else self.api_host}:{self.api_port}"
        )

        self.setup_splash_screen()
        self.setup_system_tray()

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

    def setup_splash_screen(self):
        """Create splash screen."""
        self.splash = QSplashScreen()
        self.splash.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.splash.setFixedSize(600, 400)

        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(15, 23, 42))
        self.splash.setPalette(palette)
        self.splash.setAutoFillBackground(True)

        self.label = QLabel(self.splash)
        self.label.setGeometry(0, 0, 600, 400)
        self.label.setAlignment(Qt.AlignCenter)

        self.update_splash_content("Initializing...")

        screen = self.app.primaryScreen()
        if screen is not None:
            rect = screen.availableGeometry()
            x = rect.x() + (rect.width() - 600) // 2
            y = rect.y() + (rect.height() - 400) // 2
            self.splash.move(x, y)

    def update_splash_content(self, status_text):
        """Update splash screen content."""
        html = f"""
        <div style='text-align: center; padding: 60px;'>
            <div style='font-size: 80px; margin-bottom: 20px;'>
                BOT
            </div>
            <h1 style='color: #38bdf8; font-size: 36px; margin: 0; font-weight: bold;'>
                ICT TRADING BOT
            </h1>
            <p style='color: #94a3b8; font-size: 16px; margin-top: 15px;'>
                Professional AI Trading System
            </p>
            <div style='margin-top: 50px; padding: 20px;'>
                <p style='color: #fbbf24; font-size: 18px; font-weight: bold;'>
                    {status_text}
                </p>
            </div>
            <p style='color: #64748b; font-size: 12px; margin-top: 40px;'>
                v2.0 | Prop Firm Ready | Adaptive AI
            </p>
        </div>
        """
        self.label.setText(html)
        QApplication.processEvents()

    def setup_system_tray(self):
        """Create system tray icon."""
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

        dashboard_action = QAction("Open Dashboard", None)
        dashboard_action.triggered.connect(self.open_dashboard)
        menu.addAction(dashboard_action)

        menu.addSeparator()

        self.status_action = QAction("Status: Starting...", None)
        self.status_action.setEnabled(False)
        menu.addAction(self.status_action)

        menu.addSeparator()

        quit_action = QAction("Quit Bot", None)
        quit_action.triggered.connect(self.quit_app)
        menu.addAction(quit_action)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self.on_tray_clicked)

    def on_tray_clicked(self, reason):
        """Handle tray icon click."""
        if reason == QSystemTrayIcon.DoubleClick:
            self.open_dashboard()

    def start_bot_process(self):
        """Start the bot in background (hidden)."""
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
        """Open dashboard in browser."""
        webbrowser.open(self.local_dashboard_url)

    def request_graceful_shutdown(self):
        """Ask API server to shutdown engine before process terminate."""
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
        self.update_splash_content("Starting trading engine...")
        QTimer.singleShot(1500, self._start_stage_launch_bot)

    def _start_stage_launch_bot(self):
        success = self.start_bot_process()
        if not success:
            detail = f" ({self._start_error})" if self._start_error else ""
            self.update_splash_content(f"Failed to start bot{detail}")
            QTimer.singleShot(3000, self._fail_and_quit)
            return

        self.update_splash_content("Connecting to MT5...")
        QTimer.singleShot(2000, self._start_stage_wait_dashboard)

    def _start_stage_wait_dashboard(self):
        self.update_splash_content("Starting dashboard server...")
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
            self.update_splash_content("Loading dashboard...")
            self.open_dashboard()
            QTimer.singleShot(500, self._show_running_state)
            return

        self.update_splash_content("Bot started, dashboard not ready yet")
        QTimer.singleShot(1500, self._show_running_state)

    def _show_running_state(self):
        self.tray.setVisible(True)
        self.status_action.setText("Status: Running")
        self.tray.showMessage(
            "ICT Trading Bot",
            "Bot is running! Double-click icon to open dashboard.",
            QSystemTrayIcon.Information,
            3000,
        )
        self.splash.close()

    def _fail_and_quit(self):
        self.splash.close()
        self.quit_app()

    def quit_app(self):
        """Clean shutdown."""
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
        """Run the launcher."""
        self.splash.show()
        QApplication.processEvents()
        QTimer.singleShot(500, self._start_stage_engine)
        sys.exit(self.app.exec_())


if __name__ == "__main__":
    launcher = TradingBotLauncher()
    launcher.run()

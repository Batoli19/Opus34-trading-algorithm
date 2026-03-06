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
        """Create ENHANCED premium splash screen - MUCH LARGER"""
        # ENHANCED: 960x540 (half screen on 1920x1080)
        self.splash_w = 960
        self.splash_h = 540

        self._splash_progress = 0.08
        self._splash_target_progress = 0.08
        self._splash_status_text = "Initializing..."
        self._splash_detail_text = None
        self._splash_anim_phase = 0.0

        # Load icon - try multiple paths
        self.splash_icon_path = self.repo_root / "bot icons" / "bot algo.png"
        if not self.splash_icon_path.exists():
            self.splash_icon_path = self.repo_root / "bot_icon.png"
        if not self.splash_icon_path.exists():
            self.splash_icon_path = self.repo_root / "icon.png"
        
        self._splash_icon_pix = QPixmap(str(self.splash_icon_path)) if self.splash_icon_path.exists() else QPixmap()

        self.splash = QSplashScreen()
        self.splash.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.splash.setFixedSize(self.splash_w, self.splash_h)

        # Initial render
        self._render_splash(self._splash_status_text, progress=self._splash_progress)

        self._splash_anim_timer = QTimer(self.app)
        self._splash_anim_timer.timeout.connect(self._animate_splash)
        self._splash_anim_timer.start(33)

        # Center on screen
        screen = self.app.primaryScreen()
        if screen is not None:
            rect = screen.availableGeometry()
            x = rect.x() + (rect.width() - self.splash_w) // 2
            y = rect.y() + (rect.height() - self.splash_h) // 2
            self.splash.move(x, y)

    def update_splash_content(self, status_text, progress=None, detail_text=None):
        """Update splash with enhanced styling"""
        self._splash_status_text = str(status_text or "Loading...")
        self._splash_detail_text = detail_text

        if progress is not None:
            self._splash_target_progress = max(0.0, min(1.0, float(progress)))
        else:
            self._splash_target_progress = max(
                self._splash_target_progress,
                min(0.95, self._splash_target_progress + 0.10),
            )

        self._render_splash(
            self._splash_status_text,
            progress=self._splash_progress,
            detail_text=self._splash_detail_text,
        )
        QApplication.processEvents()

    def _animate_splash(self):
        if not hasattr(self, "splash"):
            return

        delta = self._splash_target_progress - self._splash_progress
        if abs(delta) > 0.0005:
            step = max(0.003, min(0.04, abs(delta) * 0.28))
            if delta > 0:
                self._splash_progress = min(self._splash_target_progress, self._splash_progress + step)
            else:
                self._splash_progress = max(self._splash_target_progress, self._splash_progress - step)

        self._splash_anim_phase = (self._splash_anim_phase + 0.03) % 1.0
        if self.splash.isVisible():
            self._render_splash(
                self._splash_status_text,
                progress=self._splash_progress,
                detail_text=self._splash_detail_text,
            )

    def _render_splash(self, status_text, progress=0.1, detail_text=None):
        """Render premium, high-visibility splash screen."""
        w, h = self.splash_w, self.splash_h
        px = QPixmap(w, h)
        px.setDevicePixelRatio(self.app.devicePixelRatio())
        px.fill(Qt.transparent)

        # Premium color scheme
        BG_DARK = QColor("#050b18")
        BG_MID = QColor("#0c1d33")
        BORDER = QColor(56, 189, 248, 85)
        TEXT_PRIMARY = QColor("#e5f3ff")
        TEXT_SECONDARY = QColor("#9fb7c9")
        ACCENT_CYAN = QColor("#38bdf8")
        ACCENT_BLUE = QColor("#2563eb")
        ACCENT_GOLD = QColor("#fbbf24")
        ACCENT_GREEN = QColor("#34d399")

        p = QPainter(px)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.TextAntialiasing, True)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)

        # Background gradient
        bg_grad = QLinearGradient(0, 0, w, h)
        bg_grad.setColorAt(0.0, BG_DARK)
        bg_grad.setColorAt(0.5, BG_MID)
        bg_grad.setColorAt(1.0, QColor("#071226"))
        p.fillRect(0, 0, w, h, bg_grad)

        # Main card
        panel_margin = 24
        panel_rect = QRectF(panel_margin, panel_margin, w - (panel_margin * 2), h - (panel_margin * 2))
        panel_path = QPainterPath()
        panel_path.addRoundedRect(panel_rect, 24, 24)

        panel_grad = QLinearGradient(panel_rect.left(), panel_rect.top(), panel_rect.left(), panel_rect.bottom())
        panel_grad.setColorAt(0.0, QColor(255, 255, 255, 11))
        panel_grad.setColorAt(1.0, QColor(0, 0, 0, 28))
        p.fillPath(panel_path, panel_grad)

        p.setPen(QPen(BORDER, 1.6))
        p.drawPath(panel_path)

        # Subtle cyan inner border
        inner_rect = panel_rect.adjusted(10, 10, -10, -10)
        p.setPen(QPen(QColor(56, 189, 248, 35), 1.2))
        p.drawRoundedRect(inner_rect, 18, 18)

        # Logo section (centered 120px icon)
        logo_size = 120
        logo_x = (w - logo_size) // 2
        logo_y = 62
        logo_rect = QRectF(logo_x, logo_y, logo_size, logo_size)

        # Glow layers behind badge
        for spread, alpha in ((22, 45), (34, 26), (46, 14)):
            glow_rect = logo_rect.adjusted(-spread, -spread, spread, spread)
            glow_path = QPainterPath()
            glow_path.addRoundedRect(glow_rect, 28 + spread * 0.35, 28 + spread * 0.35)
            glow_grad = QLinearGradient(glow_rect.left(), glow_rect.top(), glow_rect.right(), glow_rect.bottom())
            glow_grad.setColorAt(0.0, QColor(56, 189, 248, alpha))
            glow_grad.setColorAt(1.0, QColor(37, 99, 235, max(5, alpha - 8)))
            p.fillPath(glow_path, glow_grad)

        # Blue gradient badge around logo
        badge_path = QPainterPath()
        badge_path.addRoundedRect(logo_rect, 22, 22)
        badge_grad = QLinearGradient(logo_rect.left(), logo_rect.top(), logo_rect.right(), logo_rect.bottom())
        badge_grad.setColorAt(0.0, QColor("#1d4ed8"))
        badge_grad.setColorAt(1.0, QColor("#0ea5e9"))
        p.fillPath(badge_path, badge_grad)
        p.setPen(QPen(QColor("#7dd3fc"), 2.4))
        p.drawPath(badge_path)

        # Draw icon inside badge
        if not self._splash_icon_pix.isNull():
            icon_clip = QPainterPath()
            icon_clip.addRoundedRect(logo_rect.adjusted(10, 10, -10, -10), 16, 16)
            p.save()
            p.setClipPath(icon_clip)
            icon_target = logo_rect.adjusted(14, 14, -14, -14)
            p.drawPixmap(icon_target.toRect(), self._splash_icon_pix)
            p.restore()
        else:
            p.setPen(QColor("#dbeafe"))
            p.setFont(QFont("Segoe UI Emoji", 62))
            p.drawText(logo_rect.toRect(), Qt.AlignCenter, "🤖")

        # Title section
        title_y = int(logo_y + logo_size + 58)
        p.setPen(ACCENT_CYAN)
        title_font = QFont("Segoe UI", 48, QFont.Bold)
        title_font.setLetterSpacing(QFont.PercentageSpacing, 111)
        p.setFont(title_font)
        p.drawText(
            QRectF(0, title_y - 46, w, 56).toRect(),
            Qt.AlignHCenter | Qt.AlignVCenter,
            "ICT TRADING BOT",
        )

        # Subtitle
        p.setPen(TEXT_SECONDARY)
        sub_font = QFont("Segoe UI", 16, QFont.Medium)
        sub_font.setLetterSpacing(QFont.PercentageSpacing, 104)
        p.setFont(sub_font)
        p.drawText(
            QRectF(0, title_y + 12, w, 34).toRect(),
            Qt.AlignHCenter | Qt.AlignVCenter,
            "Professional AI Trading System",
        )

        # Status section
        status_rect = QRectF(90, 318, w - 180, 78)
        status_path = QPainterPath()
        status_path.addRoundedRect(status_rect, 16, 16)

        status_grad = QLinearGradient(status_rect.left(), status_rect.top(), status_rect.right(), status_rect.bottom())
        status_grad.setColorAt(0.0, QColor(251, 191, 36, 44))
        status_grad.setColorAt(1.0, QColor(180, 83, 9, 20))
        p.fillPath(status_path, status_grad)

        p.setPen(QPen(QColor("#fde68a"), 2.0))
        p.drawPath(status_path)

        p.setPen(TEXT_PRIMARY)
        p.setFont(QFont("Segoe UI", 20, QFont.DemiBold))
        p.drawText(
            status_rect.adjusted(24, 8, -24, -30).toRect(),
            Qt.AlignLeft | Qt.AlignVCenter,
            f"⚡ {status_text}",
        )

        # Detail text (if provided)
        if detail_text:
            p.setPen(TEXT_SECONDARY)
            p.setFont(QFont("Segoe UI", 11, QFont.Normal))
            p.drawText(
                status_rect.adjusted(24, 39, -24, -8).toRect(),
                Qt.AlignLeft | Qt.AlignVCenter,
                detail_text,
            )

        # Progress bar
        bar_rect = QRectF(90, 422, w - 180, 12)
        bar_bg_path = QPainterPath()
        bar_bg_path.addRoundedRect(bar_rect, 6, 6)
        p.fillPath(bar_bg_path, QColor(255, 255, 255, 20))
        p.setPen(QPen(QColor(255, 255, 255, 40), 1.0))
        p.drawPath(bar_bg_path)

        progress_clamped = max(0.0, min(1.0, float(progress)))
        fill_w = bar_rect.width() * progress_clamped
        if fill_w > 0:
            fill_rect = QRectF(bar_rect.left(), bar_rect.top(), fill_w, bar_rect.height())
            fill_path = QPainterPath()
            fill_path.addRoundedRect(fill_rect, 6, 6)

            phase_shift = self._splash_anim_phase * bar_rect.width()
            fill_grad = QLinearGradient(
                fill_rect.left() - phase_shift,
                fill_rect.top(),
                fill_rect.right() + (bar_rect.width() - phase_shift),
                fill_rect.top(),
            )
            fill_grad.setColorAt(0.0, ACCENT_BLUE)
            fill_grad.setColorAt(0.5, ACCENT_CYAN)
            fill_grad.setColorAt(1.0, QColor("#22d3ee"))
            p.fillPath(fill_path, fill_grad)

        p.setPen(QColor(191, 219, 254))
        p.setFont(QFont("Segoe UI", 11, QFont.DemiBold))
        p.drawText(
            QRectF(90, 438, w - 180, 24).toRect(),
            Qt.AlignRight | Qt.AlignVCenter,
            f"{int(round(progress_clamped * 100)):02d}%",
        )

        # Feature badges
        badges = [
            "Prop Firm Ready",
            "Adaptive Learning",
            "MT5 Connected",
            "Risk Controls",
        ]
        badge_y = 462
        badge_h = 34
        badge_w = 186
        badge_gap = 12
        badges_total_w = (badge_w * len(badges)) + (badge_gap * (len(badges) - 1))
        badge_x = int((w - badges_total_w) / 2)

        p.setFont(QFont("Segoe UI", 11, QFont.Medium))
        for i, label in enumerate(badges):
            rect = QRectF(badge_x + i * (badge_w + badge_gap), badge_y, badge_w, badge_h)
            badge_path = QPainterPath()
            badge_path.addRoundedRect(rect, 12, 12)
            p.fillPath(badge_path, QColor(16, 185, 129, 28))
            p.setPen(QPen(QColor(52, 211, 153, 150), 1.2))
            p.drawPath(badge_path)
            p.setPen(ACCENT_GREEN)
            p.drawText(rect.toRect(), Qt.AlignCenter, f"✓ {label}")

        # Footer
        p.setPen(QColor(255, 255, 255, 132))
        p.setFont(QFont("Segoe UI", 11, QFont.Medium))
        p.drawText(
            QRectF(0, h - 44, w, 24).toRect(),
            Qt.AlignHCenter | Qt.AlignVCenter,
            "v2.0 • Institutional Grade",
        )

        p.end()
        self.splash.setPixmap(px)

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
        if hasattr(self, "_splash_anim_timer"):
            self._splash_anim_timer.stop()
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
        if hasattr(self, "_splash_anim_timer"):
            self._splash_anim_timer.stop()
        self.splash.close()
        self.quit_app()

    def quit_app(self):
        """Clean shutdown"""
        if hasattr(self, "_splash_anim_timer"):
            self._splash_anim_timer.stop()
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

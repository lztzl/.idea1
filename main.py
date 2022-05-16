# coding:utf-8
from copy import deepcopy
from pathlib import Path
from random import shuffle
from typing import List

from common import resource
from common.crawler import CrawlerBase
from common.database import DBInitializer
from common.database.entity import AlbumInfo, Playlist, SongInfo
from common.library import Library
from common.os_utils import moveToTrash
from common.signal_bus import signalBus
from common.thread.get_online_song_url_thread import GetOnlineSongUrlThread
from common.thread.library_thread import LibraryThread
from components.dialog_box.create_playlist_dialog import CreatePlaylistDialog
from components.dialog_box.message_dialog import MessageDialog
from components.frameless_window import FramelessWindow
from components.label_navigation_interface import LabelNavigationInterface
from components.media_player import MediaPlaylist, PlaylistType
from components.system_tray_icon import SystemTrayIcon
from components.thumbnail_tool_bar import ThumbnailToolBar
from components.title_bar import TitleBar
from components.video_window import VideoWindow
from components.widgets.stacked_widget import (OpacityAniStackedWidget,
                                               PopUpAniStackedWidget)
from components.widgets.state_tooltip import StateTooltip
from PyQt5.QtCore import QEasingCurve, QEvent, QEventLoop, QFile, Qt, QTimer
from PyQt5.QtGui import QColor, QIcon, QPixmap
from PyQt5.QtMultimedia import QMediaPlayer, QMediaPlaylist
from PyQt5.QtWidgets import (QAction, QApplication, QHBoxLayout, QLabel,
                             QWidget, qApp)
from PyQt5.QtWinExtras import QtWin
from View.album_interface import AlbumInterface
from View.more_search_result_interface import MoreSearchResultInterface
from View.my_music_interface import MyMusicInterface
from View.navigation_interface import NavigationInterface
from View.play_bar import PlayBar
from View.playing_interface import PlayingInterface
from View.playlist_card_interface import PlaylistCardInterface
from View.playlist_interface import PlaylistInterface
from View.search_result_interface import SearchResultInterface
from View.setting_interface import SettingInterface
from View.singer_interface import SingerInterface
from View.smallest_play_interface import SmallestPlayInterface


class MainWindow(FramelessWindow):
    """ Main window """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.isInSelectionMode = False
        self.navigationHistories = [("myMusicInterfaceStackWidget", 0)]
        self.setObjectName("mainWindow")
        self.initDatabase()
        self.createWidgets()
        self.initWidget()

    def initDatabase(self):
        """ initialize database """
        initializer = DBInitializer()
        initializer.init()
        self.db = initializer.db

    def createWidgets(self):
        """ create widgets """
        # main window contains totalStackWidget, playBar and titleBar
        # totalStackWidget contanins subMainWindow, playingInterface and videoWindow
        self.totalStackWidget = OpacityAniStackedWidget(self)

        # subMainWindow is used to put navigation interface and subStackWidget
        self.subMainWindow = QWidget(self)

        # create splash screen
        self.splashScreen = SplashScreen(self)

        # create title bar
        self.titleBar = TitleBar(self)

        # display the window on the desktop first
        self.initWindow()

        # subStackWidget contains myMusicInterface, albumInterface and other interface
        # that need to be displayed on the right side of navigationInterface
        self.subStackWidget = PopUpAniStackedWidget(self.subMainWindow)

        # get online music url thread
        self.getOnlineSongUrlThread = GetOnlineSongUrlThread(self)

        # create setting interface
        self.settingInterface = SettingInterface(self.subMainWindow)

        # create song library
        self.initLibrary()

        # create player and playlist
        self.player = QMediaPlayer(self)
        self.mediaPlaylist = MediaPlaylist(self.library, self)

        # create my music interface
        self.myMusicInterface = MyMusicInterface(
            self.library, self.subMainWindow)

        # create timer to update the position of lyrics
        self.updateLyricPosTimer = QTimer(self)

        # crete thumbnail bar
        self.thumbnailToolBar = ThumbnailToolBar(self)
        self.thumbnailToolBar.setWindow(self.windowHandle())

        # create play bar
        color = self.settingInterface.config['playBar-color']
        self.playBar = PlayBar(
            self.mediaPlaylist.lastSongInfo, QColor(*color), self)

        # create playing interface
        self.playingInterface = PlayingInterface(
            self.mediaPlaylist.playlist, self)

        # create video interface
        self.videoWindow = VideoWindow(self)

        # create album interface
        self.albumInterface = AlbumInterface(
            self.library, parent=self.subMainWindow)

        # create singer interface
        self.singerInterface = SingerInterface(
            self.library, parent=self.subMainWindow)

        # create playlist card interface and playlist interface
        self.playlistCardInterface = PlaylistCardInterface(
            self.library, self.subMainWindow)
        self.playlistInterface = PlaylistInterface(self.library, parent=self)

        # create navigation interface
        self.navigationInterface = NavigationInterface(self.subMainWindow)

        # create label navigation interface
        self.labelNavigationInterface = LabelNavigationInterface(
            self.subMainWindow)

        # create smallest play interface
        self.smallestPlayInterface = SmallestPlayInterface(
            self.mediaPlaylist.playlist, parent=self)

        # create system tray icon
        self.systemTrayIcon = SystemTrayIcon(self)

        # create search result interface
        pageSize = self.settingInterface.config['online-music-page-size']
        quality = self.settingInterface.config['online-play-quality']
        folder = self.settingInterface.config['download-folder']
        self.searchResultInterface = SearchResultInterface(
            self.library, pageSize, quality, folder, self.subMainWindow)

        # create more search result interface
        self.moreSearchResultInterface = MoreSearchResultInterface(
            self.library, self.subMainWindow)

        # create state tooltip
        self.scanInfoTooltip = None

        # create hot keys
        self.togglePlayPauseAct_1 = QAction(
            parent=self, shortcut=Qt.Key_Space, triggered=self.togglePlayState)
        self.showNormalAct = QAction(
            parent=self, shortcut=Qt.Key_Escape, triggered=self.exitFullScreen)
        self.lastSongAct = QAction(
            parent=self, shortcut=Qt.Key_MediaPrevious, triggered=self.mediaPlaylist.previous)
        self.nextSongAct = QAction(
            parent=self, shortcut=Qt.Key_MediaNext, triggered=self.mediaPlaylist.next)
        self.togglePlayPauseAct_2 = QAction(
            parent=self, shortcut=Qt.Key_MediaPlay, triggered=self.togglePlayState)
        self.addActions([
            self.togglePlayPauseAct_1,
            self.showNormalAct,
            self.nextSongAct,
            self.lastSongAct,
            self.togglePlayPauseAct_2,
        ])

        self.songTabSongListWidget = self.myMusicInterface.songListWidget

    def initLibrary(self):
        """ initialize song library """
        self.library = Library(
            self.settingInterface.config["selected-folders"], self.db)
        self.libraryThread = LibraryThread(
            self.settingInterface.config["selected-folders"], self)

        eventLoop = QEventLoop(self)
        self.libraryThread.finished.connect(eventLoop.quit)
        self.libraryThread.start()
        eventLoop.exec()

        self.library.songInfos = self.libraryThread.library.songInfos
        self.library.albumInfos = self.libraryThread.library.albumInfos
        self.library.singerInfos = self.libraryThread.library.singerInfos
        self.library.playlists = self.libraryThread.library.playlists

    def initWindow(self):
        """ initialize window """
        self.resize(1240, 970)
        self.setWindowTitle(self.tr("Groove Music"))
        self.setWindowIcon(QIcon(":/images/logo/logo_small.png"))

        QtWin.enableBlurBehindWindow(self)
        self.setWindowFlags(Qt.FramelessWindowHint |
                            Qt.WindowMinMaxButtonsHint)
        self.windowEffect.addWindowAnimation(self.winId())
        desktop = QApplication.desktop().availableGeometry()
        self.move(desktop.width() // 2 - self.width() // 2,
                  desktop.height() // 2 - self.height() // 2)
        self.show()
        QApplication.processEvents()

    def initWidget(self):
        """ initialize widgets """
        self.resize(1240, 970)
        self.setMinimumSize(1030, 800)
        self.videoWindow.hide()

        QApplication.setQuitOnLastWindowClosed(
            not self.settingInterface.config['minimize-to-tray'])

        desktop = QApplication.desktop().availableGeometry()
        self.smallestPlayInterface.move(desktop.width() - 390, 40)

        self.titleBar.raise_()

        # add sub interface to stacked Widget
        self.subStackWidget.addWidget(self.myMusicInterface, 0, 70)
        self.subStackWidget.addWidget(self.playlistCardInterface, 0, 120)
        self.subStackWidget.addWidget(self.settingInterface, 0, 120)
        self.subStackWidget.addWidget(self.albumInterface, 0, 70)
        self.subStackWidget.addWidget(self.singerInterface, 0, 70)
        self.subStackWidget.addWidget(self.playlistInterface, 0, 70)
        self.subStackWidget.addWidget(self.labelNavigationInterface, 0, 100)
        self.subStackWidget.addWidget(self.searchResultInterface, 0, 120)
        self.subStackWidget.addWidget(self.moreSearchResultInterface, 0, 120)
        self.totalStackWidget.addWidget(self.subMainWindow)
        self.totalStackWidget.addWidget(self.playingInterface)
        self.totalStackWidget.addWidget(self.videoWindow)
        self.subMainWindow.setGraphicsEffect(None)

        self.adjustWidgetGeometry()
        self.setQss()

        # Set the interval that the player sends update position signal
        self.player.setNotifyInterval(1000)

        self.updateLyricPosTimer.setInterval(200)

        # set MV quality
        self.playingInterface.getMvUrlThread.setVideoQuality(
            self.settingInterface.config['mv-quality'])

        self.initPlaylist()
        self.connectSignalToSlot()
        self.initPlayBar()

        self.setPlayButtonEnabled(self.songTabSongListWidget.songCardNum() > 0)

        self.navigationInterface.navigationMenu.installEventFilter(self)
        self.updateLyricPosTimer.start()
        self.onInitFinished()

    def onInitFinished(self):
        """ initialize finished slot """
        self.splashScreen.hide()
        self.subStackWidget.show()
        self.navigationInterface.show()
        self.playBar.show()
        self.systemTrayIcon.show()
        self.setWindowEffect(
            self.settingInterface.config["enable-acrylic-background"])

    def setWindowEffect(self, isEnableAcrylic: bool):
        """ set window effect """
        if isEnableAcrylic:
            self.windowEffect.setAcrylicEffect(self.winId(), "F2F2F299", True)
            self.setStyleSheet("#mainWindow{background:transparent}")
        else:
            self.setStyleSheet("#mainWindow{background:#F2F2F2}")
            self.windowEffect.addShadowEffect(self.winId())
            self.windowEffect.removeBackgroundEffect(self.winId())

    def adjustWidgetGeometry(self):
        """ adjust the geometry of widgets """
        self.titleBar.resize(self.width(), 40)
        self.splashScreen.resize(self.size())

        if not hasattr(self, 'playBar'):
            return

        self.subMainWindow.resize(self.size())
        self.totalStackWidget.resize(self.size())
        self.playBar.resize(self.width(), self.playBar.height())
        self.playBar.move(0, self.height() - self.playBar.height())

        if not hasattr(self, "navigationInterface"):
            return

        self.navigationInterface.setOverlay(self.width() < 1280)
        self.subStackWidget.move(self.navigationInterface.width(), 0)
        self.subStackWidget.resize(
            self.width() - self.navigationInterface.width(), self.height())
        self.navigationInterface.resize(
            self.navigationInterface.width(), self.height())

    def setQss(self):
        """ set style sheet """
        self.setObjectName("mainWindow")
        self.subMainWindow.setObjectName("subMainWindow")
        self.subStackWidget.setObjectName("subStackWidget")
        self.playingInterface.setObjectName("playingInterface")

        f = QFile(":/qss/main_window.qss")
        f.open(QFile.ReadOnly)
        self.setStyleSheet(str(f.readAll(), encoding='utf-8'))
        f.close()

    def eventFilter(self, obj, e: QEvent):
        if obj == self.navigationInterface.navigationMenu:
            # 显示导航菜单是更改标题栏返回按钮和标题的父级为导航菜单
            isVisible = self.titleBar.returnButton.isVisible()

            if e.type() == QEvent.Show:
                self.titleBar.returnButton.setParent(obj)

                # show title
                self.titleBar.title.setParent(obj)
                self.titleBar.title.move(15, 10)
                self.titleBar.title.show()

                # shorten the navigation menu if the play bar is visible
                isScaled = self.playBar.isVisible()
                height = self.height() - isScaled * self.playBar.height()
                self.navigationInterface.navigationMenu.setBottomSpacingVisible(
                    not isScaled)
                self.navigationInterface.navigationMenu.resize(
                    self.navigationInterface.navigationMenu.width(), height)
            elif e.type() == QEvent.Hide:
                # hide title
                self.titleBar.title.setParent(self.titleBar)
                self.titleBar.returnButton.setParent(self.titleBar)
                self.titleBar.title.hide()

            self.titleBar.returnButton.setVisible(isVisible)

        return super().eventFilter(obj, e)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.adjustWidgetGeometry()
        self.titleBar.maxButton.setMaxState(
            self._isWindowMaximized(int(self.winId())))

    def showEvent(self, e):
        if hasattr(self, 'smallestPlayInterface'):
            self.smallestPlayInterface.hide()

        super().showEvent(e)

    def initPlaylist(self):
        """ initialize playlist """
        self.player.setPlaylist(self.mediaPlaylist)

        if not self.mediaPlaylist.playlist:
            songInfos = self.songTabSongListWidget.songInfos
            self.setPlaylist(songInfos)
            self.mediaPlaylist.playlistType = PlaylistType.ALL_SONG_PLAYLIST
            self.songTabSongListWidget.setPlay(0)
            if songInfos:
                self.systemTrayIcon.updateWindow(songInfos[0])

        if self.mediaPlaylist.lastSongInfo in self.mediaPlaylist.playlist:
            index = self.mediaPlaylist.playlist.index(
                self.mediaPlaylist.lastSongInfo)
            self.mediaPlaylist.setCurrentIndex(index)
            self.playingInterface.setCurrentIndex(index)
            self.smallestPlayInterface.setCurrentIndex(index)
            self.systemTrayIcon.updateWindow(self.mediaPlaylist.lastSongInfo)

            index = self.songTabSongListWidget.index(
                self.mediaPlaylist.lastSongInfo)
            if index is not None:
                self.songTabSongListWidget.setPlay(index)

    def initPlayBar(self):
        """ initialize play bar """
        volume = self.settingInterface.config["volume"]
        self.playBar.setVolume(volume)

        if self.mediaPlaylist.playlist:
            self.playBar.updateWindow(self.mediaPlaylist.getCurrentSong())
            self.playBar.songInfoCard.albumCoverLabel.setOpacity(1)

    def setFullScreen(self, isFullScreen: bool):
        """ set full screen """
        if isFullScreen == self.isFullScreen():
            return

        if not isFullScreen:
            self.exitFullScreen()
            return

        # update title bar
        self.playBar.hide()
        self.titleBar.title.hide()
        self.titleBar.setWhiteIcon(True)
        self.titleBar.hide()

        # switch to playing interface
        self.totalStackWidget.setCurrentIndex(1)
        self.navigationHistories.append(("totalStackWidget", 1))

        self.showFullScreen()
        self.videoWindow.playBar.fullScreenButton.setFullScreen(True)
        self.videoWindow.playBar.fullScreenButton.setToolTip(
            self.tr('Exit fullscreen'))
        self.playingInterface.setFullScreen(True)
        if self.playingInterface.isPlaylistVisible:
            self.playingInterface.songInfoCardChute.move(
                0, 258 - self.height())

    def setVideoFullScreen(self, isFullScreen: bool):
        """ set video interface full screen """
        self.titleBar.setVisible(not isFullScreen)
        self.titleBar.maxButton.setMaxState(isFullScreen)
        self.titleBar.returnButton.show()
        if isFullScreen:
            self.showFullScreen()
        else:
            self.showNormal()

    def setMute(self, isMute: bool):
        """ set whether to mute """
        self.player.setMuted(isMute)
        self.playBar.setMute(isMute)
        self.playingInterface.setMute(isMute)

    def onVolumeChanged(self, volume: int):
        """ volume changed slot """
        self.player.setVolume(volume)
        self.playBar.setVolume(volume)
        self.playingInterface.setVolume(volume)

    def setRandomPlay(self, isRandomPlay: bool):
        """ set whether to play randomly """
        self.mediaPlaylist.setRandomPlay(isRandomPlay)
        self.playingInterface.setRandomPlay(isRandomPlay)
        self.playBar.randomPlayButton.setRandomPlay(isRandomPlay)

    def play(self):
        """ play songs """
        if not self.mediaPlaylist.playlist:
            self.playBar.songInfoCard.hide()
            self.setPlayButtonState(False)
            self.setPlayButtonEnabled(False)
            self.playBar.setTotalTime(0)
            self.playBar.progressSlider.setRange(0, 0)
        else:
            self.player.play()
            self.setPlayButtonState(True)
            self.playBar.songInfoCard.show()

    def setPlaylist(self, playlist: list, index=0):
        """ set playing playlist """
        self.playingInterface.setPlaylist(playlist, index=index)
        self.smallestPlayInterface.setPlaylist(playlist)
        self.mediaPlaylist.setPlaylist(playlist, index)
        self.play()

    def setPlayButtonEnabled(self, isEnabled: bool):
        """ set the enabled state of play buttons """
        self.playBar.playButton.setEnabled(isEnabled)
        self.playBar.nextSongButton.setEnabled(isEnabled)
        self.playBar.lastSongButton.setEnabled(isEnabled)
        self.playingInterface.playBar.playButton.setEnabled(isEnabled)
        self.playingInterface.playBar.nextSongButton.setEnabled(isEnabled)
        self.playingInterface.playBar.lastSongButton.setEnabled(isEnabled)
        self.thumbnailToolBar.playButton.setEnabled(isEnabled)
        self.thumbnailToolBar.nextSongButton.setEnabled(isEnabled)
        self.thumbnailToolBar.lastSongButton.setEnabled(isEnabled)
        self.smallestPlayInterface.playButton.setEnabled(isEnabled)
        self.smallestPlayInterface.lastSongButton.setEnabled(isEnabled)
        self.smallestPlayInterface.nextSongButton.setEnabled(isEnabled)
        self.systemTrayIcon.menu.songAct.setEnabled(isEnabled)
        self.systemTrayIcon.menu.playAct.setEnabled(isEnabled)
        self.systemTrayIcon.menu.lastSongAct.setEnabled(isEnabled)
        self.systemTrayIcon.menu.nextSongAct.setEnabled(isEnabled)

    def setPlayButtonState(self, isPlay: bool):
        """ set the play state of play buttons """
        self.playBar.setPlay(isPlay)
        self.systemTrayIcon.setPlay(isPlay)
        self.playingInterface.setPlay(isPlay)
        self.thumbnailToolBar.setPlay(isPlay)
        self.smallestPlayInterface.setPlay(isPlay)

    def togglePlayState(self):
        """ toggle play state """
        if self.totalStackWidget.currentWidget() is self.videoWindow:
            self.videoWindow.togglePlayState()
            return

        if self.player.state() == QMediaPlayer.PlayingState:
            self.player.pause()
            self.setPlayButtonState(False)
            self.thumbnailToolBar.setButtonsEnabled(True)
        else:
            self.play()

    def onPlayerPositionChanged(self, position):
        """ player position changed slot """
        self.playBar.setCurrentTime(position)
        self.playBar.progressSlider.setValue(position)
        self.playingInterface.setCurrentTime(position)
        self.playingInterface.playBar.progressSlider.setValue(position)
        self.smallestPlayInterface.progressBar.setValue(position)

    def onPlayerDurationChanged(self):
        """ player duration changed slot """
        # the duration is 0 when just switching songs
        duration = self.player.duration()
        if duration < 1:
            return

        self.playBar.setTotalTime(duration)
        self.playBar.progressSlider.setRange(0, duration)
        self.playingInterface.playBar.setTotalTime(duration)
        self.playingInterface.playBar.progressSlider.setRange(0, duration)
        self.smallestPlayInterface.progressBar.setRange(0, duration)

    def onMediaStatusChanged(self, status: QMediaPlayer.MediaStatus):
        """ media status changed slot """
        if status != QMediaPlayer.NoMedia:
            return

        self.setPlayButtonState(False)

    def onProgressSliderMoved(self, position):
        """ progress slider moved slot """
        self.player.setPosition(position)
        self.playBar.setCurrentTime(position)
        self.playingInterface.setCurrentTime(position)
        self.smallestPlayInterface.progressBar.setValue(position)

    def switchLoopMode(self, loopMode):
        """ switch loop mode of player """
        self.mediaPlaylist.prePlayMode = loopMode

        self.playBar.setLoopMode(loopMode)
        self.playingInterface.setLoopMode(loopMode)

        if not self.mediaPlaylist.randPlayBtPressed:
            self.mediaPlaylist.setPlaybackMode(loopMode)
        else:
            if self.playBar.loopModeButton.loopMode == QMediaPlaylist.CurrentItemInLoop:
                self.mediaPlaylist.setPlaybackMode(
                    QMediaPlaylist.CurrentItemInLoop)
            else:
                self.mediaPlaylist.setPlaybackMode(QMediaPlaylist.Random)

    def getOnlineSongUrl(self, index: int):
        """ get the play url of online music """
        if index < 0 or not self.mediaPlaylist.playlist:
            return

        songInfo = self.mediaPlaylist.playlist[index]
        if songInfo.file != CrawlerBase.song_url_mark:
            return

        i = self.searchResultInterface.onlineSongInfos.index(songInfo)
        songCard = self.searchResultInterface.onlineSongListWidget.songCards[i]

        # get play url and cover
        eventLoop = QEventLoop(self)
        self.getOnlineSongUrlThread.finished.connect(eventLoop.quit)
        self.getOnlineSongUrlThread.setSongInfo(
            songInfo, self.settingInterface.config['online-play-quality'])
        self.getOnlineSongUrlThread.start()
        eventLoop.exec()

        # TODO：更优雅地更新在线媒体
        songInfo.file = self.getOnlineSongUrlThread.playUrl
        songInfo['coverPath'] = self.getOnlineSongUrlThread.coverPath
        songCard.setSongInfo(songInfo)
        self.mediaPlaylist.insertSong(index, songInfo)
        self.playingInterface.playlist[index] = songInfo
        self.smallestPlayInterface.playlist[index] = songInfo
        self.searchResultInterface.onlineSongInfos[i] = songInfo
        self.mediaPlaylist.removeOnlineSong(index + 1)
        self.mediaPlaylist.setCurrentIndex(index)

    def updateWindow(self, index: int):
        """ update main window after switching songs """
        if not self.mediaPlaylist.playlist:
            self.playBar.songInfoCard.hide()
            self.setPlayButtonState(False)
            self.setPlayButtonEnabled(False)
            return

        self.setPlayButtonEnabled(True)

        # handling the situation that song does not exist
        if index < 0:
            return

        songInfo = self.mediaPlaylist.playlist[index]

        # update sub interfaces
        self.playBar.updateWindow(songInfo)
        self.playingInterface.setCurrentIndex(index)
        self.systemTrayIcon.updateWindow(songInfo)

        if self.smallestPlayInterface.isVisible():
            self.smallestPlayInterface.setCurrentIndex(index)

        signalBus.playBySongInfoSig.emit(songInfo)

        self.checkMediaAvailable()

    def checkMediaAvailable(self):
        """ check the availability of media """
        if not self.mediaPlaylist.playlist:
            return

        # determin the availability
        songPath = self.mediaPlaylist.getCurrentSong().file
        if songPath.startswith('http') or Path(songPath).exists():
            return

        # pause player when the media is not available
        self.player.pause()
        self.setPlayButtonState(False)

        # pop up message dialog
        w = MessageDialog(self.tr("Can't play this song"), self.tr(
            "It's not on this device or somewhere we can stream from."), self)
        w.cancelButton.setText(self.tr('Close'))
        w.yesButton.hide()
        w.exec()

    def onMinimizeToTrayChanged(self, isMinimize: bool):
        """ minimize to tray slot """
        QApplication.setQuitOnLastWindowClosed(not isMinimize)

    def onReturnButtonClicked(self):
        """ return button clicked slot """
        if self.isInSelectionMode:
            return

        self.playingInterface.playBar.volumeSliderWidget.hide()

        history = self.navigationHistories.pop()
        if history == ("totalStackWidget", 2):
            self.videoWindow.pause()
            self.totalStackWidget.setCurrentIndex(1)
            return

        # should not return to the playingInterface
        if self.navigationHistories[-1] == ("totalStackWidget", 1):
            self.navigationHistories.pop()

        stackWidget, index = self.navigationHistories[-1]
        if stackWidget == "myMusicInterfaceStackWidget":
            self.myMusicInterface.stackedWidget.setCurrentIndex(index)
            self.subStackWidget.setCurrentIndex(
                0, True, False, 200, QEasingCurve.InCubic)
            self.navigationInterface.setCurrentIndex(0)
            self.myMusicInterface.setSelectedButton(index)
            self.titleBar.setWhiteIcon(False)
        elif stackWidget == "subStackWidget":
            isShowNextWidgetDirectly = self.subStackWidget.currentWidget() is not self.settingInterface
            self.subStackWidget.setCurrentIndex(
                index, True, isShowNextWidgetDirectly, 200, QEasingCurve.InCubic)
            self.navigationInterface.setCurrentIndex(index)

            # update icon color of title bar
            whiteIndexes = [self.subStackWidget.indexOf(
                i) for i in [self.albumInterface, self.playlistInterface, self.singerInterface]]
            self.titleBar.setWhiteIcon(index in whiteIndexes)
            self.titleBar.returnButton.setWhiteIcon(False)

        self.hidePlayingInterface()

        if len(self.navigationHistories) == 1:
            self.titleBar.returnButton.hide()

    def showLabelNavigationInterface(self, labels: list, layout: str):
        """ show label navigation interface """
        self.labelNavigationInterface.setLabels(labels, layout)
        self.switchToSubInterface(self.labelNavigationInterface)

    def showSmallestPlayInterface(self):
        """ show smallest play interface """
        self.smallestPlayInterface.setCurrentIndex(
            self.mediaPlaylist.currentIndex())
        self.hide()
        self.smallestPlayInterface.show()

    def showVideoWindow(self, url: str):
        """ show video window """
        self.player.pause()
        self.setPlayButtonState(False)

        songInfo = self.mediaPlaylist.getCurrentSong()
        self.videoWindow.setVideo(url, songInfo.singer + ' - ' + songInfo.title)
        self.totalStackWidget.setCurrentIndex(2)

        self.navigationHistories.append(("totalStackWidget", 2))
        self.titleBar.returnButton.show()

    def exitSmallestPlayInterface(self):
        """ exit smallest play interface """
        self.smallestPlayInterface.hide()
        self.show()

    def hidePlayingInterface(self):
        """ hide playing interface """
        if not self.playingInterface.isVisible():
            return

        self.playBar.show()
        self.totalStackWidget.setCurrentIndex(0)

        # set the icon color of title bar
        whiteInterface = [self.albumInterface,
                          self.playlistInterface, self.singerInterface]
        if self.subStackWidget.currentWidget() in whiteInterface:
            self.titleBar.returnButton.setWhiteIcon(False)
        else:
            self.titleBar.setWhiteIcon(False)

        # hide return button
        cond = self.subStackWidget.currentWidget() not in [
            self.labelNavigationInterface, self.albumInterface]
        if len(self.navigationHistories) == 1 and cond:
            self.titleBar.returnButton.hide()

        self.titleBar.title.setVisible(self.navigationInterface.isExpanded)

    def showPlayingInterface(self):
        """ show playing interface """
        self.show()

        if self.playingInterface.isVisible():
            return

        self.exitSelectionMode()
        self.playBar.hide()
        self.titleBar.title.hide()
        self.titleBar.returnButton.show()

        if not self.playingInterface.isPlaylistVisible and len(self.playingInterface.playlist) > 0:
            self.playingInterface.songInfoCardChute.move(
                0, -self.playingInterface.playBar.height() + 68)
            self.playingInterface.playBar.show()

        self.totalStackWidget.setCurrentIndex(1)
        self.titleBar.setWhiteIcon(True)

        self.navigationHistories.append(("totalStackWidget", 1))

    def showPlayingPlaylist(self):
        """ show playing playlist """
        self.playingInterface.showPlaylist()
        self.playingInterface.playBar.pullUpArrowButton.setArrowDirection(
            "down")
        if self.playingInterface.isPlaylistVisible:
            self.showPlayingInterface()

    def clearPlaylist(self):
        """ clear playlist """
        self.mediaPlaylist.playlistType = PlaylistType.NO_PLAYLIST
        self.mediaPlaylist.clear()
        self.playingInterface.clearPlaylist()
        self.smallestPlayInterface.clearPlaylist()
        self.playBar.songInfoCard.hide()
        self.setPlayButtonState(False)
        self.setPlayButtonEnabled(False)

        self.songTabSongListWidget.cancelPlayState()
        self.albumInterface.songListWidget.cancelPlayState()
        self.playlistInterface.songListWidget.cancelPlayState()
        self.searchResultInterface.localSongListWidget.cancelPlayState()
        self.searchResultInterface.onlineSongListWidget.cancelPlayState()

        self.playBar.setTotalTime(0)
        self.playBar.progressSlider.setRange(0, 0)

    def onNavigationDisplayModeChanged(self, disPlayMode: int):
        """ navigation interface display mode changed slot """
        self.titleBar.title.setVisible(self.navigationInterface.isExpanded)
        self.adjustWidgetGeometry()
        self.navigationInterface.navigationMenu.stackUnder(self.playBar)
        # 如果现在显示的是字母导航界面就将其隐藏
        if self.subStackWidget.currentWidget() is self.labelNavigationInterface:
            self.subStackWidget.setCurrentIndex(0)

    def onSelectionModeStateChanged(self, isOpen: bool):
        """ selection mode state changed slot """
        self.isInSelectionMode = isOpen
        if not self.playingInterface.isVisible():
            self.playBar.setHidden(isOpen)

    def exitSelectionMode(self):
        """ exit selection mode """
        if not self.isInSelectionMode:
            return

        self.myMusicInterface.exitSelectionMode()
        self.albumInterface.exitSelectionMode()
        self.playlistCardInterface.exitSelectionMode()
        self.playlistInterface.exitSelectionMode()
        self.playingInterface.exitSelectionMode()
        self.singerInterface.exitSelectionMode()

    def exitFullScreen(self):
        """ exit full screen """
        if not self.isFullScreen():
            return

        self.showNormal()

        # 更新最大化按钮图标
        self.titleBar.maxButton.setMaxState(False)
        self.titleBar.returnButton.show()
        self.titleBar.show()

        self.videoWindow.playBar.fullScreenButton.setFullScreen(False)
        self.playingInterface.setFullScreen(False)
        if self.playingInterface.isPlaylistVisible:
            self.playingInterface.songInfoCardChute.move(
                0, 258 - self.height())

    def appendSubStackWidgetHistory(self, widget: QWidget):
        """ push the switching history of sub interface """
        index = self.subStackWidget.indexOf(widget)
        if self.navigationHistories[-1] == ("subStackWidget", index):
            return

        self.navigationHistories.append(('subStackWidget', index))

    def switchToSubInterface(self, widget: QWidget, whiteIcon=False, whiteReturn=False):
        """ switch to sub interface in `subStackWidget`

        Parameters
        ----------
        widget: QWidget
            the interface to be displayed

        whiteIcon: bool
            whether to set the icon color of title bar to white

        whiteReturn: bool
            Whether to set the return button to a white button
        """
        self.titleBar.returnButton.show()
        self.titleBar.setWhiteIcon(whiteIcon)
        self.titleBar.returnButton.setWhiteIcon(whiteReturn)

        # switch interface
        self.exitSelectionMode()
        self.playBar.show()
        self.totalStackWidget.setCurrentIndex(0)
        self.subStackWidget.setCurrentWidget(widget)
        self.appendSubStackWidgetHistory(widget)

    def switchToSettingInterface(self):
        """ switch to setting interface """
        self.show()

        # TODO: 从视频界面直接切换回设置界面
        if self.videoWindow.isVisible():
            return

        if self.playingInterface.isVisible():
            self.titleBar.returnButton.click()

        self.switchToSubInterface(self.settingInterface)

    def switchToMyMusicInterface(self):
        """ switch to my music interface """
        self.exitSelectionMode()
        self.subStackWidget.setCurrentWidget(self.myMusicInterface)
        self.appendSubStackWidgetHistory(self.myMusicInterface)

    def switchToPlaylistInterface(self, name: str):
        """ switch to playlist interface """
        if self.isInSelectionMode:
            return

        playlist = self.library.playlistController.getPlaylist(name)
        if not playlist:
            return

        self.playlistInterface.updateWindow(playlist)
        self.switchToSubInterface(self.playlistInterface, True)
        self.playlistInterface.songListWidget.setPlayBySongInfo(
            self.mediaPlaylist.getCurrentSong())

    def switchToPlaylistCardInterface(self):
        """ switch to playlist card interface """
        self.switchToSubInterface(self.playlistCardInterface)

    def switchToSearchResultInterface(self, keyWord: str):
        """ switch to search result interface """
        self.searchResultInterface.search(keyWord)
        self.switchToSubInterface(self.searchResultInterface)
        self.searchResultInterface.localSongListWidget.setPlayBySongInfo(
            self.mediaPlaylist.getCurrentSong())

    def switchToMoreSearchResultInterface(self, keyWord: str, viewType, data: list):
        """ switch to more search result interface """
        self.moreSearchResultInterface.updateWindow(keyWord, viewType, data)
        self.switchToSubInterface(self.moreSearchResultInterface)
        self.moreSearchResultInterface.localSongListWidget.setPlayBySongInfo(
            self.mediaPlaylist.getCurrentSong())

    def switchToSingerInterface(self, singer: str):
        """ switch to singer interface """
        if self.isInSelectionMode:
            return

        singerInfo = self.library.singerInfoController.getSingerInfoByName(
            singer)
        if not singerInfo:
            return

        self.exitFullScreen()
        self.singerInterface.updateWindow(singerInfo)
        self.switchToSubInterface(self.singerInterface, True)
        self.singerInterface.albumBlurBackground.hide()

    def switchToAlbumInterface(self, singer: str, album: str):
        """ switch to album interface """
        if self.isInSelectionMode:
            return

        albumInfo = self.library.albumInfoController.getAlbumInfo(
            singer, album)
        if not albumInfo:
            return

        self.exitFullScreen()
        self.albumInterface.updateWindow(albumInfo)
        self.switchToSubInterface(self.albumInterface, True)
        self.albumInterface.songListWidget.setPlayBySongInfo(
            self.mediaPlaylist.getCurrentSong())

    def switchToAlbumCardInterface(self):
        """ switch to album card interface """
        self.subStackWidget.setCurrentWidget(self.myMusicInterface)
        self.titleBar.setWhiteIcon(False)
        self.titleBar.returnButton.show()
        self.myMusicInterface.setCurrentTab(1)
        self.navigationInterface.setCurrentIndex(0)

        # add navigation history
        index = self.myMusicInterface.stackedWidget.indexOf(
            self.myMusicInterface.albumTabInterface)
        self.navigationHistories.append(('myMusicInterfaceStackWidget', index))

    def onMyMusicInterfaceStackWidgetIndexChanged(self, index):
        """ my music interface tab index changed slot """
        self.navigationHistories.append(("myMusicInterfaceStackWidget", index))
        self.titleBar.returnButton.show()

    def onSongTabSongCardPlay(self, songInfo: SongInfo):
        """ song tab interface play song card slot """
        songInfos = self.songTabSongListWidget.songInfos

        if self.mediaPlaylist.playlistType != PlaylistType.ALL_SONG_PLAYLIST \
                or songInfos != self.mediaPlaylist.playlist:
            self.mediaPlaylist.playlistType = PlaylistType.ALL_SONG_PLAYLIST
            songInfos = self.songTabSongListWidget.songInfos
            index = songInfos.index(songInfo)
            playlist = songInfos[index:] + songInfos[:index]
            self.setPlaylist(playlist)

        self.mediaPlaylist.setCurrentSong(songInfo)

    def onPlaylistInterfaceSongCardPlay(self, index):
        """ playlist interface song card play slot """
        songInfos = self.playlistInterface.songInfos
        self.playCustomPlaylistSong(songInfos, index)

    def playOneSongCard(self, songInfo: SongInfo):
        """ reset the playing playlist to one song """
        self.mediaPlaylist.playlistType = PlaylistType.SONG_CARD_PLAYLIST
        self.setPlaylist([songInfo])

    def updatePlaylist(self, reset=False):
        """ update playing playlist """
        playlist = self.mediaPlaylist.playlist
        self.playingInterface.setPlaylist(playlist, reset)
        self.smallestPlayInterface.setPlaylist(playlist, reset)
        self.play()

    def onSongsNextToPlay(self, songInfos: List[SongInfo]):
        """ songs next to play slot """
        reset = not self.mediaPlaylist.playlist
        index = self.mediaPlaylist.currentIndex()
        self.mediaPlaylist.insertSongs(index + 1, songInfos)
        self.updatePlaylist(reset)

    def addSongsToPlayingPlaylist(self, songInfos: list):
        """ add songs to playing playlist """
        reset = not self.mediaPlaylist.playlist
        self.mediaPlaylist.addSongs(songInfos)
        self.updatePlaylist(reset)

    def addSongsToCustomPlaylist(self, name: str, songInfos: List[SongInfo]):
        """ add songs to custom playlist """

        def resetSongInfo(songInfos: list, diffSongInfos):
            songInfos.clear()
            songInfos.extend(diffSongInfos)

        songInfos = deepcopy(songInfos)

        # find new songs
        oldPlaylist = self.library.playlistController.getPlaylist(name)
        oldFiles = [i.file for i in oldPlaylist.songInfos]
        diffSongInfos = [i for i in songInfos if i.file not in oldFiles]

        planToAddNum = len(songInfos)
        repeatNum = planToAddNum - len(diffSongInfos)

        # show dialog box if there are duplicate songs
        if repeatNum > 0:
            if planToAddNum == 1:
                content = self.tr(
                    "This song is already in your playlist. Do you want to add?")
            elif repeatNum < planToAddNum:
                content = self.tr(
                    "Some songs are already in your playlist. Do you want to add?")
            else:
                content = self.tr(
                    "All these songs are already in your playlist. Do you want to add?")

            w = MessageDialog(self.tr("Song duplication"), content, self)
            w.cancelSignal.connect(
                lambda: resetSongInfo(songInfos, diffSongInfos))
            w.exec_()

        success = self.library.playlistController.addSongs(name, songInfos)
        if not success:
            return

        self.playlistCardInterface.addSongsToPlaylist(name, songInfos)
        self.searchResultInterface.playlistGroupBox.playlistCardView.addSongsToPlaylistCard(
            name, songInfos)
        self.moreSearchResultInterface.playlistInterface.playlistCardView.addSongsToPlaylistCard(
            name, songInfos)

    def removeSongsFromCustomPlaylist(self, name: str, songInfos: List[SongInfo]):
        """ remove songs from custom playlist """
        success = self.library.playlistController.removeSongs(name, songInfos)
        if not success:
            return

        self.playlistCardInterface.removeSongsFromPlaylist(name, songInfos)
        self.searchResultInterface.playlistGroupBox.playlistCardView.removeSongsFromPlaylistCard(
            name, songInfos)
        self.moreSearchResultInterface.playlistInterface.playlistCardView.removeSongsFromPlaylistCard(
            name, songInfos)

    def playAlbum(self, singer: str, album: str, index=0):
        """ play songs in an album """
        albumInfo = self.library.albumInfoController.getAlbumInfo(
            singer, album)
        if not albumInfo:
            return

        playlist = albumInfo.songInfos
        self.playingInterface.setPlaylist(playlist, index=index)
        self.smallestPlayInterface.setPlaylist(playlist)
        self.mediaPlaylist.playAlbum(playlist, index)
        self.play()

    def playAbumSong(self, index: int):
        """ play the song in an album """
        if self.mediaPlaylist.playlistType != PlaylistType.ALBUM_CARD_PLAYLIST or \
                self.mediaPlaylist.playlist != self.albumInterface.songInfos:
            self.playAlbum(self.albumInterface.singer,
                           self.albumInterface.album, index)

        self.mediaPlaylist.setCurrentIndex(index)

    def playCustomPlaylist(self, songInfos: list, index=0):
        """ play songs in custom playlist """
        self.mediaPlaylist.playlistType = PlaylistType.CUSTOM_PLAYLIST
        self.setPlaylist(songInfos, index)

    def playCustomPlaylistSong(self, songInfos: List[SongInfo], index: int):
        """ play the song in a custom playlist  """
        if self.mediaPlaylist.playlistType != PlaylistType.CUSTOM_PLAYLIST or \
                self.mediaPlaylist.playlist != songInfos:
            self.playCustomPlaylist(songInfos, index)

        self.mediaPlaylist.setCurrentIndex(index)

    def playLocalSearchedSong(self, index: int):
        """ play selected local searched song """
        songInfos = self.searchResultInterface.localSongListWidget.songInfos
        self.playCustomPlaylistSong(songInfos, index)

    def playOnlineSearchedSong(self, index: int):
        """ play selected online searched song """
        songInfos = self.searchResultInterface.onlineSongListWidget.songInfos
        self.playCustomPlaylistSong(songInfos, index)

    def playLocalMoreSearchedSong(self, songInfo: SongInfo):
        """ play selected local more searched song """
        songInfos = self.moreSearchResultInterface.localSongListWidget.songInfos
        index = songInfos.index(songInfo)
        self.playCustomPlaylistSong(songInfos, index)

    def randomPlayAll(self):
        """ play all songs randomly """
        self.mediaPlaylist.playlistType = PlaylistType.ALL_SONG_PLAYLIST
        playlist = self.songTabSongListWidget.songInfos.copy()
        shuffle(playlist)
        self.setPlaylist(playlist)

    def onEditSongInfo(self, oldSongInfo: SongInfo, newSongInfo: SongInfo):
        """ edit song information slot """
        self.library.updateSongInfo(newSongInfo)
        self.mediaPlaylist.updateSongInfo(newSongInfo)
        self.playingInterface.updateSongInfo(newSongInfo)
        self.myMusicInterface.updateSongInfo(newSongInfo)
        self.playlistInterface.updateSongInfo(newSongInfo)
        self.albumInterface.updateSongInfo(newSongInfo)
        self.searchResultInterface.localSongListWidget.updateOneSongCard(
            newSongInfo)

    def onEditAlbumInfo(self, oldAlbumInfo: AlbumInfo, newAlbumInfo: AlbumInfo, coverPath: str):
        """ edit album information slot """
        songInfos = newAlbumInfo.songInfos
        self.library.updateMultiSongInfos(songInfos)
        self.mediaPlaylist.updateMultiSongInfos(songInfos)
        self.myMusicInterface.updateMultiSongInfos(songInfos)
        self.playingInterface.updateMultiSongInfos(songInfos)
        self.playlistInterface.updateMultiSongInfos(songInfos)
        self.albumInterface.updateMultiSongInfos(songInfos)
        self.searchResultInterface.localSongListWidget.updateMultiSongCards(
            songInfos)

    def deleteSongs(self, songPaths: List[str]):
        """ delete songs from local """
        for songPath in songPaths:
            moveToTrash(songPath)

    def onUpdateLyricPosTimeOut(self):
        """ update lyric postion timer time out """
        if self.player.state() != QMediaPlayer.PlayingState:
            return

        t = self.player.position()
        self.playingInterface.lyricWidget.setCurrentTime(t)

    def onPlayingInterfaceCurrentIndexChanged(self, index):
        """ playing interface current index changed slot """
        self.mediaPlaylist.setCurrentIndex(index)
        self.play()

    def onExit(self):
        """ exit main window """
        config = {
            "volume": self.playBar.volumeSlider.value(),
            "playBar-color": list(self.playBar.getColor().getRgb()[:3])
        }
        self.settingInterface.config.update(config)
        self.mediaPlaylist.save()
        self.systemTrayIcon.hide()

    def onNavigationLabelClicked(self, label: str):
        """ navigation label clicked slot """
        self.myMusicInterface.scrollToLabel(label)
        self.subStackWidget.setCurrentWidget(
            self.subStackWidget.previousWidget)
        self.navigationHistories.pop()

    def onSelectedFolderChanged(self, directories: List[str]):
        """ selected music folders changed slot """
        title = self.tr("Scanning song information")
        content = self.tr("Please wait patiently")
        self.scanInfoTooltip = StateTooltip(title, content, self.window())
        self.scanInfoTooltip.move(self.scanInfoTooltip.getSuitablePos())
        self.scanInfoTooltip.show()

        self.libraryThread.setTask(
            self.libraryThread.library.setDirectories, directories=directories)
        self.libraryThread.start()

    def onReloadFinished(self):
        """ reload library finished slot """
        self.libraryThread.library.copyTo(self.library)
        self.myMusicInterface.updateWindow()

        if self.scanInfoTooltip:
            self.scanInfoTooltip.setState(True)

        self.scanInfoTooltip = None

    def showCreatePlaylistDialog(self, songInfos: List[SongInfo] = None):
        """ show create playlist dialog box """
        w = CreatePlaylistDialog(self.library, songInfos, self)
        w.createPlaylistSig.connect(self.onCreatePlaylist)
        w.exec_()

    def onCreatePlaylist(self, name: str, playlist: Playlist):
        """ create a playlist """
        self.playlistCardInterface.addPlaylistCard(name, playlist)
        self.navigationInterface.updateWindow()

    def onRenamePlaylist(self, old: str, new: str):
        """ rename a playlist """
        success = self.library.playlistController.rename(old, new)
        if not success:
            return

        self.navigationInterface.updateWindow()
        self.playlistCardInterface.renamePlaylist(old, new)
        self.searchResultInterface.playlistGroupBox.playlistCardView.renamePlaylistCard(
            old, new)
        self.moreSearchResultInterface.playlistInterface.playlistCardView.renamePlaylistCard(
            old, new)

    def onDeleteCustomPlaylist(self, name: str):
        """ delete a playlist """
        success = self.library.playlistController.delete(name)
        if not success:
            return

        self.navigationInterface.updateWindow()
        self.playlistCardInterface.deletePlaylistCard(name)
        self.searchResultInterface.deletePlaylistCard(name)
        self.moreSearchResultInterface.playlistInterface.playlistCardView.deletePlaylistCard(
            name)

        if self.playlistInterface.isVisible():
            self.titleBar.returnButton.click()

        N = len(self.moreSearchResultInterface.playlistInterface.playlistCards)
        if self.moreSearchResultInterface.playlistInterface.isVisible() and N == 0:
            self.titleBar.returnButton.click()

    def onFileRemoved(self, files: List[str]):
        """ files removed slot """
        self.myMusicInterface.deleteSongs(files)
        self.albumInterface.songListWidget.removeSongCards(files)
        self.searchResultInterface.localSongListWidget.removeSongCards(files)
        self.moreSearchResultInterface.localSongListWidget.removeSongCards(
            files)

    def onFileAdded(self, songInfos: List[SongInfo]):
        """ files add slot """
        self.myMusicInterface.updateWindow()

    def onCrawMetaDataFinished(self):
        """ craw meta data finished slot """
        self.library.load()
        self.myMusicInterface.updateWindow()

    def connectSignalToSlot(self):
        """ connect signal to slot """

        # player signal
        self.player.positionChanged.connect(self.onPlayerPositionChanged)
        self.player.durationChanged.connect(self.onPlayerDurationChanged)
        self.player.mediaStatusChanged.connect(self.onMediaStatusChanged)

        # media playlist signal
        self.mediaPlaylist.currentIndexChanged.connect(self.getOnlineSongUrl)
        self.mediaPlaylist.currentIndexChanged.connect(self.updateWindow)

        # setting interface signal
        self.settingInterface.acrylicEnableChanged.connect(
            self.setWindowEffect)
        self.settingInterface.selectedMusicFoldersChanged.connect(
            self.onSelectedFolderChanged)
        self.settingInterface.downloadFolderChanged.connect(
            self.searchResultInterface.setDownloadFolder)
        self.settingInterface.onlinePlayQualityChanged.connect(
            self.searchResultInterface.setOnlinePlayQuality)
        self.settingInterface.pageSizeChanged.connect(
            self.searchResultInterface.setOnlineMusicPageSize)
        self.settingInterface.mvQualityChanged.connect(
            self.playingInterface.getMvUrlThread.setVideoQuality)
        self.settingInterface.minimizeToTrayChanged.connect(
            self.onMinimizeToTrayChanged)
        self.settingInterface.crawlFinished.connect(
            self.onCrawMetaDataFinished)

        # title signal
        self.titleBar.returnButton.clicked.connect(self.onReturnButtonClicked)

        # navigation interface signal
        self.navigationInterface.displayModeChanged.connect(
            self.onNavigationDisplayModeChanged)
        self.navigationInterface.showCreatePlaylistDialogSig.connect(
            self.showCreatePlaylistDialog)
        self.navigationInterface.searchSig.connect(
            self.switchToSearchResultInterface)

        # play bar signal
        self.playBar.savePlaylistSig.connect(
            lambda: self.showCreatePlaylistDialog(self.mediaPlaylist.playlist))

        # signal bus signal
        signalBus.nextSongSig.connect(self.mediaPlaylist.next)
        signalBus.lastSongSig.connect(self.mediaPlaylist.previous)
        signalBus.togglePlayStateSig.connect(self.togglePlayState)
        signalBus.progressSliderMoved.connect(self.onProgressSliderMoved)

        signalBus.muteStateChanged.connect(self.setMute)
        signalBus.volumeChanged.connect(self.onVolumeChanged)

        signalBus.loopModeChanged.connect(self.switchLoopMode)
        signalBus.randomPlayChanged.connect(self.setRandomPlay)

        signalBus.fullScreenChanged.connect(self.setFullScreen)

        signalBus.playAlbumSig.connect(self.playAlbum)
        signalBus.randomPlayAllSig.connect(self.randomPlayAll)
        signalBus.playCheckedSig.connect(self.playCustomPlaylist)
        signalBus.playOneSongCardSig.connect(self.playOneSongCard)
        signalBus.nextToPlaySig.connect(self.onSongsNextToPlay)

        signalBus.editSongInfoSig.connect(self.onEditSongInfo)
        signalBus.editAlbumInfoSig.connect(self.onEditAlbumInfo)

        signalBus.addSongsToPlayingPlaylistSig.connect(
            self.addSongsToPlayingPlaylist)
        signalBus.addSongsToCustomPlaylistSig.connect(
            self.addSongsToCustomPlaylist)
        signalBus.addSongsToNewCustomPlaylistSig.connect(
            self.showCreatePlaylistDialog)
        signalBus.selectionModeStateChanged.connect(
            self.onSelectionModeStateChanged)

        signalBus.removeSongSig.connect(self.deleteSongs)
        signalBus.clearPlayingPlaylistSig.connect(self.clearPlaylist)
        signalBus.deletePlaylistSig.connect(self.onDeleteCustomPlaylist)
        signalBus.renamePlaylistSig.connect(self.onRenamePlaylist)

        signalBus.showPlayingPlaylistSig.connect(self.showPlayingPlaylist)
        signalBus.showPlayingInterfaceSig.connect(self.showPlayingInterface)
        signalBus.switchToSingerInterfaceSig.connect(
            self.switchToSingerInterface)
        signalBus.switchToAlbumInterfaceSig.connect(
            self.switchToAlbumInterface)
        signalBus.switchToMyMusicInterfaceSig.connect(
            self.switchToMyMusicInterface)
        signalBus.switchToPlaylistInterfaceSig.connect(
            self.switchToPlaylistInterface)
        signalBus.switchToPlaylistCardInterfaceSig.connect(
            self.switchToPlaylistCardInterface)
        signalBus.switchToSettingInterfaceSig.connect(
            self.switchToSettingInterface)
        signalBus.switchToMoreSearchResultInterfaceSig.connect(
            self.switchToMoreSearchResultInterface)
        signalBus.showSmallestPlayInterfaceSig.connect(
            self.showSmallestPlayInterface)
        signalBus.showLabelNavigationInterfaceSig.connect(
            self.showLabelNavigationInterface)

        # playing interface signal
        self.playingInterface.currentIndexChanged.connect(
            self.onPlayingInterfaceCurrentIndexChanged)
        self.playingInterface.removeSongSignal.connect(
            self.mediaPlaylist.removeSong)
        self.playingInterface.selectionModeStateChanged.connect(
            self.onSelectionModeStateChanged)
        self.playingInterface.switchToVideoInterfaceSig.connect(
            self.showVideoWindow)

        # song tab interface song list widget signal
        self.songTabSongListWidget.playSignal.connect(
            self.onSongTabSongCardPlay)

        # my music interface signal
        self.myMusicInterface.currentIndexChanged.connect(
            self.onMyMusicInterfaceStackWidgetIndexChanged)

        # update lyrics position timer signal
        self.updateLyricPosTimer.timeout.connect(self.onUpdateLyricPosTimeOut)

        # album interface signal
        self.albumInterface.songCardPlaySig.connect(
            self.playAbumSong)

        # playlist interface signal
        self.playlistInterface.songCardPlaySig.connect(
            self.onPlaylistInterfaceSongCardPlay)
        self.playlistInterface.removeSongSig.connect(
            self.removeSongsFromCustomPlaylist)
        self.playlistInterface.switchToAlbumCardInterfaceSig.connect(
            self.switchToAlbumCardInterface)

        # playlist card interface signal
        self.playlistCardInterface.createPlaylistSig.connect(
            self.showCreatePlaylistDialog)

        # smallest play interface signal
        self.smallestPlayInterface.exitSmallestPlayInterfaceSig.connect(
            self.exitSmallestPlayInterface)

        # label navigation interface signal
        self.labelNavigationInterface.labelClicked.connect(
            self.onNavigationLabelClicked)

        # search result interface signal
        self.searchResultInterface.playLocalSongSig.connect(
            self.playLocalSearchedSong)
        self.searchResultInterface.playOnlineSongSig.connect(
            self.playOnlineSearchedSong)

        # more search result interface signal
        self.moreSearchResultInterface.playLocalSongSig.connect(
            self.playLocalMoreSearchedSong)

        # system tray icon signal
        qApp.aboutToQuit.connect(self.onExit)
        self.systemTrayIcon.exitSignal.connect(qApp.quit)
        self.systemTrayIcon.showMainWindowSig.connect(self.show)

        # video window signal
        self.videoWindow.fullScreenChanged.connect(self.setVideoFullScreen)

        # library thread signal
        self.libraryThread.reloadFinished.connect(self.onReloadFinished)

        # library signal
        self.library.fileAdded.connect(self.onFileAdded)
        self.library.fileRemoved.connect(self.onFileRemoved)


class SplashScreen(QWidget):
    """ Splash screen """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.hBoxLayout = QHBoxLayout(self)
        self.logo = QLabel(self)
        self.logo.setPixmap(QPixmap(":/images/logo/splash_screen_logo.png"))
        self.hBoxLayout.addWidget(self.logo, 0, Qt.AlignCenter)
        self.setAttribute(Qt.WA_StyledBackground)
        self.setStyleSheet('background:white'



import sys

from qtreactor import pyqt4reactor
from PyQt4 import QtGui
from twisted.python import log

app = QtGui.QApplication(sys.argv)
pyqt4reactor.install()

from twisted.protocols.basic import LineReceiver
from twisted.internet.protocol import Factory


class RelayProtocol(LineReceiver):
    def __init__(self):
        self.factory = None
        self.window = None

    def connectionMade(self):
        log.msg('connected to relay')
        self.factory.setRelay(self)

    def lineReceived(self, line):
        log.msg(line)
        self.factory.window.show(line)


class RelayFactory(Factory):
    protocol = RelayProtocol

    def __init__(self, window):
        self.relay = None
        self.window = window
        self.nickname = None

    def startedConnecting(self, connector):
        log.msg('connecting to relay...')

    def getRelay(self):
        return self.relay

    def setRelay(self, rl):
        self.relay = rl

    def setNickname(self, nickname):
        self.nickname = nickname

    def buildProtocol(self, addr):
        self.relay = RelayProtocol()
        self.relay.factory = self
        return self.relay

    def clientConnectionLost(self, connector, reason):
        line = 'Connection lost: {0}'.format(reason)
        self.window.show(line)
        # connector.connect()

    def connectServer(self, servername, nickname, port=6667):
        # connect <server> <nickname> <port>
        line = 'connect {0} {1} {2}'.format(servername, nickname, port)
        self.relay.sendLine(line)

    def sendMessage(self, channel, message):
        # sendLine <channel> <message>
        line = 'sendLine {0} {1}'.format(channel, message)
        self.relay.sendLine(line)


class MainWindow(QtGui.QMainWindow):
    def __init__(self):
        log.startLogging(sys.stdout)

        super(MainWindow, self).__init__()

        layout = QtGui.QHBoxLayout()

        layout.addWidget(QtGui.QLabel('Server'))
        self.serverName = QtGui.QLineEdit('irc.freenode.net')
        layout.addWidget(self.serverName)

        layout.addWidget(QtGui.QLabel('Channel'))
        self.channelName = QtGui.QLineEdit('#secretfun')
        layout.addWidget(self.channelName)

        layout.addWidget(QtGui.QLabel('Nickname'))
        self.nickName = QtGui.QLineEdit('twisted_toast2')
        layout.addWidget(self.nickName)

        self.connectButton = QtGui.QPushButton('Connect')
        layout.addWidget(self.connectButton)
        self.connectButton.clicked.connect(self.connect_irc_server)

        self.view = QtGui.QListWidget()
        self.entry = QtGui.QLineEdit()
        self.entry.returnPressed.connect(self.handle_line)

        irc_widget = QtGui.QWidget(self)

        vbox = QtGui.QVBoxLayout()
        vbox.addLayout(layout)
        vbox.addWidget(self.view)
        vbox.addWidget(self.entry)

        irc_widget.setLayout(vbox)

        self.setCentralWidget(irc_widget)

        self.setWindowTitle('IRC')

        self.setUnifiedTitleAndToolBarOnMac(True)

        self.showMaximized()

        self.protocol = None

        self.relayFactory = RelayFactory(window=self)
        log.msg('relayFactory.window: ', self.relayFactory.window)

        from twisted.internet import reactor

        reactor.connectTCP('localhost', 9993, self.relayFactory)
        reactor.run()

        # def connect_irc_server(self):
        # self.

    def connect_irc_server(self):
        self.connectButton.setDisabled(True)

        self.channelName.setDisabled(True)
        self.nickName.setDisabled(True)
        self.serverName.setDisabled(True)

        nickname = self.nickName.text()
        servername = self.serverName.text()

        self.relayFactory.setNickname(nickname)

        self.relayFactory.connectServer(servername, nickname)

    def send_message(self):
        channelname = self.channelName.text()
        message = self.entry.text()

        self.relayFactory.sendMessage(channelname, message)

        self.show('{0} <{1}> {2}'.format(channelname, self.relayFactory.nickname, message))

    def send_command(self, line):
        # No checking at this point, hope your command is sane
        log.msg('Command: ', line)
        self.relayFactory.relay.sendLine(line)

    def show(self, line):
        self.view.addItem(line)

    def handle_line(self):
        # Split twice, ignore everything after the channel name
        cmd = self.entry.text().split(' ', 2)

        if cmd[0] == '/join':
            # Join a channel
            line = 'join {}'.format(cmd[1])
            self.show(line)
            self.send_command(line)

        else:
            # Send unrecognized line as a message to the current channel
            # sendLine <channel> <message>
            channelname = self.channelName.text()
            message = self.entry.text()

            lineToShow = '{0} <{1}> {2}'.format(channelname, self.relayFactory.nickname, message)
            line = 'sendLine {0} {1}'.format(channelname, message)

            self.show(lineToShow)
            self.send_command(line)


if __name__ == '__main__':
    mainWin = MainWindow()
    sys.exit(app.exec_())

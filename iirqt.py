import sys
from time import sleep

from qtreactor import pyqt4reactor
from PyQt4 import QtGui
from twisted.python import log

app = QtGui.QApplication(sys.argv)
pyqt4reactor.install()

from twisted.protocols.basic import LineReceiver
from twisted.internet.protocol import Factory

import iirc


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

    def sendMessage(self, server, channel, message):
        # sendLine <server> <channel> <message>
        line = 'sendLine {0} {1} {2}'.format(server, channel, message)
        self.relay.sendLine(line)


class MainWindow(QtGui.QMainWindow):
    def __init__(self):
        DEBUG = True

        self.selectedChannel = "core"

        log.startLogging(sys.stdout)

        super(MainWindow, self).__init__()

        """Set up the window layout"""
        # [ [server name] [nickname] (connect) ]
        serverLine = QtGui.QHBoxLayout()

        serverLine.addWidget(QtGui.QLabel('Server'))
        self.serverName = QtGui.QLineEdit('irc.freenode.net')
        serverLine.addWidget(self.serverName)

        serverLine.addWidget(QtGui.QLabel('Nickname'))
        self.nickName = QtGui.QLineEdit('twisted_toast2')
        serverLine.addWidget(self.nickName)

        self.connectButton = QtGui.QPushButton('Connect')
        serverLine.addWidget(self.connectButton)
        self.connectButton.clicked.connect(self.IRCConnectServer)

        self.view = QtGui.QListWidget()
        self.entry = QtGui.QLineEdit()
        self.entry.returnPressed.connect(self.handle_line)


        # [ [tree channel list] [                    chat window                   ]
        """
        Set up the channel tree widget.
        Add the default server which represents core messages
        Expand all collapsibles.
        """

        chatLine = QtGui.QHBoxLayout()

        self.channelTree = QtGui.QTreeWidget()
        self.channelTree.setColumnCount(1)
        self.channelTree.setFixedWidth(200)

        # coreBuffer = QtGui.QTreeWidgetItem(self.channelTree)
        # coreBuffer.setText(0, 'TestServer.net')

        self.addServerToTree("IIRC Core")

        # self.channelTree.add(coreBuffer)

        chatLine.addWidget(self.channelTree)
        chatLine.addWidget(self.view)

        entryLine = QtGui.QHBoxLayout()

        self.channelName = QtGui.QLineEdit('#secretfun')
        self.channelName.setFixedWidth(150)
        entryLine.addWidget(QtGui.QLabel('Channel'))
        entryLine.addWidget(self.channelName)
        entryLine.addWidget(QtGui.QLabel('<<'))
        entryLine.addWidget(self.entry)

        irc_widget = QtGui.QWidget(self)

        vbox = QtGui.QVBoxLayout()
        vbox.addLayout(serverLine)
        vbox.addLayout(chatLine)
        # vbox.addWidget(self.view)
        vbox.addLayout(entryLine)

        irc_widget.setLayout(vbox)

        self.statusBar().showMessage('Ready to Connect')

        self.setCentralWidget(irc_widget)

        self.setWindowTitle('IIRC')

        self.setUnifiedTitleAndToolBarOnMac(True)

        self.resize(1200, 850)

        self.setVisible(True)

        self.protocol = None
        """End layout setup"""

        self.relayFactory = RelayFactory(window=self)
        log.msg('relayFactory.window: ', self.relayFactory.window)

        from twisted.internet import reactor

        reactor.connectTCP('localhost', 9993, self.relayFactory)
        reactor.run()

        if DEBUG is True:
            self.IRCConnectServer()
            self.entry.insert('/join #secretfun')

            # def connect_irc_server(self):
            # self.

    def addServerToTree(self, serverName):
        newServer = QtGui.QTreeWidgetItem(self.channelTree)
        newServer.setText(0, serverName)
        list = self.channelTree.selectedItems()
        # Have to clear the selectness of other items
        for thing in list:
            thing.setSelected(False)

        # Scroll to new server and select it
        self.channelTree.scrollToItem(newServer)
        self.channelTree.setItemSelected(newServer, True)
        # newServer.setBackgroundColor(0, QtCore.Qt.red)

    def clearTreeSelections(self):
        selections = self.channelTree.selectedItems()
        for item in selections:
            item.setSelected(False)

    def addChannelToTree(self, serverParent, channelName):
        # serverParent is a channel tree item
        log.msg('Adding', channelName, 'to', serverParent.text(0))
        newChannel = QtGui.QTreeWidgetItem(serverParent)
        newChannel.setText(0, channelName)
        serverParent.addChild(newChannel)
        # Expand the server tree
        serverParent.setExpanded(True)
        # Select the new item
        self.clearTreeSelections()
        newChannel.setSelected(True)

    def IRCConnectServer(self):
        self.connectButton.setDisabled(True)

        # self.channelName.setDisabled(True)
        self.nickName.setDisabled(True)
        self.serverName.setDisabled(True)

        nickname = self.nickName.text()
        servername = self.serverName.text()

        self.addServerToTree(servername)

        self.relayFactory.setNickname(nickname)

        self.relayFactory.connectServer(servername, nickname)

    def IRCConnectChannel(self, channel):
        # Tell core to connect
        server = self.getSelectedServer()
        line = 'join {0} {1}'.format(self.getSelectedServer().text(0), channel)
        self.send_command(line)
        self.addChannelToTree(server, channel)
        self.entry.clear()

    def IRCSendLine(self, message):
        # Send a line to the currently highlight channel
        server = self.getSelectedServer().text(0)
        channel = self.getSelectedChannel().text(0)

        lineToShow = '{0} <{1}> {2}'.format(channel, self.relayFactory.nickname, message)
        # TODO: set up an array to hold servers and channels, use nickname from there
        line = 'sendLine {0} {1} {2}'.format(server, channel, message)
        self.show(lineToShow, clear=True, bottom=True)
        self.send_command(line)

    def send_message(self):
        channelname = self.channelName.text()
        message = self.entry.text()
        # TODO: Need to make sure it's a channel first
        servername = self.channelTree.selectedItems()[0].parent().getText()
        log.msg("Sending line to server: " + servername)

        self.relayFactory.sendMessage(servername, channelname, message)

        self.show('{0} <{1}> {2}'.format(channelname, self.relayFactory.nickname, message), clear=True)

    def send_command(self, line):
        # No checking at this point, hope your command is sane
        log.msg('Command: ', line)
        self.relayFactory.relay.sendLine(line)

    def show(self, line, clear=False, bottom=False):
        self.view.addItem(line)
        if clear:
            self.entry.clear()
        if bottom:
            self.view

    def getSelectedServer(self):
        # Returns the currently selected ITEM in the channel tree
        item = self.channelTree.selectedItems()[0]
        log.msg(item.text(0), item.parent())
        if item.parent() is None:
            return item
        else:
            return item.parent()

    def getSelectedChannel(self):
        # TODO: Check to make sure it's actually a channel
        item = self.channelTree.selectedItems()[0]
        return item

    def handle_line(self):
        # Split twice, ignore everything after the channel name
        cmd = self.entry.text().split(' ', 2)

        if cmd[0] == '/join':
            # Join a channel
            # > join <server> <channel>
            channel = cmd[1]
            self.IRCConnectChannel(channel)

        elif cmd[0] == '/part':
            # Leave (part) a channel
            # > part <channel>
            line = 'part {}'.format(cmd[1])
            self.show(line)
            self.send_command(line)
            self.IRCConnectChannel(self.getSelectedServer())

        else:
            # Send unrecognized line as a message to the current channel
            # > sendLine <server> <channel> <message>
            message = self.entry.text()
            self.IRCSendLine(message)


if __name__ == '__main__':
    DEBUG = True
    iirc.startIIRC()
    sleep(1)
    mainWin = MainWindow()
    sys.exit(app.exec_())

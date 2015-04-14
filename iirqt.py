import sys

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
        # log.msg(line)
        cmd = line.split(' ', 1)

        if cmd[0] == 'msg':
            self.factory.window.show(cmd[1], bottom=True)


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


class connectDialog(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__(self)

    def initUI(self):
        self.setGeometry(100, 100, 400, 200)
        self.setWindowTitle('Connect to a server')

        # Set up the entry boxes
        serverLine = QtGui.QHBoxLayout()
        serverName = QtGui.QLineEdit()
        serverLine.addWidget(QtGui.QLabel('Server name: '))
        serverLine.addWidget(serverName)

        portLine = QtGui.QHBoxLayout()
        portName = QtGui.QLineEdit()
        portName.setPlaceholderText('6667')
        portLine.addWidget(QtGui.QLabel('Port: '))
        portLine.addWidget(portName)

        connectBtn = QtGui.QPushButton('Connect')


        # Main layout
        windowLayout = QtGui.QVBoxLayout()
        windowLayout.addLayout(serverLine)
        windowLayout.addLayout(portLine)
        windowLayout.addWidget(connectBtn)
        self.setLayout(windowLayout)
        self.show()


class MainWindow(QtGui.QMainWindow):
    def __init__(self):
        DEBUG = True
        self.chatWindow = None

        log.startLogging(sys.stdout)

        super(MainWindow, self).__init__()

        """Set up the window layout"""

        """ Setting up the menu bar and tool bar"""
        menuBar = self.menuBar()
        serverMenu = menuBar.addMenu('&Server')

        connectAction = QtGui.QAction('&Connect to server', self)
        connectAction.setShortcut('Ctrl+C')
        connectAction.setStatusTip('Connect to an IRC network')
        connectAction.triggered.connect(self.connectWindow)
        serverMenu.addAction(connectAction)

        # # [ [server name] [nickname] (connect) ]
        # serverLine = QtGui.QHBoxLayout()
        #
        # serverLine.addWidget(QtGui.QLabel('Server'))
        # self.serverName = QtGui.QLineEdit('irc.freenode.net')
        # serverLine.addWidget(self.serverName)
        #
        # serverLine.addWidget(QtGui.QLabel('Nickname'))
        # self.nickName = QtGui.QLineEdit('twisted_toast2')
        # serverLine.addWidget(self.nickName)
        #
        # self.connectButton = QtGui.QPushButton('Connect')
        # serverLine.addWidget(self.connectButton)
        # self.connectButton.clicked.connect(self.IRCConnectServer)


        # [ [tree channel list] [                    chat window                   ]
        """
        Set up the channel tree widget.
        Add the default server which represents core messages
        Expand all collapsibles.
        """
        """
        The bufferDict holds information about every buffer currently in view.
        A buffer is any view that displays chat text and has a channel tree item (channels and servers)

        bufferDict is keyed by the text name of server+channel (irc.freenode.net#secretfun)
        You can delimit on the #, everything after is the channel

        bufferdict is periodically updated by the ircclients through the relay, it's just meant to be
        a local copy of some oft-accessed information
        """
        self.bufferDict = {}

        chatLine = QtGui.QHBoxLayout()

        # Channel Tree
        self.channelTree = QtGui.QTreeWidget()
        self.channelTree.setColumnCount(1)
        self.channelTree.setFixedWidth(200)
        self.channelTree.setHeaderLabel('Channels')
        self.channelTree.itemClicked.connect(self.changeView)

        # Chat window
        self.chatWindow = QtGui.QStackedWidget()
        self.coreList = QtGui.QListWidget()
        self.coreList.addItem('Test')

        self.chatWindow.addWidget(self.coreList)

        # Entry text box
        self.entry = QtGui.QLineEdit()
        self.entry.returnPressed.connect(self.handle_line)

        # Add the core buffer as the first chat view
        self.addServerToTree('IIRC Core', 'corebuffer')
        self.bufferDict['IIRC Core'] = {'index': 1}

        chatLine.addWidget(self.channelTree)
        chatLine.addWidget(self.chatWindow)

        entryLine = QtGui.QHBoxLayout()

        self.channelName = QtGui.QLineEdit('#secretfun')
        self.channelName.setFixedWidth(150)
        entryLine.addWidget(QtGui.QLabel('Channel'))
        entryLine.addWidget(self.channelName)
        entryLine.addWidget(QtGui.QLabel('<<'))
        entryLine.addWidget(self.entry)

        mainLayout = QtGui.QWidget(self)

        vbox = QtGui.QVBoxLayout()
        # vbox.addLayout(serverLine)
        vbox.addLayout(chatLine)
        # vbox.addWidget(self.view)
        vbox.addLayout(entryLine)

        mainLayout.setLayout(vbox)

        self.statusBar().showMessage('Ready to Connect')
        self.setCentralWidget(mainLayout)
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

    def connectWindow(self):
        self.cw = connectDialog()
        self.cw.initUI()

    def addServerToTree(self, serverName, nickname):
        newServer = QtGui.QTreeWidgetItem(self.channelTree)
        newServer.setText(0, serverName)
        list = self.channelTree.selectedItems()
        # Have to clear the selectness of other items
        self.clearTreeSelections()

        # Scroll to new server and select it
        self.channelTree.scrollToItem(newServer)
        self.channelTree.setItemSelected(newServer, True)
        # newServer.setBackgroundColor(0, QtCore.Qt.red)

        identifier = str(serverName)
        # Count always one more than highest index
        index = self.chatWindow.count()
        newBuffer = QtGui.QListWidget()
        self.bufferDict[identifier] = {'index': index, 'buffer': newBuffer, 'nick': str(nickname)}

        # Create the chat view
        self.chatWindow.addWidget(newBuffer)
        self.chatWindow.setCurrentIndex(index)

    def clearTreeSelections(self):
        selections = self.channelTree.selectedItems()
        for item in selections:
            item.setSelected(False)

    def addChannelToTree(self, serverParent, channelName):
        # serverParent is a channel tree item
        server = self.getSelectedServer()
        log.msg('Adding', channelName, 'to', server.text(0))
        newChannel = QtGui.QTreeWidgetItem(server)
        newChannel.setText(0, channelName)
        serverParent.addChild(newChannel)

        # Create the chat view
        identifier = str(server.text(0)) + str(channelName)
        index = self.chatWindow.count()
        newBuffer = QtGui.QListWidget()
        self.bufferDict[identifier] = {'index': index, 'buffer': newBuffer}
        self.chatWindow.addWidget(newBuffer)

        # Expand the server tree
        serverParent.setExpanded(True)

        # Select the new item
        self.clearTreeSelections()
        newChannel.setSelected(True)
        self.chatWindow.setCurrentIndex(index)

        log.msg('bufferDict: ', self.bufferDict)

    def IRCConnectServer(self, server, nickname):
        self.entry.clear()
        self.addServerToTree(server, nickname)
        # self.relayFactory.setNickname(nickname)
        self.relayFactory.connectServer(server, nickname)

    def IRCConnectChannel(self, channel):
        # Tell core to connect
        server = self.getSelectedServer()
        line = 'join {0} {1}'.format(self.getSelectedServer().text(0), channel)
        self.send_command(line)
        self.addChannelToTree(server, channel)
        self.entry.clear()

    def IRCSendLine(self, message):
        # Send a line to the currently highlight channel
        server = str(self.getSelectedServer().text(0))
        channel = str(self.getSelectedChannel().text(0))
        nickname = str(self.bufferDict[server]['nick'])

        log.msg('IRCSendLine server: ', server, '  channel: ', channel)

        # TODO: set up an array to hold servers and channels, use nickname from there
        line = 'sendLine {0} {1} {2} {3}'.format(server, channel, nickname, message)
        lineToShow = '{0} {1} {2} {3}'.format(server, channel, nickname, message)
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
        log.msg('iirqt sending command: ', line)
        self.relayFactory.relay.sendLine(line)

    def show(self, line, clear=False, bottom=False):
        # Find the index of the right list widget and add to that
        # <server> <channel> <user> <msg>
        arg = line.split(' ', 3)
        log.msg('show log: ', line, arg)
        server = arg[0]
        channel = arg[1]
        user = arg[2]
        msg = arg[3]

        log.msg('show arguments: {0} {1} {2} {3}'.format(server, channel, user, msg))
        log.msg('show current buffer: ', self.chatWindow.currentIndex())

        identifier = server + channel
        # index = self.bufferDict[identifier]['index']
        buffer = self.bufferDict[identifier]['buffer']

        line = '<{0}> {1}'.format(user, msg)

        buffer.addItem(line)
        if clear:
            self.entry.clear()
        if bottom:
            buffer.scrollToBottom()

    def getSelectedServer(self):
        # Returns the currently selected ITEM in the channel tree
        item = self.channelTree.selectedItems()[0]
        log.msg('Query for server: ', item.text(0), item.parent().text(0) if item.parent() is not None else 'no parent')
        if item.parent() is None:
            return item
        else:
            return item.parent()

    def getSelectedChannel(self):
        # TODO: Check to make sure it's actually a channel
        item = self.channelTree.selectedItems()[0]
        return item

    def handle_line(self):
        line = self.entry.text()
        log.msg('Handling line: ', line)

        if line.startsWith('/join'):
            # Join a channel
            # > join <server> <channel>
            channel = line.split(' ', 1)[1]
            self.IRCConnectChannel(channel)

            # elif line.startsWith('/part'):
            # Leave (part) a channel
            # > part <channel>
            # channel = cmd[1]
            # line = 'part {}'.format(channel)
            # self.show(line)
            # self.send_command(line)
            # self.IRCConnectChannel(self.getSelectedServer())

        # elif cmd[0] == '/connect':
        elif line.startsWith('/connect'):
            # Connect to a server
            # > connect <server> <nickname>
            arg = line.split(' ', 2)
            server = arg[1]
            nickname = arg[2]
            self.IRCConnectServer(server, nickname)

        else:
            # Send unrecognized line as a message to the current channel
            # > sendLine <server> <channel> <message>
            self.IRCSendLine(line)

    def changeView(self, item, index):
        log.msg('changeView triggered, item: ', item, '  index: ', index)
        server = self.getSelectedServer()
        channel = self.getSelectedChannel()
        identifier = str(server.text(0)) + str(channel.text(0))
        # A server buffer will have identical server and channel
        if server == channel:
            buffer = self.bufferDict[str(server.text(0))]['buffer']
        else:
            buffer = self.bufferDict[identifier]['buffer']
        self.chatWindow.setCurrentWidget(buffer)


if __name__ == '__main__':
    DEBUG = True
    iirc.startIIRC()
    # sleep(1)
    mainWin = MainWindow()
    sys.exit(app.exec_())

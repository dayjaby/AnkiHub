from PyQt4 import QtCore,QtGui
import httplib
import urllib2
import json
import os
import sys
from AnkiHub.updates import Ui_DialogUpdates
from AnkiHub.markdown2 import markdown
import aqt
from anki.hooks import addHook

headers = {"User-Agent": "AnkiHub"}
dataPath = os.path.expanduser('~/.ankihub.json')


class DialogUpdates(QtGui.QDialog, Ui_DialogUpdates):
    def __init__(self, parent, data, oldData, callback, automaticAnswer=None):
        QtGui.QDialog.__init__(self,parent)
        self.setupUi(self)
        totalSize = sum(map(lambda x:x['size'],data['assets']))

        def answer(doUpdate,answ,append):
            callback(doUpdate,answ,append)
            self.close()

        self.html = u''
        self.appendHtml(markdown(data['body']))

        if not automaticAnswer:
            self.connect(self.update,QtCore.SIGNAL('clicked()'),
                         lambda:answer(True,'ask',self.appendHtml))
            self.connect(self.dont,QtCore.SIGNAL('clicked()'),
                     lambda:answer(False,'ask',self.appendHtml))
            self.connect(self.always,QtCore.SIGNAL('clicked()'),
                     lambda:answer(True,'always',self.appendHtml))
            self.connect(self.never,QtCore.SIGNAL('clicked()'),
                     lambda:answer(False,'never',self.appendHtml))
        else:
            self.update.setEnabled(False)
            self.dont.setEnabled(False)
            self.always.setEnabled(False)
            self.never.setEnabled(False)
            answer(True,automaticAnswer,self.appendHtml)

        fromVersion = ''
        if 'tag_name' in oldData:
            fromVersion = u'from {0} '.format(oldData['tag_name'])
        self.labelUpdates.setText(
            unicode(self.labelUpdates.text()).format(
                data['name'],
                fromVersion,
                data['tag_name']))


    def appendHtml(self,html='',temp=''):
        self.html += html
        self.textBrowser.setHtml(u'<html><body>{0}{1}</body></html>'.format(self.html,temp))


def asset(a):
    return {
        'url': a['browser_download_url'],
        'size': a['size']
    }

profileLoaded = False
def _profileLoaded():
    profileLoaded = True

addHook("profileLoaded",_profileLoaded)

def updateSingle(repositories,path,data):
    def callback(doUpdate,answer,appendHtml):
        if doUpdate:
            repositories[path] = data
            for asset in data['assets']:
                code = asset['url']
                p, fname = os.path.split(code)
                response = urllib2.urlopen(code)
                meta = response.info()
                file_size = int(meta.getheaders("Content-Length")[0])
                d = buffer('')
                dl = 0
                i = 0
                lastPercent = None
                while True:
                    dkb = response.read(1024)
                    if not dkb:
                        break
                    dl += len(dkb)
                    d += dkb
                    if dl*100/file_size>i:
                        lastPercent = int(dl*100/file_size)
                        i = lastPercent+1
                        appendHtml(temp='<br />Downloading {1}: {0}%<br/>'.format(lastPercent,fname))
                    QtGui.QApplication.instance().processEvents()
                appendHtml('<br />Downloading {1}: 100%<br/>'.format(int(dl*100/file_size),fname))
                def installData():
                    aqt.mw.addonManager.install(d,fname)
                    repositories[path]['update'] = answer
                    with open(dataPath,'w') as file:
                        json.dump(repositories,file,indent=2)
                if profileLoaded:
                    installData()
                else:
                    addHook("profileLoaded",installData)
        else:
            repositories[path]['update'] = answer
            with open(dataPath,'w') as file:
                json.dump(repositories,file,indent=2)
    return callback

datas = []

def update(add=[],install=False):
    conn = httplib.HTTPSConnection("api.github.com")
    try:
        with open(dataPath,'r') as file:
            repositories = json.load(file)
    except:
        repositories = {
            'dayjaby/AnkiHub': {
                'id': 4089471,
                'update': 'ask'
            }
        }
    for a in add:
        if a not in repositories:
            repositories[a] = {
                'id': 0,
                'update': 'ask'
            }

    for path,repository in repositories.items():
        if repository['update'] != 'never':
            try:
                response = urllib2.urlopen("https://api.github.com/repos/{0}/releases/latest".format(path))
                data = response.read()
                release = json.loads(data)
                datas.append(data)
            except Exception as e:
                datas.append(e)
                release = {}
            if 'id' in release:
                if release['id'] != repository['id']:
                    data = {
                        'id': release['id'],
                        'name': release['name'],
                        'tag_name': release['tag_name'],
                        'body': release['body'],
                        'assets': map(asset,release['assets']),
                        'update': 'ask'
                    }
                    if repository['update'] == 'always':
                        dialog = DialogUpdates(None,data,repository,updateSingle(repositories,path,data),'always')
                    elif install:
                        dialog = DialogUpdates(None,data,repository,updateSingle(repositories,path,data),'ask')
                    else:
                        dialog = DialogUpdates(None,data,repository,updateSingle(repositories,path,data))
                    dialog.exec_()
    with open(dataPath,'w') as file:
        json.dump(repositories,file,indent=2)

update()

def addRepository():
    repo, ok = QtGui.QInputDialog.getText(aqt.mw,'Add GitHub repository',
                                          'Path:',text='<name>/<repository>')
    if repo and ok:
        update([repo],install=True)

firstAction = aqt.mw.form.menuPlugins.actions()[0]
action = QtGui.QAction('From GitHub', aqt.mw)
action.setIconVisibleInMenu(True)
action.triggered.connect(addRepository)
aqt.mw.form.menuPlugins.insertAction(firstAction,action)

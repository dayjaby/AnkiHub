from PyQt4 import QtCore,QtGui
import httplib
import requests
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
    def __init__(self, parent, data, oldData, callback):
        QtGui.QDialog.__init__(self,parent)
        self.setupUi(self)
        totalSize = sum(map(lambda x:x['size'],data['assets']))

        def answer(doUpdate,answ):
            callback(doUpdate,answ)
            self.close()

        self.connect(self.update,QtCore.SIGNAL('clicked()'),
                     lambda:answer(True,'ask'))
        self.connect(self.dont,QtCore.SIGNAL('clicked()'),
                     lambda:answer(False,'ask'))
        self.connect(self.always,QtCore.SIGNAL('clicked()'),
                     lambda:answer(True,'always'))
        self.connect(self.never,QtCore.SIGNAL('clicked()'),
                     lambda:answer(False,'never'))

        self.labelUpdates.setText(
            unicode(self.labelUpdates.text()).format(
                data['name'],
                oldData.get('tag_name') or unicode(),
                data['tag_name']))

        html = '<html><body>'
        html += markdown(data['body'])
        html += '</body></html>'
        self.textBrowser.setHtml(html)




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
    def callback(doUpdate,answer):
        if doUpdate:
            repositories[path] = data
            for asset in data['assets']:
                code = asset['url']
                p, fname = os.path.split(code)
                d = requests.get(code)
                def installData():
                    aqt.mw.addonManager.install(d.content,fname)
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
                conn.request("GET", "/repos/{0}/releases/latest".format(path),headers=headers)
                r1 = conn.getresponse()
                data = r1.read()
                release = json.loads(data)
            except:
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
                        updateSingle(repositories,path,data)(True,'always')
                    elif install:
                        updateSingle(repositories,path,data)(True,'ask')
                    else:
                        dialog = DialogUpdates(None,data,repository,updateSingle(repositories,path,data))
                        dialog.exec_()

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

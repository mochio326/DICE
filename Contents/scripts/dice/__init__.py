# # -*- coding: utf-8 -*-
from mochinode.vendor.Qt import QtCore, QtGui, QtWidgets
from . import common
from . import node_xml
from . import node_original
from . import view

import exprespy
from maya import cmds
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
import json
import ast
import os
import functools


class DragLabel(QtWidgets.QLabel):

    def __init__(self, title, drag_text):
        super(DragLabel, self).__init__(title)
        self.drag_text = drag_text
        self._set_css()

    def _set_css(self, color='rgb(200,200,200)'):
        self.setStyleSheet(
            "color : {0};"
            "border-width : 1px;"
            "border-style : solid;"
            "border-color : {0};"
            "qproperty-alignment: 'AlignVCenter';"
            " qproperty-wordWrap: true;".format(color))

    def enterEvent(self, e):
        self._set_css('#5285a6')

    def leaveEvent (self, e):
        self._set_css()

    def mouseMoveEvent(self, e):
        if e.buttons() != QtCore.Qt.LeftButton:
            return

        mimeData = QtCore.QMimeData()
        mimeData.setText(self.drag_text)

        drag = QtGui.QDrag(self)
        drag.setMimeData(mimeData)
        drag.setHotSpot(e.pos() - self.rect().topLeft())
        drag.exec_(QtCore.Qt.MoveAction)

        super(DragLabel, self).mouseMoveEvent(e)


class Window(MayaQWidgetDockableMixin, QtWidgets.QWidget):

    @property
    def parent_node(self):
        return cmds.ls(self.parent_node_id)[0]

    def __init__(self, parent_node, save_attr_name):
        super(Window, self).__init__()
        self.parent_node_id = cmds.ls(parent_node, uuid=True)[0]
        self.save_attr_name = save_attr_name
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)

        self.setObjectName('DICE')
        self.setWindowTitle('DICE')
        self.job = None

        self.resize(900, 600)
        hbox = QtWidgets.QHBoxLayout()
        hbox.setSpacing(2)
        hbox.setContentsMargins(2, 2, 2, 2)
        self.setLayout(hbox)

        scene = QtWidgets.QGraphicsScene()
        scene.setObjectName('Scene')
        scene.setSceneRect(0, 0, 32000, 32000)
        self.view = view.DiceView(scene, self)

        self.central_layout = QtWidgets.QVBoxLayout()
        hbox.addLayout(self.central_layout, 17)
        hbox.addWidget(self.view, 100)

        run_button = QtWidgets.QPushButton('Run !!!')
        run_button.clicked.connect(self.run)
        run_button.setStyleSheet("background-color: rgb(244, 72, 66);")
        self.central_layout.addWidget(run_button)

        auto_layout_button = QtWidgets.QPushButton('Auto Layout')
        auto_layout_button.clicked.connect(lambda: self.view.auto_layout())
        auto_layout_button.setStyleSheet("background-color: #2b2b2b;")
        self.central_layout.addWidget(auto_layout_button)

        self.name_fld = QtWidgets.QLineEdit('')
        self.central_layout.addWidget(self.name_fld)
        '''
        テキストエリアに日本語を入力中（IME未確定状態）にMayaがクラッシュする場合があった。
        textChanged.connect をやめ、例えば focusOut や エンターキー押下を発火条件にすることで対応
        '''
        self.name_fld.textChanged.connect(self.__create_node_label)

        def _focus_out(event):
            self.__create_node_label()

        def _key_press(event, widget=None):
            QtWidgets.QLineEdit.keyPressEvent(widget, event)
            key = event.key()
            if (key == QtCore.Qt.Key_Enter) or (key == QtCore.Qt.Key_Return):
                self.__create_node_label()

        self.name_fld.focusOutEvent = _focus_out
        self.name_fld.keyPressEvent = functools.partial(_key_press, widget=self.name_fld)

        self.node_list_layout = QtWidgets.QVBoxLayout()
        self.central_layout.addLayout(self.node_list_layout)

        self.central_layout.addStretch(1)

        self.load_data()
        self.__create_node_label()
        self.__create_job()

    def __create_node_label(self):
        for child in self.findChildren(DragLabel):
            self.node_list_layout.removeWidget(child)
            child.setVisible(False)
            child.setParent(None)
            child.deleteLater()
        filter_stg = self.name_fld.text()
        self.__create_original_node_label(filter_stg)
        self.__create_xml_node_label(filter_stg)

    def __create_job(self):
        self.job = cmds.scriptJob(attributeChange=[self.dice_attr_path, self.load_data])

    def __kill_job(self):
        cmds.scriptJob(kill=self.job, force=True)

    def closeEvent(self, e):
        self.__kill_job()

    def __create_original_node_label(self, filter_stg=''):
        cls_ls = ['GetNode', 'SetNode', 'PinNode', 'ScalarNode', 'BooleanNode']
        label_ls = ['GetData', 'SetData', 'Pin', 'Scalar', 'Boolean']

        for _c, _l in zip(cls_ls, label_ls):
            if filter_stg != '' and filter_stg.lower() not in _l.lower():
                continue
            self.__add_drag_label(_l, '{0}::'.format(_c))

    def __create_xml_node_label(self, filter_stg=''):
        for _f in node_xml.get_node_file_list():
            label = node_xml.get_node_label(_f)
            if filter_stg != '' and filter_stg.lower() not in label.lower():
                continue
            file_name, _ = os.path.splitext(os.path.basename(_f))
            self.__add_drag_label(label, 'XmlNode::{0}'.format(file_name))

    def __add_drag_label(self, label, drag_text):
        _button = DragLabel(label, drag_text)
        self.node_list_layout.addWidget(_button)

    def run(self):
        self.__kill_job()
        cmds.undoInfo(openChunk=True)
        _sel_nodes = cmds.ls(sl=True)
        old_exp = cmds.listConnections(self.dice_attr_path, d=True)
        if old_exp is not None:
            cmds.delete(old_exp)

        code_str = common.nodes_recalculation(self.view)
        expy = exprespy.create()
        exprespy.setCode(expy, code_str)
        cmds.addAttr(expy, longName='dice', dt='string')

        self.dice_attr = common.get_save_data_from_scene_all(self.view)
        cmds.connectAttr(self.dice_attr_path, '{0}.dice'.format(expy, self.save_attr_name))
        cmds.select(_sel_nodes)
        cmds.undoInfo(closeChunk=True)
        self.__create_job()

    @property
    def dice_attr_path(self):
        return '{0}.{1}'.format(self.parent_node, self.save_attr_name)

    @property
    def dice_attr(self):
        return cmds.getAttr(self.dice_attr_path)

    @dice_attr.setter
    def dice_attr(self, v):
        cmds.setAttr(self.dice_attr_path, v, type='string')

    def load_data(self):
        self.view.clear()
        # stringはそのままjson形式に出来ないのでstring→dict→jsonとして読み込む必要があるらしい
        if self.dice_attr is None:
            return
        _jd = json.dumps(ast.literal_eval(self.dice_attr))
        json_ = json.loads(_jd)
        common.load_save_data(json_, self.view)


'''
============================================================
---   SHOW WINDOW
============================================================
'''


def maya_version():
    return int(cmds.about(v=True)[:4])


def get_ui(name, weight_type):
    all_ui = {w.objectName(): w for w in QtWidgets.QApplication.allWidgets()}
    for k, v in all_ui.items():
        if name not in k:
            continue
        # 2017だとインスタンスの型をチェックしないと別の物まで入ってきてしまうらしい
        # 2016以前だと比較すると通らなくなる…orz
        if maya_version() >= 2017:
            if v.__class__.__name__ == weight_type:
                return v
        else:
            return v
    return None


def main():

    select_nodes = cmds.ls(sl=True)
    if not select_nodes:
        return

    dice_attr_name = 'dice_graph_data'
    sel_node = select_nodes[0]
    if not cmds.attributeQuery(dice_attr_name,node=sel_node, ex=True):
        cmds.addAttr(sel_node, longName=dice_attr_name, dt='string', m=True, h=True)

    attrs = cmds.listAttr('{0}.{1}'.format(sel_node, dice_attr_name), multi=True)
    if attrs is None:
        cmds.getAttr('{0}.{1}[1]'.format(sel_node, dice_attr_name))

    ui = get_ui('DICE', 'Window')
    if ui is not None:
        ui.close()

    nodeWindow = Window(sel_node, '{0}[1]'.format(dice_attr_name))
    nodeWindow.show()


if __name__ == '__main__':
    main()

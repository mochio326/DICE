# # -*- coding: utf-8 -*-
from mochinode.vendor.Qt import QtCore, QtGui, QtWidgets
import mochinode.view
import uuid
from . import common


class DiceView(mochinode.view.View):
    focus_in = QtCore.Signal()

    def __init__(self, *args, **kwargs):
        self._current_operation_history = 0
        self._operation_history = [None]
        self.drop_node = None
        super(DiceView, self).__init__(*args, **kwargs)
        self.setAcceptDrops(True)

    def dragMoveEvent(self, event):
        pos = self.mapToScene(event.pos())
        self.drop_node.setPos(pos)
        self.drop_node.update()

    def dragLeaveEvent(self, event):
        """ドラッグが抜けた時の処理
        """
        if self.drop_node is not None:
            self.remove_item(self.drop_node)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.setAccepted(True)

            text = event.mimeData().text()
            pos = self.mapToScene(event.pos())

            self.drop_node = common.drop_create_node(text, pos)
            self.add_item(self.drop_node)

            self.drop_node.setOpacity(0.35)
            self.update()

    def dropEvent(self, event):
        event.acceptProposedAction()
        pos = self.mapToScene(event.pos())
        self.drop_node.setPos(pos)
        self.drop_node.setOpacity(1)
        self.node_connect_event(self.drop_node)
        self.create_history()
        self.drop_node = None

    def add_node_on_center(self, node):
        super(DiceView, self).add_node_on_center(node)
        self.node_connect_event(node)

    def node_connect_event(self, node):
        node.port_expanded.connect(self.create_history)
        node.pos_changed.connect(self.create_history)
        node.port_connect_changed.connect(self.create_history)
        node.data_changed.connect(self.create_history)

    def mouseReleaseEvent(self, event):
        super(DiceView, self).mouseReleaseEvent(event)

        if event.button() == QtCore.Qt.RightButton:
            menu = QtWidgets.QMenu()
            save = menu.addAction('save')
            load = menu.addAction('load')
            selected_action = menu.exec_(event.globalPos())

            if selected_action == save:
                common.scene_save(self)
            if selected_action == load:
                common.scene_load(self)

    def auto_layout(self):
        super(DiceView, self).auto_layout()
        self.create_history()

    def _delete(self):
        super(DiceView, self)._delete()
        self.create_history()

    def _copy(self):
        self._clipboard = {}
        self._paste_offset = 0
        selected_nodes = self.scene().selectedItems()
        related_lines = common.get_lines_related_with_node(selected_nodes, self)
        self._clipboard = common.get_save_data(selected_nodes, related_lines)

    def _paste(self):
        if self._clipboard is None:
            return
        self._paste_offset = self._paste_offset + 1

        # 貼り付け前に保存データ内のノードIDを変更することでシーン内のIDの重複を避ける
        id_change_dict = {}
        for _n in self._clipboard['node']:
            new_id = str(uuid.uuid4())
            id_change_dict[_n['i']] = new_id
            _n['i'] = new_id
            _n['z'] = _n['z'] + self._paste_offset
            _n['x'] = _n['x'] + self._paste_offset * 10
            _n['y'] = _n['y'] + self._paste_offset * 10
        for _l in self._clipboard['line']:
            if id_change_dict.get(_l['s']['i']) is not None:
                _l['s']['i'] = id_change_dict.get(_l['s']['i'])
            if id_change_dict.get(_l['t']['i']) is not None:
                _l['t']['i'] = id_change_dict.get(_l['t']['i'])

        nodes = common.load_save_data(self._clipboard, self)
        self.scene().clearSelection()
        for _n in nodes:
            _n.setSelected(True)
        self.scene().update()

    def _cut(self):
        pass

    def _undo(self):
        self._undo_redo_base('undo')

    def _redo(self):
        self._undo_redo_base('redo')

    def create_history(self):
        data = common.get_save_data_from_scene_all(self)
        # Undo Redo用の操作
        if self._current_operation_history > 0:
            del self._operation_history[0:self._current_operation_history]
        self._operation_history.insert(0, data)
        self._current_operation_history = 0

    def _undo_redo_base(self, type_):
        _add = 1 if type_ == 'undo' else -1
        if self._current_operation_history >= len(self._operation_history) - _add:
            return
        if self._current_operation_history + _add < 0:
            return
        self._current_operation_history = self._current_operation_history + _add
        data = self._operation_history[self._current_operation_history]
        self.clear()
        common.load_save_data(data, self)

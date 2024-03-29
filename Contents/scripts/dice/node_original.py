# # -*- coding: utf-8 -*-
from mochinode.vendor.Qt import QtCore, QtGui, QtWidgets
from mochinode import Node, Port
from maya import cmds
from .port import PortColor
from .port import Port


def get_attr_value_type(attr_path):
    """
    Attribute名から値のタイプを調べる
    ついでにここにあるものがDICEがサポートしてるアトリビュートになる
    :param name:
    :return:
    """
    _type = cmds.getAttr(attr_path, type=True)

    if _type == 'matrix':
        return 'Matrix4x4'
    elif _type == 'double3':
        # _attr_name = attr_path.split('.')[1]
        # if _attr_name == 'r' or _attr_name == 'rotate':
        #     return 'Rotation'
        return 'Vector3d'
    elif _type == 'bool':
        return 'Boolean'
    elif _type == 'string':
        return 'Str'
    elif _type in ['doubleLinear', 'doubleAngle', 'short', 'long', 'enum', 'double', 'float', 'time', 'distance',
                   'angle']:
        return 'Scalar'
    elif _type in ['short2', 'short3', 'long2', 'long3', 'double2', 'double3', 'double4', 'float2', 'float3']:
        return 'Array'

    # Polymorphic = QtCore.Qt.gray

    return None


class DiceNodeBase(Node):
    # ポートの接続状態変化で発動
    data_changed = QtCore.Signal()

    @classmethod
    def create_node_for_save_data(cls, save_data):
        n = cls()
        n.load_data(save_data)
        return n

    def __init__(self, *args, **kwargs):
        self.serial_number = 0
        # フリータイプのポートがノードにある場合に接続可能なタイプを保持
        self.free_port_can_connection_types = None
        super(DiceNodeBase, self).__init__(*args, **kwargs)
        self.port_cls = Port

    def recalculation(self):
        """
        ノード内でexprespyコードを生成する関数
        :return: exprespy code [string]
        """
        pass

    def update_recalculation_weight(self):
        _source_nodes = self.get_source_nodes()
        self.recalculation_weight = len(_source_nodes)

    def cleanup_free_port(self):
        # フリーポートで定義されているものすべてのコネクションがなくなっている場合
        # ポートを初期設定に戻す
        _free_port_connect_line_count = 0
        for _p in self.children_ports_all_iter():
            if _p.default_value_type == self.port_cls.free_type_port:
                _free_port_connect_line_count += len(_p.lines)

        if _free_port_connect_line_count > 0:
            return

        for _p in self.children_ports_all_iter():
            if _p.default_value_type == self.port_cls.free_type_port:
                _p.value_type = self.port_cls.free_type_port
                _p.color = getattr(PortColor(), _p.value_type)
                _p.change_to_basic_color()
            print _p.value_type, _p.default_value_type

    def load_data(self, save_data):
        """
        辞書データからノードを再構築する
        :param save_data: 辞書データ
        :return: None
        """
        self.id = save_data['i']
        self.setZValue(save_data['z'])
        self.setX(save_data['x'])
        self.setY(save_data['y'])

        for _p in self.children_ports_all_iter():
            _p.children_port_expand = save_data['p'][_p.name]['e']
            _p.value = save_data['p'][_p.name]['v']

            _dvt = 'default_value_type'
            if hasattr(_p, _dvt):
                if getattr(_p, _dvt) == Port.free_type_port:
                    _value_type = save_data['p'][_p.name]['t']
                    _p.value_type = _value_type
                    _p.color = getattr(PortColor(), _value_type)
                    _p.change_to_basic_color()

        self.deploying_port()
        self.cleanup_free_port()
        self.update()

    @property
    def save_data(self):
        """
        再構築に必要なデータを戻す
        :return: dict
        """
        data = {}
        data['c'] = self.__class__.__name__
        data['i'] = self.id
        data['n'] = self.name
        data['z'] = self.zValue()
        data['x'] = self.x()
        data['y'] = self.y()
        data['p'] = {}
        for _p in self.children_ports_all_iter():
            data['p'][_p.name] = {}
            data['p'][_p.name]['e'] = _p.children_port_expand
            data['p'][_p.name]['v'] = _p.value
            # ポートにDefaultタイプの属性がある場合はセーブデータに記録し復元する
            _dvt = 'default_value_type'
            if hasattr(_p, _dvt):
                if getattr(_p, _dvt) == Port.free_type_port:
                    data['p'][_p.name]['t'] = _p.value_type
        return data


class GetSetBaseNode(DiceNodeBase):

    @property
    def top_level_widget(self):
        return self.scene().views()[0].parent()

    @property
    def save_data(self):
        data = super(GetSetBaseNode, self).save_data
        data['at'] = self.attr_name
        data['tn'] = self.target_node_id
        return data

    @property
    def target_attr_full_path(self):
        return self._get_attr_path(self.target_node_id, self.attr_name)

    def _get_attr_path(self, node, attr, error_returns_none=True):
        #
        if '' == node:
            node = self.top_level_widget.parent_node
        _target = cmds.ls(node)
        if not _target:
            if error_returns_none:
                return None
            return '???.{0}'.format(attr)
        else:
            node = _target[0]

        if not cmds.attributeQuery(attr, node=node, ex=True):
            if error_returns_none:
                return None

        return '{0}.{1}'.format(node, attr)

    def load_data(self, save_data):
        self.attr_name = save_data['at']
        self.target_node_id = save_data['tn']
        super(GetSetBaseNode, self).load_data(save_data)
        self.update_label()

    def __init__(self, name='', label='node'):
        self.target_node_id = ''
        self.attr_name = ''
        self.error = False
        super(GetSetBaseNode, self).__init__(name=name, label=label)
        self.error_color()

    def error_color(self):
        self.label_bg_color_l = QtCore.Qt.red
        self.label_bg_color_r = QtCore.Qt.red
        self.bg_color = QtGui.QColor(180, 40, 40)

    def init_color(self):
        self.label_bg_color_l = QtGui.QColor(66, 135, 245)
        self.label_bg_color_r = self.init_bg_color
        self.bg_color = self.init_bg_color

    def check_error(self):
        if self.target_attr_full_path is None:
            self.error_color()
            self.error = True
        else:
            self.init_color()
            self.error = False
        self.update_label()
        self.update()

    def update_label(self):
        if self.error:
            self.label = self.default_node_label
            self.port[self.default_port_label].label = self.default_port_label
        else:
            _n = self.target_node_id
            if _n == '':
                _n = 'Self'
            else:
                _n = cmds.ls(_n, sn=True)[0]
            _prifix = self.default_node_label.split(' ')[0]
            self.label = _prifix + ' ' + _n
            self.port[self.default_port_label].label = self.attr_name
        self.update()

    def mouseDoubleClickEvent(self, event):
        # pos = event.lastScreenPos()
        target_node_id, attr_name = self.input_target_attr_path()
        _full_path = self._get_attr_path(target_node_id, attr_name)
        if _full_path is None:
            return

        _value_type = get_attr_value_type(_full_path)
        if _value_type is None:
            return

        # ポートが既に接続済みだった場合は同じ値のタイプ同士の変更のみ許可
        if len(self.port['Value'].lines) != 0:
            if self.port['Value'].value_type != _value_type:
                return

        self.attr_name = attr_name
        if target_node_id == self.top_level_widget.parent_node_id:
            target_node_id = ''
        self.target_node_id = target_node_id

        self.port['Value'].value_type = _value_type
        self.port['Value'].color = getattr(PortColor(), _value_type)
        self.port['Value'].change_to_basic_color()

        self.check_error()
        self.data_changed.emit()

    def input_target_attr_path(self):
        if self.target_node_id != '' and self.attr_name != '':
            attr_full_path = self._get_attr_path(self.target_node_id, self.attr_name, False)
        elif self.target_node_id == '' and self.attr_name != '':
            attr_full_path = '.{0}'.format(self.attr_name)
        else:
            attr_full_path = ''

        text, ok = QtWidgets.QInputDialog.getText(self.scene().views()[0], self.__class__.__name__,
                                                  """Please enter the address of acquisition data"""
                                                  , text=attr_full_path)
        if not ok:
            return None, None

        if not text.split('.'):
            return None, None

        target_node, attr_name = text.split('.')

        # if self.target_attr_full_path is None:
        #     return None, None

        if target_node != '':
            # uuidベースで保持する
            target_node = cmds.ls(target_node, uuid=True)
            if not target_node:
                return None, None
            target_node = target_node[0]

        return target_node, attr_name


class GetNode(GetSetBaseNode):

    def __init__(self, *args, **kwargs):
        self.default_node_label = 'Get Data'
        self.default_port_label = 'Value'
        super(GetNode, self).__init__(name='GetNode', label=self.default_node_label)
        self.add_port(label=self.default_port_label, port_type='out',
                      color=getattr(PortColor(), Port.free_type_port),
                      value_type=Port.free_type_port, value=None)

    def recalculation(self):
        code_str = ''
        for _p in self.ports:
            if not _p.lines:
                continue
            node_id = 'n' + str(_p.node.serial_number)
            code_str = code_str + '{0}_{1} = {2}'.format(node_id, _p.name, self.target_attr_full_path)
        return code_str


class SetNode(GetSetBaseNode):
    def __init__(self, *args, **kwargs):
        self.default_node_label = 'Set Data'
        self.default_port_label = 'Value'
        super(SetNode, self).__init__(name='SetNode', label=self.default_node_label)
        self.add_port(label=self.default_port_label, port_type='in',
                      color=getattr(PortColor(), Port.free_type_port),
                      value_type=Port.free_type_port, value=None)

    def recalculation(self):
        code_str = ''
        for _p in self.ports:
            if not _p.lines:
                continue
            source_port = _p.lines[0].source
            node_id = 'n' + str(source_port.node.serial_number)
            in_value = node_id + '_' + source_port.name

            code_str = code_str + '{0} = {1}'.format(self.target_attr_full_path, in_value)
        return code_str


class PinNode(DiceNodeBase):

    def __init__(self, *args, **kwargs):
        super(PinNode, self).__init__(name='Pin', label=None, width=40)
        _t = Port.free_type_port
        _p = self.add_port(port_type='in', color=getattr(PortColor(), _t), value_type=_t, label=None, value=0)
        _p.name = 'in'
        _p = self.add_port(port_type='out', color=getattr(PortColor(), _t), value_type=_t, label=None, value=0)
        _p.name = 'out'

    def recalculation(self):
        code_str = ''
        for _p in self.in_ports:
            if not _p.lines:
                # ポートにラインがない場合は直値
                in_value = str(_p.value)
            else:
                source_port = _p.lines[0].source
                node_id = 'n' + str(source_port.node.serial_number)
                in_value = node_id + '_' + source_port.name

        for _p in self.out_ports:
            if not _p.lines:
                continue
            code_str = 'n{0}_out = {1}'.format(str(self.serial_number), in_value)

        return code_str

    def deploying_port(self):
        # ポートの入出力はそれぞれ１つ前提なので
        # 同じ高さに入出力ポートが配置されるように改造
        _port_y = self.port_init_y + 5
        for _p in self.ports:
            _p.setY(_port_y)
            _p.update_connect_line_pos()
            _p.deploying_port()
        self.height = _port_y + _p.height_space


class SingleValueNodeBase(DiceNodeBase):

    @property
    def save_data(self):
        data = super(SingleValueNodeBase, self).save_data
        data['v'] = self.value
        return data

    def __init__(self, name='', label='True'):
        self.value = ''
        super(SingleValueNodeBase, self).__init__(name=name, label=label)

    def load_data(self, save_data):
        self.value = save_data['v']
        super(SingleValueNodeBase, self).load_data(save_data)
        self.update_label()

    def update_label(self):
        self.label = str(self.value)
        self.update()

    def recalculation(self):
        code_str = ''
        for _p in self.out_ports:
            if not _p.lines:
                continue
            node_id = 'n' + str(_p.node.serial_number)
            code_str = code_str + '{0}_{1} = {2}'.format(node_id, _p.name, self.value)
        return code_str

    def mouseDoubleClickEvent(self, event):
        value, ok = self._input_dialog()
        if not ok:
            return None
        self.value = value
        self.update_label()
        self.data_changed.emit()


class ScalarNode(SingleValueNodeBase):

    def __init__(self, name='', label='0'):
        super(ScalarNode, self).__init__(name=name, label=label)
        self.value = 0
        _t = 'Scalar'
        _p = self.add_port(port_type='out', color=getattr(PortColor(), _t), value_type=_t, label='Result',
                           value=self.value)

    def _input_dialog(self):
        return QtWidgets.QInputDialog.getDouble(self.scene().views()[0], 'Scalar', '', self.value)


class BooleanNode(SingleValueNodeBase):

    def __init__(self, name='', label='True'):
        super(BooleanNode, self).__init__(name=name, label=label)
        self.value = 'True'
        _t = 'Boolean'
        _p = self.add_port(port_type='out', color=getattr(PortColor(), _t), value_type=_t, label='Result', value=10)

    def _input_dialog(self):
        items = ['True', 'False']
        return QtWidgets.QInputDialog.getItem(self.scene().views()[0], 'Boolean', "Value:", items,
                                              items.index(self.value), False)

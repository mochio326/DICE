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
        return 'Bool'
    elif _type == 'string':
        return 'Str'
    elif _type in ['doubleLinear', 'doubleAngle', 'short', 'long', 'enum', 'double', 'float', 'time', 'distance',
                   'angle']:
        return 'Scalar'
    elif _type in ['short2', 'short3', 'long2', 'long3', 'double2', 'double3', 'double4', 'float2', 'float3']:
        return 'Array'

    Scalar = QtGui.QColor(79, 231, 79)
    Polymorphic = QtCore.Qt.gray

    return None


def input_target_attr_path(title, def_value, node):
    text, ok = QtWidgets.QInputDialog.getText(node.scene().views()[0], title,
                                              """Please enter the address of acquisition data"""
                                              , text=def_value)
    if not ok:
        return None

    parent_node = node.top_level_widget.parent_node

    sp = text.split('.')
    if len(sp) != 2:
        return None

    node_name = sp[0]
    if node_name == '':
        node_name = parent_node
    attr_name = sp[1]

    if len(cmds.ls(node_name)) != 1:
        return None

    if not cmds.attributeQuery(attr_name, node=node_name, ex=True):
        return None

    attr_path = '{0}.{1}'.format(node_name, attr_name)

    q = get_attr_value_type(attr_path)
    if q is None:
        return None

    return text


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
        super(DiceNodeBase, self).__init__(*args, **kwargs)
        self.port_cls = Port
        self.serial_number = 0

    def recalculation(self):
        """
        ノード内でexprespyコードを生成する関数
        :return: exprespy code [string]
        """
        pass

    def update_recalculation_weight(self):
        _source_nodes = self.get_source_nodes()
        self.recalculation_weight = len(_source_nodes)

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
        data['at'] = self.attr_path
        return data

    @property
    def true_attr_path(self):
        if '' == self.attr_path.split('.')[0]:
            return self.attr_path.replace('.', self.top_level_widget.parent_node + '.')
        return self.attr_path

    def load_data(self, save_data):
        self.attr_path = save_data['at']
        super(GetSetBaseNode, self).load_data(save_data)
        self.update_label()

    def __init__(self, name='', label='node'):
        self.serial_number = 0
        self.attr_path = ''
        super(GetSetBaseNode, self).__init__(name=name, label=label)

    def mouseDoubleClickEvent(self, event):
        pos = event.lastScreenPos()
        text = input_target_attr_path(self.__class__.__name__, self.attr_path, self)
        if text is None:
            return
        self.attr_path = text

        _attr_name = self.attr_path.split('.')[1]
        _value_type = get_attr_value_type(self.attr_path)
        self.port['Value'].value_type = _value_type
        self.port['Value'].color = getattr(PortColor(), _value_type)
        self.port['Value'].change_to_basic_color()

        self.update_label()
        self.data_changed.emit()

    def update_label(self):
        if self.attr_path == '':
            self.label = self.default_node_label
            self.port[self.default_port_label].label = self.default_port_label
        else:
            _n, _a = self.attr_path.split('.')
            if _n == '':
                _n = 'Self'
            _prifix = self.default_node_label.split(' ')[0]
            self.label = _prifix + ' ' + _n
            self.port[self.default_port_label].label = _a
        self.update()


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
            if len(_p.lines) == 0:
                continue
            node_id = 'n' + str(_p.node.serial_number)
            code_str = code_str + '{0}_{1} = {2}'.format(node_id, _p.name, self.true_attr_path)
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
            if len(_p.lines) == 0:
                continue
            source_port = _p.lines[0].source
            node_id = 'n' + str(source_port.node.serial_number)
            in_value = node_id + '_' + source_port.name

            code_str = code_str + '{0} = {1}'.format(self.true_attr_path, in_value)
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
        self_node_id = 'n' + self.id.replace('-', '')
        for _p in self.in_ports:
            if len(_p.lines) > 0:
                source_port = _p.lines[0].source
                node_id = 'n' + source_port.node.id.replace('-', '')
                in_value = node_id + '_' + source_port.name
            else:
                # ポートにラインがない場合は直値
                in_value = str(_p.value)

        for _p in self.out_ports:
            if len(_p.lines) == 0:
                continue
            code_str = '{0}_out = {1}'.format(self_node_id, in_value)

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


class ScalarNode(DiceNodeBase):

    @property
    def save_data(self):
        data = super(ScalarNode, self).save_data
        data['v'] = self.value
        return data

    def load_data(self, save_data):
        self.value = save_data['v']
        super(ScalarNode, self).load_data(save_data)
        self.update_label()

    def __init__(self, name='', label='0'):
        self.serial_number = 0
        self.value = 10
        super(ScalarNode, self).__init__(name=name, label=label)
        _t = 'Scalar'
        _p = self.add_port(port_type='out', color=getattr(PortColor(), _t), value_type=_t, label='value', value=10)

    def mouseDoubleClickEvent(self, event):
        pos = event.lastScreenPos()
        value, ok = QtWidgets.QInputDialog.getDouble(self.scene().views()[0], 'Scalar', '')
        if not ok:
            return None
        self.value = value
        self.update_label()
        self.data_changed.emit()

    def update_label(self):
        self.label = str(self.value)
        self.update()

    def recalculation(self):
        code_str = ''
        for _p in self.ports:
            if len(_p.lines) == 0:
                continue
            node_id = 'n' + str(_p.node.serial_number)
            code_str = code_str + '{0}_{1} = {2}'.format(node_id, _p.name, self.value)
        return code_str

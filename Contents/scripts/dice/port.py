# # -*- coding: utf-8 -*-
from mochinode.vendor.Qt import QtCore, QtGui, QtWidgets
from mochinode.port import Port as OriginalPort


class PortColor(object):
    Scalar = QtGui.QColor(79, 231, 79)
    Bool = QtGui.QColor(231, 129, 0)
    Str = QtGui.QColor(0, 0, 255)
    Polymorphic = QtCore.Qt.gray
    Vector3d = QtGui.QColor(201, 201, 26)
    # Rotation = QtGui.QColor(129, 231, 231)
    Matrix4x4 = QtGui.QColor(129, 172, 172)
    Array = QtGui.QColor(96, 66, 245)

    def __setattr__(self, *_):
        pass


class Port(OriginalPort):
    free_type_port = 'Polymorphic'

    def __init__(self, *args, **kwargs):
        self.default_value_type = kwargs['value_type']
        super(Port, self).__init__(*args, **kwargs)

    def can_connection(self, port):

        # フリーポート同士が連結できると後にタイプが変更される際に
        # 端までタイプをチェック、伝搬させないといけないので面倒なので現状はつなげないようにしとく
        if self.value_type == self.free_type_port and port.value_type == self.free_type_port:
            return False

        # もしフリータイプのポートだった場合に接続が許可されるようにタイプを
        # 一時的に偽装する
        _self_changed = False
        _port_changed = False
        if self.value_type == self.free_type_port:
            self.value_type = port.value_type
            _self_changed = True
        if port.value_type == self.free_type_port:
            port.value_type = self.value_type
            _port_changed = True

        v = super(Port, self).can_connection(port)

        if _self_changed:
            self.value_type = self.default_value_type
        if _port_changed:
            port.value_type = port.default_value_type
        return v

    def connect_line(self, line_, not_del=False):
        super(Port, self).connect_line(line_, not_del)

        if line_.target is None or line_.source is None:
            return

        # フリータイプポートに接続した場合にノード内のフリーポートのタイプを変更しておく
        _target_port = None
        _source_port = None

        if line_.target.value_type == self.free_type_port:
            _target_port = line_.target
            _source_port = line_.source
        elif line_.source.value_type == self.free_type_port:
            _target_port = line_.source
            _source_port = line_.target

        if _target_port is not None:
            for _p in _target_port.node.ports:
                if _p.value_type != self.free_type_port:
                    continue
                _p.value_type = _source_port.value_type
                _p.color = getattr(PortColor(), _p.value_type)
                _p.change_to_basic_color()

        line_.color = getattr(PortColor(), self.value_type)
        line_.change_to_basic_color()
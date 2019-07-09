# # -*- coding: utf-8 -*-
import json
import os
from mochinode.vendor.Qt import QtCore, QtGui, QtWidgets
from mochinode import Node, Line
from . import node_original
from . import node_xml


def get_line_save_data(l):
    # if l.source is None or l.target is None:
    #     return None
    data = {}
    # source
    data['s'] = {}
    data['s']['i'] = l.source.node.id  # node_id
    data['s']['p'] = l.source.name  # port_name
    # target
    data['t'] = {}
    data['t']['i'] = l.target.node.id  # node_id
    data['t']['p'] = l.target.name  # port_name
    return data


def scene_save(view):
    save_data = get_save_data_from_scene_all(view)
    not_escape_json_dump(r'c:\temp\node_tool.json', save_data)


def get_save_data_from_scene_all(view):
    nodes = [_n for _n in Node.scene_nodes_iter(view)]
    lines = [_l for _l in Line.scene_lines_iter(view)]
    return get_save_data(nodes, lines)


def get_save_data(nodes, lines):
    save_data = {}
    save_data['node'] = [_n.save_data for _n in nodes]
    save_data['line'] = [get_line_save_data(_l) for _l in lines]
    return save_data


def nodes_recalculation(view):
    recalculation_nodes = []

    serial_number = 0
    for _n in Node.scene_nodes_iter(view):
        _n.serial_number = serial_number
        serial_number = serial_number + 1
        _n.update_recalculation_weight()
        # if _n.forced_recalculation:
        recalculation_nodes.append(_n)

    # recalculation_weightを基準に並び替え
    recalculation_nodes = sorted(recalculation_nodes, key=lambda n: n.recalculation_weight)

    code_list = []
    for i, _n in enumerate(recalculation_nodes):
        # _n.propagation_port_value()
        _s = _n.recalculation()
        code_list.append(_s)
        _n.update()

    # 空白行が出てくるので最後に行間詰める
    exp_code = ''
    for _code in code_list:
        for _c in _code.split('\n'):
            if _c.lstrip() == '':
                continue
            exp_code = exp_code + _c + '\n'
    return exp_code


def get_node_class(class_name):
    if hasattr(node_original, class_name):
        cls = getattr(node_original, class_name)
    if hasattr(node_xml, class_name):
        cls = getattr(node_xml, class_name)
    return cls


def drop_create_node(text, pos):
    class_name, node_name = text.split('::')
    cls = get_node_class(class_name)
    n = cls(name=node_name)
    n.setPos(pos)
    return n


def load_save_data(data, view):
    if data is None:
        return
    nodes = []
    for _node_data in data['node']:
        # module内からセーブデータ内に保持していた指定クラスがあるか探す
        _class_name = _node_data['c']
        cls = get_node_class(_class_name)
        n = cls.create_node_for_save_data(_node_data)
        view.add_item(n)
        view.node_connect_event(n)
        nodes.append(n)

    for _l in data['line']:
        line_connect_for_save_data(_l, view)

    for _n in nodes:
        for _p in _n.children_ports_all_iter():
            _p.create_temp_line()

    check_all_nodes_error(view)

    return nodes


def check_all_nodes_error(view):
    # エラーがあればノードの色を変化させる
    for n in Node.scene_nodes_iter(view):
        if hasattr(n, 'check_error'):
            n.check_error()


def scene_load(view):
    data = not_escape_json_load(r'c:\temp\node_tool.json')
    view.clear()
    load_save_data(data, view)
    view.scene().update()


def line_connect_for_save_data(line_data, view):
    for _n in Node.scene_nodes_iter(view):
        if line_data['s']['i'] == _n.id:
            source = _n.port[line_data['s']['p']]
        if line_data['t']['i'] == _n.id:
            target = _n.port[line_data['t']['p']]
    new_line = Line(QtCore.QPointF(0, 0), QtCore.QPointF(0, 0), target.color)
    source.connect_line(new_line)
    target.connect_line(new_line)
    view.add_item(new_line)


def get_lines_related_with_node(nodes, view):
    # 指定ノードに関連するラインをシーン内から取得
    nodes_id = [_n.id for _n in nodes]
    related_lines = []
    for _l in Line.scene_lines_iter(view):
        if _l.source.node.id in nodes_id and _l.target.node.id in nodes_id:
            related_lines.append(_l)
    return related_lines


def not_escape_json_dump(path, data):
    # http://qiita.com/tadokoro/items/131268c9a0fd1cf85bf4
    # 日本語をエスケープさせずにjsonを読み書きする
    # text = json.dumps(data, sort_keys=True, ensure_ascii=False, indent=2)

    # 改行無し空白無しにすることで極力容量を減らす
    text = json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    with open(path, 'w') as fh:
        fh.write(text.encode('utf-8'))


def not_escape_json_load(path):
    if os.path.isfile(path) is False:
        return None
    with open(path) as fh:
        data = json.loads(fh.read(), "utf-8")
    return data

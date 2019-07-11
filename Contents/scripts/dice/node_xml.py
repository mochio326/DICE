# # -*- coding: utf-8 -*-
import xml.etree.ElementTree as ET
import re
import os
import glob
from .port import PortColor
from .port import Port
from .node_original import DiceNodeBase


def get_node_file_list():
    path = get_xml_dir()
    for f in glob.glob(r'{}\*.xml'.format(path)):
        yield f

def get_node_label(file):
    tree = ET.parse(file)
    return tree._root.attrib['Label']


def get_xml_dir():
    base = os.path.dirname(os.path.abspath(__file__))
    path = os.path.normpath(os.path.join(base, 'node_db'))
    return path


class XmlNode(DiceNodeBase):

    @classmethod
    def create_node_for_save_data(cls, save_data):
        n = cls(save_data['n'])
        n.load_data(save_data)
        return n

    def __init__(self, name=None):
        tree = ET.parse(r'{}\{}.xml'.format(get_xml_dir(), name))
        label = tree._root.attrib['Label']
        width = tree._root.attrib.get('Width', 140)
        super(XmlNode, self).__init__(name=name, label=label, width=int(width))

        # self.code = format_code(tree.find('Code').text)
        self.code = tree.find('Code')
        p = tree.findall('Port')
        create_ports_for_xml(p, self)
        self.deploying_port()

    def recalculation(self):
        # ノードからpython実行用のコードに変換
        code_str = format_code(self.code.text) + '\n'
        # まずはoutポートでラインが接続されているもののxml内のコードを収集
        for _p in self.out_ports:
            if not _p.lines:
                continue
            _out_code = self.code.findtext(_p.name)
            if _out_code != '':
                code_str = format_code(_out_code) + '\n'

        # コード内の{{}}で囲まれているポート名をexprespy内の変数に置き換える
        for _p in self.out_ports:
            node_id = 'n{0}_{1}'.format(_p.node.serial_number, _p.name)
            code_str = code_str.replace('{{' + _p.name + '}}', node_id)

        for _p in self.in_ports:
            if not _p.lines:
                # ポートにラインがない場合はデフォルト値
                replace_str = str(_p.value)
            else:
                source_port = _p.lines[0].source
                node_id = 'n' + str(source_port.node.serial_number)
                replace_str = node_id + '_' + source_port.name
            code_str = code_str.replace('{{' + _p.name + '}}', replace_str)
        return code_str


# xmlに記述された実行コードの先頭の空白を削除する
def format_code(code):
    code = code.split('\n')
    match_end = None
    for i, c in enumerate(code):
        if c.lstrip() == '':
            continue
        m = re.match('^ +', c)
        if match_end is None:
            if m is None:
                match_end = 0
            else:
                match_end = m.end()
        if len(c) > match_end:
            code[i] = c[match_end:]

    return '\n'.join(code)


def create_ports_for_xml(ports_xml, parent):
    port_color = PortColor()
    for _p in ports_xml:
        _value_type = _p.attrib.get('ValueType')
        _def_value = _p.attrib.get('DefaultValue')

        if isinstance(parent, XmlNode):
            pp = parent.add_port(label=_p.attrib.get('Label'), port_type=_p.attrib.get('Type'),
                                 color=getattr(port_color, _value_type),
                                 value_type=_value_type, value=_def_value)
        else:
            pp = Port(parent=parent, label=_p.attrib.get('Label'), port_type=_p.attrib.get('Type'),
                      color=getattr(port_color, _value_type), value_type=_value_type,
                      value=_def_value)
        _p_find = _p.findall('Port')
        create_ports_for_xml(_p_find, pp)

# DICE [Var.0.1]

SoftimageのICEをリスペクトして作成したノードエディタ

## インストール

1. Clone or download > Download ZIP からZIPファイルをダウンロードしてください。

2. 解凍したDICEフォルダを `C:\Program Files\Autodesk\ApplicationPlugins` へコピーしてください。  
MayaをCドライブ以外にインストールしている場合でもDICEフォルダは `C:\Program Files\Autodesk\ApplicationPlugins` に置く必要があるようです。  
判断に迷ったらボーナスツールと同じ場所に入れて下さい。

+ ApplicationPluginsフォルダが存在しない場合は作成してください。

+ 複数バージョンのMayaに対応しています。2014以降のバージョンでは自動的に認識されツールが使える状態になります。

+ 不要になった場合はフォルダを削除してください。

+ バージョンアップの際は上書きではなく、一度DICEフォルダを削除すると安全です。


## 使い方

ノードを選択して以下のコードを実行するとGUIが表示される

```python
import dice
dice.main()   
```

Runボタンを押すとノードグラフからexprespyのコードが生成される


## ライセンス

[MIT](https://github.com/mochio326/SiShelf/blob/master/LICENSE)

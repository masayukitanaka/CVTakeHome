
# 実行方法
$ python exec.py <PDFファイル>

# ファイルの出力先
デフォルトで output/に出力する
引数で変更できる


# 処理内容
exec.py は以下の3つのプログラムを順番に動かします。
生成されたファイルが以降のステップで使えるようにしてください.

## (1)PDFをマークダウンに変換
PDFファイルをマークダウンに変更します。
pdf_to_markdown_converter.py を使ってください。

## (2) 1のマークダウンから、ポリシーの要点を出力
parse_insurance_markdown.py を使ってください。

## (3) 1のマークダウンから、追加情報の出力
dynamic_insurance_analyzer.py を使ってください。


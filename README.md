# NPB歴代オーダー編成

実在するNPB選手・OBから好きな選手を選び、自由にオーダーを編成できるWebサイトです。

## 公開サイト

https://saca0808.github.io/npb-order-builder/

## 主な機能

- 現役・OBを含む選手検索
- 球団・守備位置・生年月日による絞り込み
- 打順と守備位置の設定
- DH制・大谷ルール対応
- 投手枠への選手登録
- NPB通算・MLB通算・日米通算成績の表示
- オーダーの保存
- 画像保存
- Xへの共有
- スマートフォン対応

## 自動更新する情報

- NPB現役選手の在籍情報
- 現役・OB判定
- 支配下・育成登録
- 球団公式の登録ポジション
- 一軍・二軍で出場した守備位置
- 生年月日・投打・読み仮名
- NPB通算打撃・投手成績
- MLB経験者のMLB通算成績
- 新しく公式名簿へ追加された選手

GitHub Actionsにより、毎日06:20ごろ（日本時間）に選手情報を更新し、検証後にGitHub Pagesへ公開します。

## 手動更新と障害確認

- 手動更新：Actions → Daily player data update → Run workflow
- 更新失敗：Actionsの実行履歴から赤くなっている処理を確認
- 正常終了：緑色のチェックを確認

## 構成

- `dist/`：GitHub Pagesで公開するサイト
- `automation/update_daily.py`：NPB選手情報の更新
- `automation/update_mlb.py`：MLB通算成績の更新
- `automation/validate_database.py`：公開前のデータ検証
- `.github/workflows/daily-player-update.yml`：毎日の更新とGitHub Pagesへの公開

## 注意

外部サイトのメンテナンスや仕様変更によって、自動更新に失敗する場合があります。月に一度程度、GitHub Actionsの実行結果を確認してください。

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
- `automation/review_ob_pitcher_positions.py`：OB投手の未確認ポジションを表示から保留（自動更新時にも実行）
- `automation/merge_fielding_evidence.py`：年度別守備成績CSVの刺殺・補殺・失策から実守備を裏付けた位置のみ復元
- `data/player_fielding.zip`：1936～2025年（公式戦のなかった1945年を除く）の年度別守備成績CSV、全89年分
- `automation/update_mlb.py`：MLB通算成績の更新
- `automation/validate_database.py`：公開前のデータ検証
- `.github/workflows/daily-player-update.yml`：毎日の更新とGitHub Pagesへの公開

## 注意

外部サイトのメンテナンスや仕様変更によって、自動更新に失敗する場合があります。月に一度程度、GitHub Actionsの実行結果を確認してください。

## OB投手の出場ポジションの確認方針

過去の守備出場集計には、試合前の偵察要員として書かれ、実際の守備には就かなかった投手が含まれ得ます。[スタメンデータベース](https://sta-men.jp/)の灰色表示や[スタメンアーカイブ](https://npbstk.web.fc2.com/order/)の交代注記を確認の手掛かりとし、スタメンだけで生涯の守備出場を断定しません。

公開データは保守的な暫定表示です。OBで投手を含む選手の投手以外の位置については、通算安打数に関係なく、守備機会（刺殺・補殺・失策）が記録された位置と個別に確認した転向のみ表示します。それ以外は `unverified_positions` に保管して検索・出場ポジションの表示から外します。これは「偵察要員だった」と認定した意味ではありません。守備機会がゼロでも実際に守ったケースや、古い記録で守備機会自体が未記載のケースがあり得ます。後日の試合記録・交代記録で裏付けが取れたら選手IDごとに修正します。

確認した修正が翌日の更新で戻らないよう、ワークフローが更新後に審査処理と守備記録の再照合を実行し、公開前に検証します。過去の値は削除せず `unverified_positions` に残るので再確認できます。

提供された全年度ZIPを `data/player_fielding.zip` に置き、リポジトリのルートで `python automation/merge_fielding_evidence.py data/player_fielding.zip` を実行します。選手IDと守備位置を照合し、公式戦で刺殺・補殺・失策の合計が1以上あるものだけを `unverified_positions` から出場ポジションへ戻します。守備機会が0でも守った可能性はあるため、その位置は「偵察要員と確定」と扱わず確認中に残します。CSVの取得失敗や列の不一致は無理に推測せず処理を止めます。

「Season Fielding Stats EN.csv」のように一覧画面から100行だけ書き出されたCSVは全件照合に使えません。日本語見出しと春秋シーズンにも対応し、十分な年度・選手数がない場合はデータベースを変更せず停止します。一部だけを個別に照合する場合は `--allow-partial` を指定し、全件確認済みとは表記しないでください。

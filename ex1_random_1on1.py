from pokepy.pokemon import *

# ライブラリの初期化
Pokemon.init()

# Battleクラスのインスタンスを生成
battle = Battle()

# ポケモンを生成して選出に追加
battle.selected[0].append(Pokemon('カイリュー'))
battle.selected[1].append(Pokemon('ガチグマ(アカツキ)'))

# 勝敗が決まるまで繰り返す
while battle.winner() is None:
    # ターン経過
    battle.proceed()

    # 行動した順にログを表示
    print(f'\nターン{battle.turn}')
    for player in battle.action_order:
        print(f'{player=}', battle.log[player], battle.damage_log[player])